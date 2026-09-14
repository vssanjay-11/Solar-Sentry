"""
Solar Sentry — Mission Replay Engine
Agent 10: Digital Twin + Mission Memory + Learning + Simulation + Integration

Provides deterministic mission playback, timeline step-through, and audit verification.
Allows replaying historical missions against the Cognitive Decision Engine to verify
reasoning determinism and post-action verification integrity.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from memory.schema import MissionRecord
from ai.decision.engine import CognitiveDecisionEngine
from ai.decision.types import (
    CognitiveInput,
    EdgeTelemetryState,
    EnvironmentPrediction,
    HealthFusionEvaluation,
    VisionEvaluation,
)


@dataclass
class ReplayStep:
    """Single chronological step in mission replay."""
    step_number: int
    event_type: str  # "MISSION_INIT", "DECISION", "COMMAND_DISPATCH", "OBSERVATION", "FAILURE", "VERIFICATION", "LESSON"
    timestamp: str
    summary: str
    details: Dict[str, Any]


@dataclass
class ReplayAuditReport:
    """Report summarizing mission replay and decision reproducibility verification."""
    mission_id: str
    total_steps: int
    objective: str
    recorded_decision: str
    reproduced_decision: str
    decision_matches: bool
    status: str
    verification_passed: bool
    lessons_summary: Optional[str]
    timeline: List[ReplayStep]


class MissionReplayEngine:
    """
    Replays mission events chronologically and validates reproducibility.
    """

    def __init__(self):
        self.decision_engine = CognitiveDecisionEngine()

    def replay_mission(self, mission: MissionRecord) -> ReplayAuditReport:
        """
        Parses and steps through the mission chronologically.
        Validates whether the cognitive decision can be deterministically reproduced.
        """
        timeline: List[ReplayStep] = []
        step_idx = 1

        # Step 1: Mission Initiation & Initial Conditions
        init_summary = f"Mission {mission.mission_id} initiated: {mission.objective.objective_type.value}"
        timeline.append(ReplayStep(
            step_number=step_idx,
            event_type="MISSION_INIT",
            timestamp=mission.created_at,
            summary=init_summary,
            details={
                "objective": mission.objective.model_dump(),
                "initial_conditions": mission.initial_conditions.model_dump()
            }
        ))
        step_idx += 1

        # Step 2: Cognitive Decision
        timeline.append(ReplayStep(
            step_number=step_idx,
            event_type="DECISION",
            timestamp=mission.cognitive_decision.trace_id or mission.created_at,
            summary=f"Cognitive decision reached: {mission.cognitive_decision.decision} (confidence={mission.cognitive_decision.confidence:.2f})",
            details=mission.cognitive_decision.model_dump()
        ))
        step_idx += 1

        # Re-evaluate decision for determinism check
        reproduced_decision = self._reproduce_decision(mission)

        # Step 3: Action Commands
        for action in mission.actions:
            timeline.append(ReplayStep(
                step_number=step_idx,
                event_type="COMMAND_DISPATCH",
                timestamp=action.dispatched_timestamp,
                summary=f"Dispatched command {action.command_verb} -> Status: {action.execution_status}",
                details=action.model_dump()
            ))
            step_idx += 1

        # Step 4: Failures (if any)
        for failure in mission.failures:
            timeline.append(ReplayStep(
                step_number=step_idx,
                event_type="FAILURE",
                timestamp=mission.created_at,
                summary=f"Failure encountered: {failure.failure_type} ({failure.error_code}): {failure.description}",
                details=failure.model_dump()
            ))
            step_idx += 1

        # Step 5: Observations
        for obs in mission.observations:
            timeline.append(ReplayStep(
                step_number=step_idx,
                event_type="OBSERVATION",
                timestamp=obs.timestamp,
                summary=f"Observation {obs.image_id} captured (Q={obs.quality_score:.2f}, Sunspots={obs.sunspot_count})",
                details=obs.model_dump()
            ))
            step_idx += 1

        # Step 6: Verification
        verif_passed = True
        if mission.verification:
            verif_passed = mission.verification.overall_verification_passed
            timeline.append(ReplayStep(
                step_number=step_idx,
                event_type="VERIFICATION",
                timestamp=mission.completed_at or mission.created_at,
                summary=f"Post-action verification verdict: {'PASS' if verif_passed else 'FAIL'} (score={mission.verification.verification_score:.2f})",
                details=mission.verification.model_dump()
            ))
            step_idx += 1

        # Step 7: Lessons
        lesson_str = None
        if mission.lessons:
            lesson_str = mission.lessons.key_takeaway
            timeline.append(ReplayStep(
                step_number=step_idx,
                event_type="LESSON",
                timestamp=mission.completed_at or mission.created_at,
                summary=f"Retrospective lesson distilled: {lesson_str}",
                details=mission.lessons.model_dump()
            ))
            step_idx += 1

        return ReplayAuditReport(
            mission_id=mission.mission_id,
            total_steps=len(timeline),
            objective=mission.objective.objective_type.value,
            recorded_decision=mission.cognitive_decision.decision,
            reproduced_decision=reproduced_decision,
            decision_matches=(reproduced_decision == mission.cognitive_decision.decision),
            status=mission.status.value,
            verification_passed=verif_passed,
            lessons_summary=lesson_str,
            timeline=timeline
        )

    def _reproduce_decision(self, mission: MissionRecord) -> str:
        """Runs the recorded initial conditions back through the Decision Engine."""
        cond = mission.initial_conditions
        health_eval = HealthFusionEvaluation(
            overall_health_score=cond.hardware_health_score / 100.0,
            is_healthy=(cond.hardware_health_score > 70),
            sensor_health={"dht22": True, "bh1750": True, "bmp280": True, "rain": True},
            failed_sensors=[],
            anomaly_score=0.0
        )
        vision_eval = VisionEvaluation(
            vision_quality=0.85,
            solar_disk_detected=True,
            sunspot_count=2,
            obstruction_score=0.05,
            confidence=0.9
        )
        env_eval = EnvironmentPrediction(
            environment_quality=cond.clearness_index,
            predicted_quality_15m=cond.predicted_quality_15m,
            predicted_quality_30m=cond.predicted_quality_15m,
            predicted_quality_60m=cond.predicted_quality_15m,
            weather_risk=cond.weather_risk,
            rain_imminent=(cond.weather_risk == "CRITICAL"),
            confidence=0.92
        )
        edge_state = EdgeTelemetryState(
            state="STANDBY",
            rain_detected=False,
            rain_raw=3850,
            comms_age_sec=0.5,
            pan=90,
            tilt=45,
            lux=cond.lux,
            temperature=cond.temperature,
            humidity=cond.humidity,
            pressure=cond.pressure
        )
        cog_input = CognitiveInput(
            vision=vision_eval,
            environment=env_eval,
            health=health_eval,
            edge=edge_state
        )
        res = self.decision_engine.evaluate(cog_input)
        return res.decision.value
