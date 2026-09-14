"""
Solar Sentry — Observatory Digital Twin Engine
Agent 10: Digital Twin + Mission Memory + Learning + Simulation + Integration

The ObservatoryDigitalTwin maintains a live, coherent computational replica of the
physical solar observatory. It synchronizes edge telemetry, computer vision perception,
environmental predictions, cognitive decisions, and mission execution states.
It projects future state trajectories, registers and clears active faults, and
performs continuous sanity and consistency cross-checks.
"""

from __future__ import annotations

import datetime
import math
import uuid
from typing import Any, Dict, List, Optional

from twin.state import (
    ActiveFault,
    ActuatorSubsystemState,
    CognitiveDecisionState,
    CurrentState,
    FaultSeverity,
    FaultState,
    HealthSubsystemState,
    MissionPhase,
    MissionState,
    ObservatoryDigitalTwinState,
    PredictedFutureState,
    ProjectedStateSnapshot,
    SensorSubsystemState,
    VisionSubsystemState,
)


class ObservatoryDigitalTwin:
    """
    Authoritative Digital Twin instance for Solar Sentry.
    Represents the full cyber-physical observatory state.
    """

    def __init__(self, twin_id: str = "twin-sentry-01", device_id: str = "esp32-sentry-01"):
        self.twin_id = twin_id
        self.device_id = device_id
        self.state = ObservatoryDigitalTwinState(
            twin_id=twin_id,
            current=CurrentState(device_id=device_id),
            predicted=PredictedFutureState(),
            fault=FaultState(),
            mission=MissionState()
        )
        self.last_sync_time = datetime.datetime.now(datetime.timezone.utc)
        self.history: List[ObservatoryDigitalTwinState] = []
        self.history_max_len = 100

    def update_from_telemetry(self, telemetry: Dict[str, Any]) -> None:
        """Updates digital twin with edge telemetry payload adhering to SensorTelemetry.json."""
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.state.last_updated = now
        curr = self.state.current
        curr.timestamp = telemetry.get("timestamp", now)
        curr.system_state = telemetry.get("state", curr.system_state)

        # Sensors
        curr.sensors.temperature = float(telemetry.get("temperature", curr.sensors.temperature))
        curr.sensors.humidity = float(telemetry.get("humidity", curr.sensors.humidity))
        curr.sensors.pressure = float(telemetry.get("pressure", curr.sensors.pressure))
        curr.sensors.lux = float(telemetry.get("lux", curr.sensors.lux))
        curr.sensors.rain_raw = int(telemetry.get("rain_raw", curr.sensors.rain_raw))
        curr.sensors.rain_detected = bool(telemetry.get("rain_detected", curr.sensors.rain_detected))

        st = telemetry.get("sensor_status", {})
        curr.sensors.dht22_healthy = bool(st.get("dht22", curr.sensors.dht22_healthy))
        curr.sensors.bh1750_healthy = bool(st.get("bh1750", curr.sensors.bh1750_healthy))
        curr.sensors.bmp280_healthy = bool(st.get("bmp280", curr.sensors.bmp280_healthy))
        curr.sensors.rain_sensor_healthy = bool(st.get("rain", curr.sensors.rain_sensor_healthy))

        # Actuators
        curr.actuators.current_pan = int(telemetry.get("pan", curr.actuators.current_pan))
        curr.actuators.current_tilt = int(telemetry.get("tilt", curr.actuators.current_tilt))
        curr.actuators.is_stowed = (curr.actuators.current_pan == 90 and curr.actuators.current_tilt == 0)

        # Health
        curr.health.composite_health_score = int(telemetry.get("health", curr.health.composite_health_score))
        curr.health.wifi_rssi = int(telemetry.get("wifi_rssi", curr.health.wifi_rssi))
        curr.vision.camera_online = bool(telemetry.get("camera_online", curr.vision.camera_online))

        # Check for safety trips
        if curr.sensors.rain_detected:
            self.register_fault(
                subsystem="SAFETY",
                severity=FaultSeverity.CRITICAL,
                code="RAIN_DETECTED",
                message="Rain detected on edge sensor; emergency stow active",
                is_recoverable=True,
                recovery_action="WAIT_FOR_DRY"
            )
            self.state.fault.safety_interlock_tripped = True
            self.state.fault.tripped_interlock_name = "RAIN_INTERLOCK"
        elif self.state.fault.tripped_interlock_name == "RAIN_INTERLOCK" and not curr.sensors.rain_detected:
            self.clear_fault("RAIN_DETECTED")
            self.state.fault.safety_interlock_tripped = False
            self.state.fault.tripped_interlock_name = None

        # Check for sensor faults
        for s_name, ok in [
            ("DHT22", curr.sensors.dht22_healthy),
            ("BH1750", curr.sensors.bh1750_healthy),
            ("BMP280", curr.sensors.bmp280_healthy),
            ("RAIN", curr.sensors.rain_sensor_healthy),
        ]:
            fault_code = f"SENSOR_FAULT_{s_name}"
            if not ok:
                self.register_fault(
                    subsystem="SENSOR",
                    severity=FaultSeverity.DEGRADED if s_name != "RAIN" else FaultSeverity.CRITICAL,
                    code=fault_code,
                    message=f"Sensor subsystem {s_name} reports read failure or offline",
                    is_recoverable=True
                )
            else:
                self.clear_fault(fault_code)

    def update_from_vision(self, vision_result: Dict[str, Any]) -> None:
        """Updates digital twin with visual perception result from Agent 5."""
        v = self.state.current.vision
        v.image_id = vision_result.get("image_id", v.image_id)
        v.quality_score = float(vision_result.get("quality_score", v.quality_score))
        v.solar_disk_detected = bool(vision_result.get("solar_disk_detected", v.solar_disk_detected))
        v.sunspot_count = int(vision_result.get("sunspot_count", v.sunspot_count))
        v.obstruction_score = float(vision_result.get("obstruction_score", v.obstruction_score))

        obs = vision_result.get("obstruction_metrics", {})
        v.cloud_fraction = float(obs.get("cloud_fraction", v.cloud_fraction))

        # Check visual obstruction fault
        if v.obstruction_score > 0.8:
            self.register_fault(
                subsystem="VISION",
                severity=FaultSeverity.WARNING,
                code="HEAVY_OPTICAL_OBSTRUCTION",
                message=f"Optical path heavily occluded (obstruction={v.obstruction_score:.2f})",
                is_recoverable=True
            )
        else:
            self.clear_fault("HEAVY_OPTICAL_OBSTRUCTION")

    def update_from_decision(self, decision_data: Dict[str, Any]) -> None:
        """Updates digital twin with cognitive decision from Agent 8."""
        dec = self.state.current.decision
        raw_dec = decision_data.get("decision", dec.decision)
        dec.decision = raw_dec.value if hasattr(raw_dec, "value") else str(raw_dec)
        dec.confidence = float(decision_data.get("confidence", dec.confidence))
        raw_risk = decision_data.get("risk", dec.risk_level)
        dec.risk_level = raw_risk.value if hasattr(raw_risk, "value") else str(raw_risk)
        raw_mode = decision_data.get("mode", decision_data.get("operational_mode", dec.operational_mode))
        dec.operational_mode = raw_mode.value if hasattr(raw_mode, "value") else str(raw_mode)
        dec.reasons = list(decision_data.get("reasons", []))
        dec.fused_utility = float(decision_data.get("fused_utility", dec.fused_utility))
        dec.total_uncertainty = float(decision_data.get("total_uncertainty", dec.total_uncertainty))

        rec = decision_data.get("recommended_action")
        if isinstance(rec, dict):
            dec.recommended_action = rec.get("action")
        elif isinstance(rec, str):
            dec.recommended_action = rec

        # Sync system state if decision is authoritative
        if dec.decision in ["OBSERVE", "WAIT", "SCAN", "SUSPEND", "SAFE"]:
            if self.state.current.system_state not in ["FAULT", "SUSPEND"] or dec.decision == "SUSPEND":
                self.state.current.system_state = dec.decision

    def update_predictions(self, prediction_payload: Dict[str, Any]) -> None:
        """Updates projected future states using Agent 6 environmental forecast."""
        horizons = prediction_payload.get("horizons", {})
        projections: Dict[str, ProjectedStateSnapshot] = {}

        now_dt = datetime.datetime.now(datetime.timezone.utc)
        current_elev = max(0.0, 60.0 - 0.25 * (now_dt.minute + now_dt.second / 60.0))

        for h_str, h_data in horizons.items():
            try:
                mins = int(h_str.replace("m", ""))
            except ValueError:
                mins = 15

            proj_dt = now_dt + datetime.timedelta(minutes=mins)
            proj_elev = max(0.0, current_elev - 0.25 * mins)
            pred_q = float(h_data.get("predicted_quality", 0.7))
            clearness = float(h_data.get("clearness_index", 0.75))
            cloud_p = float(h_data.get("cloud_probability", 0.2))

            # Determine likely decision at horizon
            if pred_q >= 0.65:
                pred_dec = "OBSERVE"
            elif pred_q >= 0.35:
                pred_dec = "WAIT"
            else:
                pred_dec = "SUSPEND"

            projections[h_str] = ProjectedStateSnapshot(
                horizon_minutes=mins,
                projected_timestamp=proj_dt.isoformat(),
                projected_sun_elevation=round(proj_elev, 2),
                predicted_quality_score=round(pred_q, 3),
                predicted_clearness_index=round(clearness, 3),
                predicted_cloud_probability=round(cloud_p, 3),
                predicted_decision=pred_dec,
                confidence=round(float(prediction_payload.get("confidence", 0.9)), 3)
            )

        self.state.predicted.projections = projections
        trend_val = prediction_payload.get("trend_direction")
        if not trend_val:
            raw_trend = prediction_payload.get("trend")
            curr_q = prediction_payload.get("current_quality", 0.7)
            h15_q = horizons.get("15m", {}).get("predicted_quality", curr_q)
            delta = h15_q - curr_q
            if delta <= -0.15:
                trend_val = "RAPID_DETERIORATION"
            elif delta < -0.02 or (hasattr(raw_trend, "lux_trend") and getattr(raw_trend.lux_trend, "value", str(raw_trend.lux_trend)) in ["FALLING", "TrendDirection.FALLING"]):
                trend_val = "DEGRADING"
            elif delta > 0.03:
                trend_val = "IMPROVING"
            else:
                trend_val = "STABLE"
        self.state.predicted.trend_direction = str(trend_val)
        self.state.predicted.next_action_recommendation = str(prediction_payload.get("recommendation", "PROCEED"))

    def sync_mission(
        self,
        mission_id: Optional[str],
        objective: str,
        phase: MissionPhase,
        active_command_verb: Optional[str] = None,
        progress_percent: float = 0.0,
        target_pan: Optional[int] = None,
        target_tilt: Optional[int] = None
    ) -> None:
        """Updates mission planning and execution tracking."""
        m = self.state.mission
        m.mission_id = mission_id
        m.objective = objective
        m.phase = phase
        m.active_command_verb = active_command_verb
        m.progress_percent = progress_percent
        m.target_pan = target_pan
        m.target_tilt = target_tilt

        if phase == MissionPhase.ACQUIRING:
            m.observations_captured += 1

        self.state.current.current_action = f"{objective}:{phase.value}"

    def register_fault(
        self,
        subsystem: str,
        severity: FaultSeverity,
        code: str,
        message: str,
        is_recoverable: bool = True,
        recovery_action: Optional[str] = None
    ) -> None:
        """Registers an active fault condition in the digital twin."""
        for f in self.state.fault.active_faults:
            if f.code == code:
                f.message = message
                f.severity = severity
                return

        new_fault = ActiveFault(
            fault_id=f"flt-{uuid.uuid4().hex[:8]}",
            subsystem=subsystem,
            severity=severity,
            code=code,
            message=message,
            is_recoverable=is_recoverable,
            recovery_action=recovery_action
        )
        self.state.fault.active_faults.append(new_fault)
        self.state.fault.has_active_fault = True

    def clear_fault(self, code: str) -> None:
        """Clears an active fault if recovered."""
        self.state.fault.active_faults = [f for f in self.state.fault.active_faults if f.code != code]
        self.state.fault.has_active_fault = len(self.state.fault.active_faults) > 0

    def snapshot(self) -> Dict[str, Any]:
        """Returns full computational twin snapshot dictionary."""
        return self.state.to_dict()

    def record_step(self) -> None:
        """Saves current state into rolling historical buffer."""
        self.history.append(self.state.model_copy(deep=True))
        if len(self.history) > self.history_max_len:
            self.history.pop(0)
