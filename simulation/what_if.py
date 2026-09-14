"""
Solar Sentry — What-If Perturbation & Propagation Simulation Engine
Agent 10: Digital Twin + Mission Memory + Learning + Simulation + Integration

Allows counterfactual scenario perturbations such as:
- humidity +15%
- rain = true
- camera quality -30%
- sensor failure (e.g. dht22, bmp280, bh1750)
- communication loss
- observation quality improvement / degradation

Propagates the perturbations downstream through:
Sensor Feeds -> Feature Extraction -> Environment Prediction -> Health Assessment ->
Cognitive Decision Engine -> Edge Safety Machine -> Comparative Impact Report.
"""

from __future__ import annotations

import copy
import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ai.decision.engine import CognitiveDecisionEngine
from ai.decision.types import (
    CognitiveInput,
    EdgeTelemetryState,
    EnvironmentPrediction,
    HealthFusionEvaluation,
    VisionEvaluation,
)
from ai.environment.predictor import EnvironmentPredictor
from ai.environment.schemas import TelemetryInput, VisionHints


@dataclass
class WhatIfPerturbation:
    """Specification of perturbations applied to a baseline observatory state."""
    delta_humidity_percent: float = 0.0
    rain_active: Optional[bool] = None
    camera_quality_delta_percent: float = 0.0
    sensor_failure: Optional[str] = None  # "dht22", "bh1750", "bmp280", "rain"
    communication_loss: bool = False
    observation_quality_delta: float = 0.0
    delta_lux_percent: float = 0.0
    delta_temperature_c: float = 0.0


@dataclass
class WhatIfComparativeReport:
    """Detailed comparative impact analysis report between baseline and perturbed scenarios."""
    baseline_decision: str
    perturbed_decision: str
    decision_changed: bool
    baseline_confidence: float
    perturbed_confidence: float
    confidence_delta: float
    baseline_risk: str
    perturbed_risk: str
    baseline_mode: str
    perturbed_mode: str
    interlocks_triggered: List[str]
    perturbations_applied: Dict[str, Any]
    baseline_reasons: List[str]
    perturbed_reasons: List[str]
    impact_narrative: str
    timestamp: str = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "baseline_decision": self.baseline_decision,
            "perturbed_decision": self.perturbed_decision,
            "decision_changed": self.decision_changed,
            "baseline_confidence": round(self.baseline_confidence, 4),
            "perturbed_confidence": round(self.perturbed_confidence, 4),
            "confidence_delta": round(self.confidence_delta, 4),
            "baseline_risk": self.baseline_risk,
            "perturbed_risk": self.perturbed_risk,
            "baseline_mode": self.baseline_mode,
            "perturbed_mode": self.perturbed_mode,
            "interlocks_triggered": self.interlocks_triggered,
            "perturbations_applied": self.perturbations_applied,
            "baseline_reasons": self.baseline_reasons,
            "perturbed_reasons": self.perturbed_reasons,
            "impact_narrative": self.impact_narrative,
            "timestamp": self.timestamp,
        }


