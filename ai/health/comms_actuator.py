"""Communication link and actuator telemetry health monitoring.

Agent 7 Ownership.
Monitors:
1. Data freshness, packet arrival jitter, Wi-Fi RSSI degradation, and communication loss.
2. Actuator tracking errors, mechanical stalls, limit bounds, and jitter.
"""

from __future__ import annotations

import time
import math
from typing import Dict, List, Optional, Any, Tuple
from collections import deque
from datetime import datetime, timezone

from ai.health.schemas import (
    AnomalyReport,
    AnomalyType,
    FaultSeverity,
    CommsHealthIndicator,
    ActuatorHealthIndicator,
)


class CommsAndTelemetryMonitor:
    """Monitors communication link quality, data freshness, and heartbeat staleness."""

    COMMS_TIMEOUT_SEC = 30.0
    WARNING_LATENCY_SEC = 10.0

    def __init__(self, max_packet_history: int = 30):
        self.max_packet_history = max_packet_history
        self.arrival_times: deque[float] = deque(maxlen=max_packet_history)
        self.intervals: deque[float] = deque(maxlen=max_packet_history)
        self.last_arrival_time: Optional[float] = None
        self.dropout_count: int = 0

    def inspect_comms(
        self,
        telemetry: Dict[str, Any],
        current_time_sec: Optional[float] = None
    ) -> Tuple[CommsHealthIndicator, List[AnomalyReport]]:
        now = time.time() if current_time_sec is None else current_time_sec
        anomalies: List[AnomalyReport] = []

        # 1. Evaluate inter-arrival intervals and jitter
        if self.last_arrival_time is not None:
            interval = now - self.last_arrival_time
            self.intervals.append(interval)
            # Normal transmission interval is ~1.0s. If interval > 5s, count dropout
            if interval > 3.0:
                missed = int(round(interval / 1.0)) - 1
                self.dropout_count += max(1, missed)
        self.last_arrival_time = now
        self.arrival_times.append(now)

        # 2. Freshness calculation
        freshness_sec = 0.0
        ts_str = telemetry.get("timestamp")
        if ts_str:
            try:
                # Parse ISO-8601 string
                dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                packet_epoch = dt.timestamp()
                freshness_sec = max(0.0, now - packet_epoch)
            except Exception:
                freshness_sec = 0.0

        # Calculate jitter (std dev of packet arrival intervals)
        jitter = 0.0
        if len(self.intervals) >= 3:
            mean_int = sum(self.intervals) / len(self.intervals)
            variance = sum((x - mean_int) ** 2 for x in self.intervals) / len(self.intervals)
            jitter = math.sqrt(variance)

        # 3. Wi-Fi RSSI evaluation
        rssi = int(telemetry.get("wifi_rssi", -65))
        if rssi >= -65:
            rssi_quality = "EXCELLENT"
        elif rssi >= -75:
            rssi_quality = "GOOD"
        elif rssi >= -85:
            rssi_quality = "FAIR"
        elif rssi >= -90:
            rssi_quality = "POOR"
        else:
            rssi_quality = "CRITICAL"

        heartbeat_stalled = (freshness_sec > self.COMMS_TIMEOUT_SEC)

        # 4. Generate comms anomalies if necessary
        if heartbeat_stalled:
            anomalies.append(
                AnomalyReport(
                    sensor="comms",
                    type=AnomalyType.COMMS_ANOMALY,
                    severity=FaultSeverity.CRITICAL,
                    description=f"Heartbeat timeout: No fresh telemetry received for {freshness_sec:.1f}s (> {self.COMMS_TIMEOUT_SEC}s threshold)",
                    observed_value=freshness_sec,
                    expected_range=[0.0, self.WARNING_LATENCY_SEC],
                )
            )
        elif freshness_sec > self.WARNING_LATENCY_SEC:
            anomalies.append(
                AnomalyReport(
                    sensor="comms",
                    type=AnomalyType.COMMS_ANOMALY,
                    severity=FaultSeverity.MEDIUM,
                    description=f"High telemetry latency: Freshness delay is {freshness_sec:.1f}s",
                    observed_value=freshness_sec,
                    expected_range=[0.0, self.WARNING_LATENCY_SEC],
                )
            )

        if rssi < -85:
            anomalies.append(
                AnomalyReport(
                    sensor="wifi_link",
                    type=AnomalyType.COMMS_ANOMALY,
                    severity=FaultSeverity.LOW if rssi >= -90 else FaultSeverity.MEDIUM,
                    description=f"Degraded Wi-Fi signal strength: RSSI={rssi} dBm ({rssi_quality})",
                    observed_value=float(rssi),
                    expected_range=[-80.0, -30.0],
                )
            )

        indicator = CommsHealthIndicator(
            freshness_seconds=round(freshness_sec, 2),
            packet_jitter_seconds=round(jitter, 3),
            rssi_dbm=rssi,
            rssi_quality=rssi_quality,
            dropout_count=self.dropout_count,
            heartbeat_stalled=heartbeat_stalled,
        )
        return indicator, anomalies


