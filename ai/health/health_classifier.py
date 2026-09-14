"""Observatory health scoring, state classification, root-cause evidence, and degraded mode guidance.

Agent 7 Ownership.
Combines sensor confidences, anomaly reports, actuator telemetry, and comms links
into the authoritative ObservatoryHealthReport.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone

from ai.health.schemas import (
    HealthState,
    FaultSeverity,
    AnomalyType,
    AnomalyReport,
    SensorConfidence,
    CommsHealthIndicator,
    ActuatorHealthIndicator,
    FusedEnvironmentalState,
    DegradedMode,
    RootCauseEvidence,
    ObservatoryHealthReport,
)


class ObservatoryHealthClassifier:
    """Computes composite health score (0-100), health state, root-cause evidence, and degraded mode."""

    def evaluate(
        self,
        telemetry: Dict[str, Any],
        confidences: Dict[str, SensorConfidence],
        anomalies: List[AnomalyReport],
        fused_state: FusedEnvironmentalState,
        comms_health: CommsHealthIndicator,
        actuator_health: ActuatorHealthIndicator,
    ) -> ObservatoryHealthReport:
        # 1. Compute Base Score Components (max 100)
        sensor_pts = self._score_sensors(confidences, fused_state) # max 45
        comms_pts = self._score_comms(comms_health)                # max 30
        actuator_pts = self._score_actuators(actuator_health)      # max 15
        edge_health_bonus = min(10.0, float(telemetry.get("health", 100)) * 0.10) # max 10

        raw_score = sensor_pts + comms_pts + actuator_pts + edge_health_bonus

        # 2. Apply Deductions for Active Anomalies (avoiding double-counting multi-variable sensor dropouts)
        penalty = 0.0
        seen_physical_dropouts = set()

        for anom in anomalies:
            if anom.type == AnomalyType.DROPOUT_DISCONNECTED:
                # Group DHT22 temp & humidity into a single physical sensor dropout
                phys_key = "dht22" if anom.sensor in ["temperature", "humidity"] else anom.sensor
                if phys_key in seen_physical_dropouts:
                    continue
                seen_physical_dropouts.add(phys_key)
                # If fallback exists (e.g. BMP280 temperature fallback for DHT22), penalty is moderate
                if phys_key == "dht22" and fused_state.primary_temp_source == "BMP280":
                    penalty += 10.0
                elif anom.severity == FaultSeverity.CRITICAL:
                    penalty += 25.0
                else:
                    penalty += 15.0
            else:
                if anom.severity == FaultSeverity.CRITICAL:
                    penalty += 25.0
                elif anom.severity == FaultSeverity.HIGH:
                    penalty += 12.0
                elif anom.severity == FaultSeverity.MEDIUM:
                    penalty += 5.0
                elif anom.severity == FaultSeverity.LOW:
                    penalty += 1.5

        final_score = int(round(max(0.0, min(100.0, raw_score - penalty))))

        # 3. Authoritative Health State Classification
        # OFFLINE takes precedence if communication timed out
        if comms_health.heartbeat_stalled or comms_health.freshness_seconds > 30.0:
            health_state = HealthState.OFFLINE
        elif any(a.severity == FaultSeverity.CRITICAL for a in anomalies) or final_score < 40:
            health_state = HealthState.CRITICAL
        elif any(a.type == AnomalyType.DROPOUT_DISCONNECTED for a in anomalies) or (50 <= final_score < 85):
            # A sensor dropped or degraded with working fallback -> DEGRADED
            health_state = HealthState.DEGRADED
        elif any(a.severity in [FaultSeverity.HIGH, FaultSeverity.MEDIUM] for a in anomalies) or (final_score < 85):
            health_state = HealthState.WARNING
        else:
            health_state = HealthState.HEALTHY

        # 4. Determine Degraded Mode Recommendation
        degraded_rec = self._determine_degraded_mode(
            health_state, confidences, anomalies, actuator_health
        )

        # 5. Compile Root Cause Evidence
        root_causes = self._compile_root_causes(anomalies, confidences, comms_health, actuator_health)

        # 6. Overall Sensory Confidence
        confidence_values = [c.confidence for c in confidences.values()]
        mean_sensor_conf = sum(confidence_values) / len(confidence_values) if confidence_values else 1.0
        comms_factor = 0.0 if comms_health.heartbeat_stalled else max(0.2, 1.0 - comms_health.freshness_seconds / 30.0)
        overall_confidence = round(max(0.0, min(1.0, mean_sensor_conf * 0.75 + comms_factor * 0.25)), 2)

        conf_dict = {k: round(v.confidence, 2) for k, v in confidences.items()}

        return ObservatoryHealthReport(
            health=health_state,
            score=final_score,
            anomalies=anomalies,
            confidence=overall_confidence,
            sensor_confidences=conf_dict,
            fused_environment=fused_state,
            actuator_health=actuator_health,
            comms_health=comms_health,
            degraded_recommendation=degraded_rec,
            root_cause_evidence=root_causes,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def _score_sensors(
        self,
        confidences: Dict[str, SensorConfidence],
        fused_state: FusedEnvironmentalState
    ) -> float:
        # Max 45 points:
        # Temp: 14 pts, Humid: 11 pts, Press: 10 pts, Lux: 5 pts, Rain: 5 pts
        weights = {
            "temperature": 14.0,
            "humidity": 11.0,
            "pressure": 10.0,
            "lux": 5.0,
            "rain": 5.0,
        }
        score = 0.0
        for k, weight in weights.items():
            conf = confidences.get(k)
            if conf:
                if k == "temperature" and conf.dropout and fused_state.primary_temp_source == "BMP280":
                    score += 10.0  # Fallback temperature preserved via BMP280
                else:
                    score += weight * conf.confidence
            else:
                score += weight  # default if not evaluated
        return score

    def _score_comms(self, comms: CommsHealthIndicator) -> float:
        # Max 30 points: Freshness (20 pts), RSSI (10 pts)
        if comms.heartbeat_stalled:
            return 0.0

        # Freshness: 20 pts at 0s, decays linearly to 0 at 30s
        freshness_pts = max(0.0, 20.0 * (1.0 - comms.freshness_seconds / 30.0))

        # RSSI: 10 pts for -60 dBm, 2 pts for -95 dBm
        rssi_pts = max(2.0, min(10.0, 10.0 - (abs(comms.rssi_dbm) - 60.0) * 0.25))

        return freshness_pts + rssi_pts

    def _score_actuators(self, act: ActuatorHealthIndicator) -> float:
        # Max 15 points
        score = 15.0
        if not act.pan_healthy:
            score -= 6.0
        if not act.tilt_healthy:
            score -= 6.0
        if act.stall_suspected:
            score -= 5.0
        if act.jitter_score > 0.5:
            score -= 3.0
        return max(0.0, score)

    def _determine_degraded_mode(
        self,
        health_state: HealthState,
        confidences: Dict[str, SensorConfidence],
        anomalies: List[AnomalyReport],
        actuator_health: ActuatorHealthIndicator
    ) -> DegradedMode:
        if health_state == HealthState.CRITICAL:
            return DegradedMode.SAFE_STOW_RECOMMENDED

        if health_state == HealthState.OFFLINE:
            return DegradedMode.COMMS_FAILSAFE_RECOMMENDED

        # Specific component fallback recommendations
        temp_conf = confidences.get("temperature")
        if temp_conf and (temp_conf.dropout or temp_conf.confidence < 0.3):
            return DegradedMode.USE_BMP280_TEMPERATURE

        humid_conf = confidences.get("humidity")
        if humid_conf and (humid_conf.dropout or humid_conf.confidence < 0.3):
            return DegradedMode.INFER_HUMIDITY_FROM_HISTORY

        press_conf = confidences.get("pressure")
        if press_conf and (press_conf.dropout or press_conf.confidence < 0.3):
            return DegradedMode.INFER_PRESSURE_FROM_HISTORY

        # Rain sensor conflict
        if any(a.sensor == "rain" and a.type == AnomalyType.CROSS_SENSOR_INCONSISTENCY for a in anomalies):
            return DegradedMode.OPTICAL_CONFIRMATION_REQUIRED

        # Actuator hunting or error
        if actuator_health.jitter_score > 0.5 or (actuator_health.pan_tracking_error_deg > 10):
            return DegradedMode.REDUCED_SLEW_VELOCITY

        return DegradedMode.NORMAL_OPERATION

    def _compile_root_causes(
        self,
        anomalies: List[AnomalyReport],
        confidences: Dict[str, SensorConfidence],
        comms: CommsHealthIndicator,
        actuator: ActuatorHealthIndicator
    ) -> List[RootCauseEvidence]:
        evidence_list: List[RootCauseEvidence] = []

        for idx, anom in enumerate(anomalies):
            aid = f"FAULT-{idx+1:03d}"
            rec_action = "Inspect hardware subsystem and check wiring/bus connections."
            suspected = anom.sensor
            diagnosis = anom.description

            if anom.type == AnomalyType.DROPOUT_DISCONNECTED:
                if "temperature" in anom.sensor or "humidity" in anom.sensor:
                    suspected = "DHT22 (GPIO4)"
                    diagnosis = "Sensor disconnection or power loss on GPIO4 single-wire bus."
                    rec_action = "Check 3.3V power, GND, and 10k pullup resistor on GPIO4. Use BMP280 fallback."
                elif "pressure" in anom.sensor:
                    suspected = "BMP280 (I2C 0x76)"
                    diagnosis = "I2C communication failure on GPIO21(SDA)/GPIO22(SCL)."
                    rec_action = "Verify I2C bus wiring and pullup resistors."
                elif "rain" in anom.sensor:
                    suspected = "Rain Sensor (GPIO34 ADC1)"
                    diagnosis = "Analog ADC open circuit or sensor board unplugged."
                    rec_action = "Inspect GPIO34 ADC1 analog pin connection and probe board."

            elif anom.type == AnomalyType.STUCK_STALE:
                diagnosis = f"Reading is invariant across consecutive samples; sensor driver or ADC pin locked."
                rec_action = "Trigger soft reset of peripheral or power-cycle sensor rail."

            elif anom.type == AnomalyType.CROSS_SENSOR_INCONSISTENCY:
                if anom.sensor == "rain":
                    suspected = "Rain Sensor Plate"
                    diagnosis = "Conductive contamination (debris, dust, or insect) shorting rain traces under arid ambient conditions."
                    rec_action = "Clean rain sensor plate; confirm precipitation optically with ESP32-CAM before stowing."
                elif "temperature" in anom.sensor:
                    suspected = "DHT22 vs BMP280"
                    diagnosis = "Severe thermal divergence between redundant sensors; possible localized solar heating or internal sensor drift."
                    rec_action = "Apply Bayesian inverse-variance weighting and flag sensor requiring recalibration."

            elif anom.type == AnomalyType.DRIFT:
                diagnosis = f"Gradual calibration drift detected on {anom.sensor}."
                rec_action = "Schedule recalibration or apply linear offset compensation."

            elif anom.type == AnomalyType.COMMS_ANOMALY:
                suspected = "Wi-Fi Interface (ESP32 Station)"
                diagnosis = f"Comms latency or heartbeat interruption. RSSI={comms.rssi_dbm} dBm."
                rec_action = "Check AP signal strength, Wi-Fi channel interference, or backend network route."

            evidence_list.append(
                RootCauseEvidence(
                    anomaly_id=aid,
                    suspected_component=suspected,
                    root_cause=diagnosis,
                    confidence=anom.confidence,
                    evidence_metrics={
                        "observed_value": anom.observed_value,
                        "severity": anom.severity.value,
                        "type": anom.type.value,
                    },
                    recommended_action=rec_action
                )
            )

        return evidence_list