class WhatIfSimulationEngine:
    """
    Evaluates sensitivity and resilience of the autonomous cognitive loop
    by perturbing environmental, visual, sensor, or network parameters.
    """

    def __init__(self):
        self.decision_engine = CognitiveDecisionEngine()
        self.env_predictor = EnvironmentPredictor()

    def run_what_if(
        self,
        baseline_telemetry: Dict[str, Any],
        baseline_vision: Dict[str, Any],
        perturbation: WhatIfPerturbation
    ) -> WhatIfComparativeReport:
        """
        Executes counterfactual simulation:
        1. Evaluates baseline cognitive decision.
        2. Applies perturbations to telemetry and visual states.
        3. Evaluates perturbed cognitive decision.
        4. Compares the two paths and produces an audit-grade impact report.
        """
        # --- 1. Evaluate Baseline ---
        base_decision = self._evaluate_pipeline(baseline_telemetry, baseline_vision)

        # --- 2. Apply Perturbations ---
        pert_telemetry = copy.deepcopy(baseline_telemetry)
        pert_vision = copy.deepcopy(baseline_vision)
        applied_deltas: Dict[str, Any] = {}

        # Humidity perturbation
        if perturbation.delta_humidity_percent != 0.0:
            orig_h = pert_telemetry.get("humidity", 45.0)
            pert_telemetry["humidity"] = round(max(0.0, min(100.0, orig_h + perturbation.delta_humidity_percent)), 1)
            applied_deltas["humidity"] = f"{orig_h}% -> {pert_telemetry['humidity']}%"

        # Temperature perturbation
        if perturbation.delta_temperature_c != 0.0:
            orig_t = pert_telemetry.get("temperature", 25.0)
            pert_telemetry["temperature"] = round(orig_t + perturbation.delta_temperature_c, 1)
            applied_deltas["temperature"] = f"{orig_t}C -> {pert_telemetry['temperature']}C"

        # Lux perturbation
        if perturbation.delta_lux_percent != 0.0:
            orig_l = pert_telemetry.get("lux", 50000.0)
            pert_telemetry["lux"] = round(max(0.0, orig_l * (1.0 + perturbation.delta_lux_percent / 100.0)), 1)
            applied_deltas["lux"] = f"{orig_l} lx -> {pert_telemetry['lux']} lx"

        # Rain perturbation
        if perturbation.rain_active is not None:
            pert_telemetry["rain_detected"] = perturbation.rain_active
            pert_telemetry["rain_raw"] = 800 if perturbation.rain_active else 3850
            applied_deltas["rain_detected"] = perturbation.rain_active

        # Camera quality perturbation
        if perturbation.camera_quality_delta_percent != 0.0:
            orig_q = pert_vision.get("quality_score", 0.85)
            new_q = max(0.0, min(1.0, orig_q * (1.0 + perturbation.camera_quality_delta_percent / 100.0)))
            pert_vision["quality_score"] = round(new_q, 3)
            # Correlate obstruction if quality drops heavily
            if perturbation.camera_quality_delta_percent < -20.0:
                pert_vision["obstruction_score"] = min(1.0, pert_vision.get("obstruction_score", 0.1) + 0.5)
                pert_vision["solar_disk_detected"] = (new_q > 0.4)
            applied_deltas["camera_quality"] = f"{orig_q} -> {pert_vision['quality_score']}"

        # Observation quality direct delta
        if perturbation.observation_quality_delta != 0.0:
            orig_q = pert_vision.get("quality_score", 0.85)
            pert_vision["quality_score"] = round(max(0.0, min(1.0, orig_q + perturbation.observation_quality_delta)), 3)
            applied_deltas["direct_quality_delta"] = f"{orig_q} -> {pert_vision['quality_score']}"

        # Sensor failure injection
        if perturbation.sensor_failure:
            st = pert_telemetry.setdefault("sensor_status", {"dht22": True, "bh1750": True, "bmp280": True, "rain": True})
            target_sensor = perturbation.sensor_failure.lower()
            if target_sensor in st:
                st[target_sensor] = False
                applied_deltas["failed_sensor"] = target_sensor
                if target_sensor == "dht22":
                    pert_telemetry["temperature"] = -999.0
                    pert_telemetry["humidity"] = -999.0
                elif target_sensor == "bmp280":
                    pert_telemetry["pressure"] = -999.0
                elif target_sensor == "bh1750":
                    pert_telemetry["lux"] = -999.0

        # Comms dropout
        comms_age = 45.0 if perturbation.communication_loss else 0.5
        if perturbation.communication_loss:
            applied_deltas["communication_loss"] = "Comms heartbeat timeout (>30s)"

        # --- 3. Evaluate Perturbed Pipeline ---
        pert_decision = self._evaluate_pipeline(pert_telemetry, pert_vision, comms_age=comms_age)

        # --- 4. Synthesis & Interlock Tracing ---
        interlocks = []
        if pert_telemetry.get("rain_detected", False):
            interlocks.append("RAIN_HAZARD_INTERLOCK")
        if comms_age > 30.0:
            interlocks.append("COMMS_TIMEOUT_INTERLOCK")
        if perturbation.sensor_failure and perturbation.sensor_failure.lower() == "rain":
            interlocks.append("CRITICAL_SENSOR_FAULT")

        dec_changed = (base_decision["decision"] != pert_decision["decision"])

        # Construct narrative
        if dec_changed:
            narrative = (
                f"Perturbation caused a state transition from {base_decision['decision']} to {pert_decision['decision']}. "
                f"Risk shifted from {base_decision['risk']} to {pert_decision['risk']}. "
                f"Confidence delta: {pert_decision['confidence'] - base_decision['confidence']:+.2f}. "
            )
            if interlocks:
                narrative += f"Hard safety interlocks triggered: {', '.join(interlocks)}."
        else:
            narrative = (
                f"System demonstrated resilience: Decision maintained at {base_decision['decision']} "
                f"despite applied perturbations ({', '.join(applied_deltas.keys())}). "
                f"Confidence changed by {pert_decision['confidence'] - base_decision['confidence']:+.2f}."
            )

        return WhatIfComparativeReport(
            baseline_decision=base_decision["decision"],
            perturbed_decision=pert_decision["decision"],
            decision_changed=dec_changed,
            baseline_confidence=base_decision["confidence"],
            perturbed_confidence=pert_decision["confidence"],
            confidence_delta=pert_decision["confidence"] - base_decision["confidence"],
            baseline_risk=base_decision["risk"],
            perturbed_risk=pert_decision["risk"],
            baseline_mode=base_decision["mode"],
            perturbed_mode=pert_decision["mode"],
            interlocks_triggered=interlocks,
            perturbations_applied=applied_deltas,
            baseline_reasons=base_decision["reasons"],
            perturbed_reasons=pert_decision["reasons"],
            impact_narrative=narrative
        )

    def _evaluate_pipeline(
        self,
        telemetry: Dict[str, Any],
        vision: Dict[str, Any],
        comms_age: float = 0.5
    ) -> Dict[str, Any]:
        """Internal helper running feature extraction, env prediction, and decision fusion."""
        # 1. Environment prediction
        t_input = TelemetryInput(
            temperature=telemetry.get("temperature", 25.0),
            humidity=telemetry.get("humidity", 40.0),
            pressure=telemetry.get("pressure", 1013.25),
            lux=telemetry.get("lux", 50000.0),
            rain_raw=telemetry.get("rain_raw", 3850),
            rain_detected=telemetry.get("rain_detected", False),
            pan=telemetry.get("pan", 90),
            tilt=telemetry.get("tilt", 45),
            state=telemetry.get("state", "STANDBY"),
            sensor_status=telemetry.get("sensor_status", {"dht22": True, "bh1750": True, "bmp280": True, "rain": True})
        )
        v_hints = VisionHints(
            vision_quality=vision.get("quality_score", 0.8),
            cloud_cover=vision.get("obstruction_score", 0.1),
            solar_disk_detected=vision.get("solar_disk_detected", True)
        )
        env_pred = self.env_predictor.predict(telemetry=t_input, vision_hints=v_hints)

        # 2. Build CognitiveInput for Agent 8 Engine
        st = telemetry.get("sensor_status", {})
        sensor_dict = {
            "dht22": st.get("dht22", True),
            "bh1750": st.get("bh1750", True),
            "bmp280": st.get("bmp280", True),
            "rain": st.get("rain", True),
        }
        all_sensors_ok = all(sensor_dict.values())

        # Health input
        failed_sensors = [k for k, v in sensor_dict.items() if not v]
        health_eval = HealthFusionEvaluation(
            overall_health_score=1.0 if all_sensors_ok else 0.6,
            is_healthy=all_sensors_ok,
            sensor_health=sensor_dict,
            failed_sensors=failed_sensors,
            anomaly_score=0.0 if all_sensors_ok else 0.45,
            anomaly_detected=not all_sensors_ok,
            sensor_conflict=False
        )

        # Vision input
        vision_eval = VisionEvaluation(
            vision_quality=vision.get("quality_score", 0.8),
            solar_disk_detected=vision.get("solar_disk_detected", True),
            sunspot_count=vision.get("sunspot_count", 0),
            obstruction_score=vision.get("obstruction_score", 0.1),
            cloud_fraction=vision.get("obstruction_score", 0.1),
            confidence=0.9
        )

        # Env prediction input
        h15 = env_pred["horizons"].get("15m", {})
        h30 = env_pred["horizons"].get("30m", {})
        h60 = env_pred["horizons"].get("60m", {})
        env_eval = EnvironmentPrediction(
            environment_quality=env_pred["current_quality"],
            predicted_quality_15m=h15.get("predicted_quality", 0.7),
            predicted_quality_30m=h30.get("predicted_quality", 0.7),
            predicted_quality_60m=h60.get("predicted_quality", 0.7),
            weather_risk=env_pred["weather_risk"],
            rain_imminent=(telemetry.get("rain_detected", False) or env_pred["weather_risk"] == "CRITICAL"),
            confidence=env_pred["confidence"]
        )

        # Edge state input
        edge_state = EdgeTelemetryState(
            state=telemetry.get("state", "STANDBY"),
            rain_detected=telemetry.get("rain_detected", False),
            rain_raw=telemetry.get("rain_raw", 3850),
            comms_age_sec=comms_age,
            pan=telemetry.get("pan", 90),
            tilt=telemetry.get("tilt", 45),
            lux=telemetry.get("lux", 50000.0),
            temperature=telemetry.get("temperature", 25.0),
            humidity=telemetry.get("humidity", 40.0),
            pressure=telemetry.get("pressure", 1013.25)
        )

        cog_input = CognitiveInput(
            vision=vision_eval,
            environment=env_eval,
            health=health_eval,
            edge=edge_state
        )

        # Evaluate decision
        dec_result = self.decision_engine.evaluate(cog_input)
        return dec_result.to_dict()