class ActuatorTelemetryMonitor:
    """Monitors dual-axis pan/tilt servo angles, tracking error, jitter, and stalls."""

    def __init__(self, history_size: int = 15):
        self.history_size = history_size
        self.pan_history: deque[int] = deque(maxlen=history_size)
        self.tilt_history: deque[int] = deque(maxlen=history_size)
        self.target_pan: Optional[int] = None
        self.target_tilt: Optional[int] = None
        self.command_time: Optional[float] = None

    def set_commanded_target(self, pan: int, tilt: int):
        self.target_pan = pan
        self.target_tilt = tilt
        self.command_time = time.time()

    def inspect_actuators(
        self,
        telemetry: Dict[str, Any],
        current_time_sec: Optional[float] = None
    ) -> Tuple[ActuatorHealthIndicator, List[AnomalyReport]]:
        now = time.time() if current_time_sec is None else current_time_sec
        anomalies: List[AnomalyReport] = []

        pan = int(telemetry.get("pan", 90))
        tilt = int(telemetry.get("tilt", 0))

        self.pan_history.append(pan)
        self.tilt_history.append(tilt)

        # 1. Bounds check
        pan_ok = (0 <= pan <= 180)
        tilt_ok = (0 <= tilt <= 180)

        if not pan_ok:
            anomalies.append(
                AnomalyReport(
                    sensor="pan_servo",
                    type=AnomalyType.ACTUATOR_ANOMALY,
                    severity=FaultSeverity.HIGH,
                    description=f"Pan angle {pan}° outside physical limit [0, 180]°",
                    observed_value=float(pan),
                    expected_range=[0.0, 180.0],
                )
            )
        if not tilt_ok:
            anomalies.append(
                AnomalyReport(
                    sensor="tilt_servo",
                    type=AnomalyType.ACTUATOR_ANOMALY,
                    severity=FaultSeverity.HIGH,
                    description=f"Tilt angle {tilt}° outside physical limit [0, 180]°",
                    observed_value=float(tilt),
                    expected_range=[0.0, 180.0],
                )
            )

        # 2. Tracking error vs commanded target
        pan_err = 0.0
        tilt_err = 0.0
        stall_suspected = False
        slew_in_progress = False

        if self.target_pan is not None and self.target_tilt is not None:
            pan_err = abs(pan - self.target_pan)
            tilt_err = abs(tilt - self.target_tilt)

            if pan_err > 1 or tilt_err > 1:
                slew_in_progress = True
                # If commanded over 5 seconds ago and angle has not reached target or moved
                if self.command_time is not None and (now - self.command_time > 5.0):
                    if len(self.pan_history) >= 5 and len(set(self.pan_history)) == 1 and pan_err > 5:
                        stall_suspected = True
                        anomalies.append(
                            AnomalyReport(
                                sensor="pan_servo",
                                type=AnomalyType.ACTUATOR_ANOMALY,
                                severity=FaultSeverity.HIGH,
                                description=f"Pan servo stall suspected: Target={self.target_pan}°, Current={pan}° frozen for > 5s",
                                observed_value=float(pan_err),
                            )
                        )
                    if len(self.tilt_history) >= 5 and len(set(self.tilt_history)) == 1 and tilt_err > 5:
                        stall_suspected = True
                        anomalies.append(
                            AnomalyReport(
                                sensor="tilt_servo",
                                type=AnomalyType.ACTUATOR_ANOMALY,
                                severity=FaultSeverity.HIGH,
                                description=f"Tilt servo stall suspected: Target={self.target_tilt}°, Current={tilt}° frozen for > 5s",
                                observed_value=float(tilt_err),
                            )
                        )

        # 3. High-frequency hunting / jitter score
        jitter_score = 0.0
        if len(self.pan_history) >= 6:
            # Count sign flips in consecutive deltas
            deltas_pan = [self.pan_history[i] - self.pan_history[i - 1] for i in range(1, len(self.pan_history))]
            sign_flips = sum(1 for i in range(1, len(deltas_pan)) if deltas_pan[i] * deltas_pan[i - 1] < 0 and abs(deltas_pan[i]) <= 3)
            jitter_score = min(1.0, sign_flips / 4.0)

            if jitter_score >= 0.75:
                anomalies.append(
                    AnomalyReport(
                        sensor="actuator_bus",
                        type=AnomalyType.ACTUATOR_ANOMALY,
                        severity=FaultSeverity.LOW,
                        description="High-frequency mechanical oscillation / hunting detected on servo control loop",
                        observed_value=jitter_score,
                    )
                )

        indicator = ActuatorHealthIndicator(
            pan_healthy=pan_ok and not stall_suspected,
            tilt_healthy=tilt_ok and not stall_suspected,
            pan_tracking_error_deg=float(pan_err),
            tilt_tracking_error_deg=float(tilt_err),
            slew_in_progress=slew_in_progress,
            stall_suspected=stall_suspected,
            jitter_score=round(jitter_score, 2),
        )
        return indicator, anomalies
