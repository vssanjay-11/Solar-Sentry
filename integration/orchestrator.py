"""
Solar Sentry — Central Autonomous Observatory Platform (Integration Orchestrator)
Agent 10: Digital Twin + Mission Memory + Learning + Simulation + Integration

The master coordinator unifying all 10 agent subsystems into a coherent autonomous loop:
PERCEIVE -> UNDERSTAND -> PREDICT -> PLAN -> ACT -> VERIFY -> LEARN
"""

from __future__ import annotations

import datetime
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from ai.decision.engine import CognitiveDecisionEngine
from ai.decision.types import (
    CognitiveInput,
    EdgeTelemetryState,
    EnvironmentPrediction,
    HealthFusionEvaluation,
    VisionEvaluation,
)
from integration.adapters import (
    DatabaseAdapter,
    EdgeAdapter,
    EnvironmentAdapter,
    HealthAnomalyAdapter,
    MissionPlannerAdapter,
    VisionAdapter,
)
from learning.collector import ExperienceCollector
from memory.schema import (
    MissionAction,
    MissionCondition,
    MissionDecision,
    MissionFailure,
    MissionLesson,
    MissionObjective,
    MissionObjectiveType,
    MissionObservation,
    MissionRecord,
    MissionStatus,
    MissionVerification,
)
from memory.storage import MissionMemoryRepository
from simulation.engine import ObservatorySimulator
from simulation.scenarios import SimulationScenario, ScenarioType, get_scenario
from simulation.what_if import WhatIfSimulationEngine, WhatIfPerturbation, WhatIfComparativeReport
from memory.replay import MissionReplayEngine, ReplayAuditReport
from twin.state import MissionPhase
from twin.twin import ObservatoryDigitalTwin


class SolarSentryPlatform:
    """
    Central autonomous cognitive platform running the full observatory operations cycle.
    """

    def __init__(
        self,
        edge_adapter: Optional[EdgeAdapter] = None,
        db_adapter: Optional[DatabaseAdapter] = None,
        twin_id: str = "twin-sentry-01"
    ):
        self.edge = edge_adapter or EdgeAdapter()
        self.db = db_adapter or DatabaseAdapter()
        self.health_adapter = HealthAnomalyAdapter()
        self.vision_adapter = VisionAdapter()
        self.env_adapter = EnvironmentAdapter()
        self.decision_engine = CognitiveDecisionEngine()
        self.planner = MissionPlannerAdapter(self.edge)
        self.digital_twin = ObservatoryDigitalTwin(twin_id=twin_id)
        self.memory = MissionMemoryRepository()
        self.learning_collector = ExperienceCollector()
        self.what_if_engine = WhatIfSimulationEngine()
        self.replay_engine = MissionReplayEngine()

        self.current_mission: Optional[MissionRecord] = None

    def run_cognitive_cycle(
        self,
        vision_preset: str = "quiet_sun",
        target_pan: int = 90,
        target_tilt: int = 45,
        scan_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Executes a single end-to-end cognitive loop across all subsystems:
        1. Ingest telemetry from edge
        2. Ingest camera vision frame
        3. Evaluate health & anomaly (Agent 7)
        4. Predict observation quality (Agent 6)
        5. Evaluate cognitive decision (Agent 8)
        6. Synchronize Digital Twin (Agent 10)
        7. Plan and execute mission action (Agent 9)
        8. Dispatch command to edge (Agent 1)
        9. Run post-action verification
        10. Record into Mission Memory & Learning (Agent 10)
        """
        cycle_id = f"cyc-{uuid.uuid4().hex[:8]}"

        # 1. PERCEIVE: Edge Telemetry
        telemetry = self.edge.get_telemetry()
        self.db.store_telemetry(telemetry)

        # 2. PERCEIVE: Optical Camera Perception
        vision = self.vision_adapter.analyze_frame(preset=vision_preset)
        self.db.store_observation(vision)

        # 3. UNDERSTAND: Sensor Fusion & Health Anomaly (Agent 7)
        health_eval = self.health_adapter.evaluate_health(telemetry)

        # 4. PREDICT: Environment & Observation Quality Forecast (Agent 6)
        env_pred = self.env_adapter.predict(telemetry, vision)

        # 5. REASON: Cognitive Decision Engine (Agent 8)
        vision_eval = VisionEvaluation(
            vision_quality=vision.get("quality_score", 0.8),
            solar_disk_detected=vision.get("solar_disk_detected", True),
            sunspot_count=vision.get("sunspot_count", 0),
            obstruction_score=vision.get("obstruction_score", 0.05),
            cloud_fraction=vision.get("obstruction_score", 0.05),
            confidence=0.9
        )

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

        edge_state = EdgeTelemetryState(
            state=telemetry.get("state", "STANDBY"),
            rain_detected=telemetry.get("rain_detected", False),
            rain_raw=telemetry.get("rain_raw", 3850),
            comms_age_sec=0.5,
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

        cognitive_decision = self.decision_engine.evaluate(cog_input)
        dec_dict = cognitive_decision.to_dict()
        dec_dict["decision"] = cognitive_decision.decision.value if hasattr(cognitive_decision.decision, "value") else str(cognitive_decision.decision)
        dec_dict["risk"] = cognitive_decision.risk.value if hasattr(cognitive_decision.risk, "value") else str(cognitive_decision.risk)
        dec_dict["operational_mode"] = cognitive_decision.mode.value if hasattr(cognitive_decision.mode, "value") else str(cognitive_decision.mode)

        # 6. DIGITAL TWIN SYNCHRONIZATION (Agent 10)
        self.digital_twin.update_from_telemetry(telemetry)
        self.digital_twin.update_from_vision(vision)
        self.digital_twin.update_from_decision(dec_dict)
        self.digital_twin.update_predictions(env_pred)
        self.digital_twin.record_step()

        # 7. PLAN & ACT: Mission Planning & Command Execution (Agent 9 -> Agent 1)
        target_decision = cognitive_decision.decision.value
        cmd_result, selected_region = self.planner.plan_and_execute(
            decision=target_decision,
            target_pan=target_pan,
            target_tilt=target_tilt,
            scan_mode=scan_mode
        )

        # Step edge actuator dynamics to allow servo slewing to target
        for _ in range(5):
            self.edge.step(dt=0.5)
            if hasattr(self.edge, "device") and hasattr(self.edge.device, "actuators"):
                if not self.edge.device.actuators.moving:
                    break
        updated_telemetry = self.edge.get_telemetry()
        self.digital_twin.update_from_telemetry(updated_telemetry)

        # 8. VERIFY: Closed-Loop Post-Action Verification
        expected_pan = selected_region[0] if selected_region else (target_pan if target_decision == "OBSERVE" else 90)
        expected_tilt = selected_region[1] if selected_region else (target_tilt if target_decision == "OBSERVE" else 0)

        pan_actual = updated_telemetry.get("pan", 90)
        tilt_actual = updated_telemetry.get("tilt", 0)

        actuator_aligned = (abs(pan_actual - expected_pan) <= 5 and abs(tilt_actual - expected_tilt) <= 5)
        disk_verified = vision.get("solar_disk_detected", False)
        quality_ok = (vision.get("quality_score", 0.0) >= 0.5)

        verif_passed = (target_decision != "OBSERVE") or (actuator_aligned and quality_ok)
        verif_score = 1.0 if verif_passed else 0.4

        verification = MissionVerification(
            actuator_aligned=actuator_aligned,
            optical_disk_verified=disk_verified,
            quality_threshold_met=quality_ok,
            environmental_safety_confirmed=(not updated_telemetry.get("rain_detected", False)),
            overall_verification_passed=verif_passed,
            verification_score=verif_score,
            notes=[f"Action {target_decision} verified with score {verif_score}"]
        )

        # 9. MISSION MEMORY RECORDING (Agent 10)
        mission_action = MissionAction(
            command_id=cmd_result.get("command_id", "cmd-unknown"),
            command_verb=target_decision,
            pan=expected_pan,
            tilt=expected_tilt,
            speed=100,
            dispatched_timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            execution_status=cmd_result.get("status", "SUCCESS"),
            edge_response_message=cmd_result.get("message")
        )

        mission_obs = MissionObservation(
            image_id=vision.get("image_id", "img-unknown"),
            timestamp=vision.get("timestamp", datetime.datetime.now(datetime.timezone.utc).isoformat()),
            pan_actual=pan_actual,
            tilt_actual=tilt_actual,
            quality_score=vision.get("quality_score", 0.0),
            solar_disk_detected=disk_verified,
            sunspot_count=vision.get("sunspot_count", 0),
            obstruction_score=vision.get("obstruction_score", 0.0),
            cloud_fraction=vision.get("obstruction_score", 0.0)
        )

        failures = []
        if cmd_result.get("status") == "REJECTED_SAFETY":
            failures.append(MissionFailure(
                failure_type="SAFETY_INTERLOCK",
                error_code="COMMAND_REJECTED_SAFETY",
                description=cmd_result.get("message", "Safety interlock rejected command"),
                occurred_at_sec=0.0
            ))

        lesson = MissionLesson(
            observation_yield_rating="OPTIMAL" if (verif_passed and target_decision == "OBSERVE") else "ACCEPTABLE",
            forecast_accuracy_delta=round(vision.get("quality_score", 0.0) - h15.get("predicted_quality", 0.7), 3),
            weather_risk_assessment_accuracy="ACCURATE",
            key_takeaway=f"Cycle executed with decision {target_decision} under {env_pred['weather_risk']} risk"
        )

        # Create or update active mission
        mission = MissionRecord(
            mission_id=f"msn-{cycle_id}",
            status=MissionStatus.COMPLETED if verif_passed else MissionStatus.SUSPENDED,
            objective=MissionObjective(
                objective_type=MissionObjectiveType.SOLAR_SURVEY if not scan_mode else MissionObjectiveType.SCAN_SEARCH,
                target_description="Autonomous single-cycle observation",
                target_pan=target_pan,
                target_tilt=target_tilt
            ),
            initial_conditions=MissionCondition(
                temperature=telemetry.get("temperature", 25.0),
                humidity=telemetry.get("humidity", 40.0),
                pressure=telemetry.get("pressure", 1013.25),
                lux=telemetry.get("lux", 50000.0),
                solar_elevation_deg=45.0,
                clearness_index=env_pred.get("clearness_index", 0.8),
                predicted_quality_15m=h15.get("predicted_quality", 0.7),
                weather_risk=env_pred["weather_risk"],
                hardware_health_score=telemetry.get("health", 100)
            ),
            cognitive_decision=MissionDecision(
                decision=target_decision,
                confidence=cognitive_decision.confidence,
                risk_level=cognitive_decision.risk.value if hasattr(cognitive_decision.risk, "value") else str(cognitive_decision.risk),
                operational_mode=cognitive_decision.mode.value if hasattr(cognitive_decision, "mode") and hasattr(cognitive_decision.mode, "value") else "AUTONOMOUS",
                reasons=cognitive_decision.reasons,
                fused_utility=dec_dict.get("fused_utility", 0.7),
                trace_id=cycle_id
            ),
            actions=[mission_action],
            observations=[mission_obs],
            failures=failures,
            verification=verification,
            lessons=lesson,
            composite_quality_score=vision.get("quality_score", 0.0)
        )
        self.memory.save_mission(mission)
        self.current_mission = mission

        # 10. CONTINUAL LEARNING INGESTION (Agent 10)
        self.learning_collector.log_prediction(
            sample_id=cycle_id,
            features={
                "temperature": telemetry.get("temperature", 25.0),
                "humidity": telemetry.get("humidity", 40.0),
                "pressure": telemetry.get("pressure", 1013.25),
                "lux": telemetry.get("lux", 50000.0),
                "clearness_index": env_pred.get("clearness_index", 0.8)
            },
            pred_15m=h15.get("predicted_quality", 0.7),
            pred_30m=h30.get("predicted_quality", 0.7),
            weather_risk=env_pred["weather_risk"]
        )
        self.learning_collector.reconcile_ground_truth(
            sample_id=cycle_id,
            actual_15m=vision.get("quality_score", 0.7),
            verification_score=verif_score
        )

        return {
            "cycle_id": cycle_id,
            "telemetry": telemetry,
            "vision": vision,
            "decision": dec_dict,
            "environment_prediction": env_pred,
            "command_result": cmd_result,
            "verification": verification.model_dump(),
            "selected_region": selected_region,
            "mission": mission.to_dict(),
            "twin_snapshot": self.digital_twin.snapshot()
        }

    def execute_scenario(self, scenario_type: ScenarioType | str, steps: int = 5) -> List[Dict[str, Any]]:
        """Runs a complete simulation scenario step-by-step through the platform."""
        sim = ObservatorySimulator(scenario=get_scenario(scenario_type))
        results = []
        for _ in range(steps):
            telemetry, sim_vision = sim.step()
            # Feed simulated step into platform loop
            # Update edge internal values
            self.edge.device.sensors.temp_base = telemetry["temperature"]
            self.edge.device.sensors.humid_base = telemetry["humidity"]
            self.edge.device.sensors.pressure_base = telemetry["pressure"]
            self.edge.device.sensors.lux_base = telemetry["lux"]
            self.edge.device.sensors.rain_raw = telemetry["rain_raw"]
            self.edge.device.sensors.rain_detected = telemetry["rain_detected"]
            self.edge.device.state = telemetry["state"]
            self.edge.device.sensors.dht_fault = not telemetry["sensor_status"]["dht22"]
            self.edge.device.sensors.bh1750_fault = not telemetry["sensor_status"]["bh1750"]
            self.edge.device.sensors.bmp_fault = not telemetry["sensor_status"]["bmp280"]

            cycle_out = self.run_cognitive_cycle(
                vision_preset=sim_vision["metadata"].get("vision_preset", "quiet_sun"),
                target_pan=telemetry.get("pan", 90),
                target_tilt=telemetry.get("tilt", 45)
            )
            results.append(cycle_out)
        return results
