"""Solar Sentry — Autonomous Mission Planner.

Agent 9 Ownership.
Decides HOW to execute the observatory objectives directed by Agent 8.
Synthesizes cognitive decisions (OBSERVE, SCAN, WAIT, SUSPEND, SAFE)
into executable missions, candidate evaluations, active perception queries,
and sequenced hardware commands.
"""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone

from .types import (
    Mission,
    MissionObjective,
    MissionType,
    MissionState,
    MissionAction,
    ActionVerb,
    ActionStatus,
    Command,
    CandidateRegion,
    ActivePerceptionInsight,
)
from .candidate_evaluator import CandidateEvaluator
from .active_perception import ActivePerceptionEvaluator
from .scan_planner import ScanPlanner


class AutonomousMissionPlanner:
    """
    Autonomous Mission Planner for Solar Sentry.
    Translates Agent 8 cognitive decisions into concrete action sequences,
    manages active perception for uncertainty reduction, and enforces safety bounds.
    """

    def __init__(
        self,
        candidate_evaluator: Optional[CandidateEvaluator] = None,
        active_perception: Optional[ActivePerceptionEvaluator] = None,
    ):
        self.candidate_evaluator = candidate_evaluator or CandidateEvaluator()
        self.active_perception = active_perception or ActivePerceptionEvaluator()

    def plan_from_decision(
        self,
        cognitive_decision: Any,
        current_pan: int = 90,
        current_tilt: int = 0,
        candidate_qualities: Optional[Dict[str, float | Dict[str, Any]]] = None,
        perception_context: Optional[Dict[str, Any]] = None,
    ) -> Mission:
        """
        Primary entry point: Translates Agent 8 CognitiveDecision into an executable Mission.
        """
        # Extract decision string/enum
        if hasattr(cognitive_decision, "decision"):
            dec_val = cognitive_decision.decision
            dec_str = dec_val.value if hasattr(dec_val, "value") else str(dec_val)
        elif isinstance(cognitive_decision, dict):
            dec_str = str(cognitive_decision.get("decision", "OBSERVE"))
        else:
            dec_str = str(cognitive_decision)

        dec_upper = dec_str.upper()

        if dec_upper == "OBSERVE":
            return self.plan_observation_mission(
                current_pan=current_pan,
                current_tilt=current_tilt,
                candidate_qualities=candidate_qualities,
                perception_context=perception_context,
            )
        elif dec_upper == "SCAN":
            return self.plan_scan_mission(
                center_pan=current_pan if current_pan != 90 else 90,
                center_tilt=current_tilt if current_tilt > 20 else 80,
                perception_context=perception_context,
            )
        elif dec_upper == "WAIT":
            return self.plan_wait_mission(
                duration_sec=30.0,
                reason="Agent 8 cognitive decision: Environmental or solar conditions pending stabilization",
            )
        elif dec_upper == "SUSPEND":
            return self.plan_suspend_mission(
                reason="Agent 8 cognitive decision: Environmental suspension (precipitation or thermal limit)"
            )
        elif dec_upper == "SAFE":
            return self.plan_safe_mission(
                reason="Agent 8 cognitive decision: Critical hardware fault or comms failure interlock"
            )
        else:
            # Fallback to wait
            return self.plan_wait_mission(
                duration_sec=15.0,
                reason=f"Unrecognized decision type '{dec_str}', defaulting to WAIT",
            )

    def plan_observation_mission(
        self,
        current_pan: int = 90,
        current_tilt: int = 0,
        candidate_qualities: Optional[Dict[str, float | Dict[str, Any]]] = None,
        perception_context: Optional[Dict[str, Any]] = None,
    ) -> Mission:
        """
        Plans an autonomous observation mission:
        1. Checks active perception: is the perception state uncertain?
        2. Evaluates candidates (e.g. LEFT=0.61, CENTER=0.82, RIGHT=0.73).
        3. Selects optimal candidate and sequences the OBSERVE command.
        """
        mid = f"msn-obs-{uuid.uuid4().hex[:8]}"
        ctx = perception_context or {}

        # 1. Active Perception Check
        ap_insight = self.active_perception.evaluate(
            vision_uncertainty=float(ctx.get("vision_uncertainty", 0.05)),
            forecast_uncertainty=float(ctx.get("forecast_uncertainty", 0.05)),
            solar_disk_confidence=float(ctx.get("solar_disk_confidence", 0.95)),
            solar_disk_detected=bool(ctx.get("solar_disk_detected", True)),
            vision_quality=float(ctx.get("vision_quality", 0.80)),
            cloud_coverage=float(ctx.get("cloud_coverage", 0.05)),
        )

        # If active perception is triggered, convert to an exploratory active perception mission
        if ap_insight.triggered:
            return self.plan_active_perception_mission(
                center_pan=current_pan if current_pan != 90 else 90,
                center_tilt=current_tilt if current_tilt > 20 else 80,
                insight=ap_insight,
            )

        # 2. Candidate Region Evaluation
        if candidate_qualities:
            candidates = CandidateEvaluator.from_quality_dict(
                candidate_qualities, current_pan, current_tilt
            )
        else:
            # Default candidates if none explicitly provided
            candidates = [
                CandidateRegion(region_id="LEFT", pan=60, tilt=80, predicted_quality=0.61),
                CandidateRegion(region_id="CENTER", pan=90, tilt=82, predicted_quality=0.82),
                CandidateRegion(region_id="RIGHT", pan=120, tilt=80, predicted_quality=0.73),
            ]

        ranked_candidates = self.candidate_evaluator.rank_candidates(
            candidates, current_pan, current_tilt
        )
        selected = self.candidate_evaluator.select_best(
            ranked_candidates, current_pan, current_tilt, min_quality_threshold=0.50
        ) or ranked_candidates[0]

        objective = MissionObjective(
            name="Find best observation region",
            description=(
                f"Autonomous solar tracking targeting {selected.region_id} "
                f"(quality={selected.predicted_quality:.2f}, pan={selected.pan}°, tilt={selected.tilt}°)"
            ),
            target_quality_min=0.70,
            target_region=selected.region_id,
        )

        # 3. Action Sequencing
        cmd = Command(
            command_id=f"cmd-obs-{uuid.uuid4().hex[:6]}",
            command=ActionVerb.OBSERVE,
            pan=selected.pan,
            tilt=selected.tilt,
            speed=100,
        )

        action = MissionAction(
            action_id=f"act-obs-{uuid.uuid4().hex[:6]}",
            action_type=f"OBSERVE_{selected.region_id}",
            command=cmd,
            timeout_sec=8.0,
            max_retries=2,
        )

        mission = Mission(
            mission_id=mid,
            name="Solar Active Region Observation",
            objective=objective,
            mission_type=MissionType.OBSERVE,
            priority=50,
            actions=[action],
            candidates=ranked_candidates,
            selected_candidate=selected,
            status=MissionState.PENDING,
            timeout_sec=45.0,
            active_perception=ap_insight,
        )
        mission.log(f"Mission {mid} created. Selected region: {selected.region_id} (Pan={selected.pan}°, Tilt={selected.tilt}°)")
        return mission

    def plan_active_perception_mission(
        self,
        center_pan: int = 90,
        center_tilt: int = 80,
        insight: Optional[ActivePerceptionInsight] = None,
    ) -> Mission:
        """
        Plans an active perception mission when uncertainty is elevated.
        Sequences exploratory scan actions to resolve ambiguity.
        """
        mid = f"msn-active-perc-{uuid.uuid4().hex[:8]}"
        candidates, actions = ScanPlanner.plan_3pt_bracket(
            center_pan=center_pan,
            center_tilt=center_tilt,
            span_deg=25,
            speed=80,
        )

        obj = MissionObjective(
            name="Active Perception Uncertainty Reduction",
            description="Exploratory multi-point scan to resolve visual or forecast ambiguity",
            target_quality_min=0.60,
            active_perception_required=True,
        )

        mission = Mission(
            mission_id=mid,
            name="Active Perception Knowledge Acquisition",
            objective=obj,
            mission_type=MissionType.ACTIVE_PERCEPTION,
            priority=65,  # Higher than normal observation
            actions=actions,
            candidates=candidates,
            status=MissionState.PENDING,
            timeout_sec=30.0,
            active_perception=insight,
        )
        mission.log(f"Active perception mission {mid} planned: {insight.trigger_reason if insight else 'Uncertainty probe'}")
        return mission

    def plan_scan_mission(
        self,
        center_pan: int = 90,
        center_tilt: int = 80,
        perception_context: Optional[Dict[str, Any]] = None,
    ) -> Mission:
        """Plans a structured survey scan sweep."""
        mid = f"msn-scan-{uuid.uuid4().hex[:8]}"
        candidates, actions = ScanPlanner.plan_3pt_bracket(
            center_pan=center_pan,
            center_tilt=center_tilt,
            span_deg=30,
            speed=75,
        )

        obj = MissionObjective(
            name="Spatial Solar Disk Survey",
            description="3-point bracketing sweep to map local limb profile",
            target_quality_min=0.65,
        )

        mission = Mission(
            mission_id=mid,
            name="Solar Boundary Scan Sweep",
            objective=obj,
            mission_type=MissionType.SCAN,
            priority=50,
            actions=actions,
            candidates=candidates,
            status=MissionState.PENDING,
            timeout_sec=30.0,
        )
        mission.log(f"Scan mission {mid} planned with {len(actions)} sweep points.")
        return mission

    def plan_wait_mission(self, duration_sec: float = 30.0, reason: str = "") -> Mission:
        """Plans a stationary standby/wait mission."""
        mid = f"msn-wait-{uuid.uuid4().hex[:8]}"
        cmd = Command(
            command_id=f"cmd-wait-{uuid.uuid4().hex[:6]}",
            command=ActionVerb.SET_STATE,
            target_state="WAIT",
        )
        action = MissionAction(
            action_id=f"act-wait-{uuid.uuid4().hex[:6]}",
            action_type="HOLD_STANDBY",
            command=cmd,
            timeout_sec=max(5.0, duration_sec),
        )

        obj = MissionObjective(
            name="Stationary Standby Wait",
            description=reason or "Stationary monitoring while conditions stabilize",
        )

        mission = Mission(
            mission_id=mid,
            name="Observatory Standby Hold",
            objective=obj,
            mission_type=MissionType.WAIT,
            priority=40,
            actions=[action],
            status=MissionState.PENDING,
            timeout_sec=duration_sec + 10.0,
        )
        mission.log(f"Wait mission {mid} created: {reason}")
        return mission

    def plan_suspend_mission(self, reason: str = "") -> Mission:
        """Plans an emergency suspension and safe stow mission."""
        mid = f"msn-suspend-{uuid.uuid4().hex[:8]}"
        cmd = Command(
            command_id=f"cmd-suspend-{uuid.uuid4().hex[:6]}",
            command=ActionVerb.PARK,
            pan=90,
            tilt=0,
            target_state="SUSPEND",
        )
        action = MissionAction(
            action_id=f"act-suspend-{uuid.uuid4().hex[:6]}",
            action_type="EMERGENCY_SUSPEND_PARK",
            command=cmd,
            timeout_sec=4.0,
            max_retries=1,
        )

        obj = MissionObjective(
            name="Environmental Hazard Suspension",
            description=reason or "Immediate safe stow due to adverse environmental conditions",
        )

        mission = Mission(
            mission_id=mid,
            name="Observatory Environmental Suspension",
            objective=obj,
            mission_type=MissionType.SUSPEND,
            priority=90,  # High priority safety preemption
            actions=[action],
            status=MissionState.PENDING,
            timeout_sec=15.0,
        )
        mission.log(f"Suspension mission {mid} planned. Reason: {reason}")
        return mission

    def plan_safe_mission(self, reason: str = "") -> Mission:
        """Plans a fail-safe shutdown and emergency park mission."""
        mid = f"msn-safe-{uuid.uuid4().hex[:8]}"
        cmd = Command(
            command_id=f"cmd-safe-{uuid.uuid4().hex[:6]}",
            command=ActionVerb.EMERGENCY_STOP,
            pan=90,
            tilt=0,
            target_state="SAFE",
        )
        action = MissionAction(
            action_id=f"act-safe-{uuid.uuid4().hex[:6]}",
            action_type="EMERGENCY_SAFE_SHUTDOWN",
            command=cmd,
            timeout_sec=3.0,
            max_retries=1,
        )

        obj = MissionObjective(
            name="Hardware Fail-Safe Interlock",
            description=reason or "Critical hardware safety interlock",
        )

        mission = Mission(
            mission_id=mid,
            name="Emergency Fail-Safe Safe State",
            objective=obj,
            mission_type=MissionType.SAFE,
            priority=100,  # Absolute highest priority
            actions=[action],
            status=MissionState.PENDING,
            timeout_sec=10.0,
        )
        mission.log(f"Emergency safe mission {mid} planned. Reason: {reason}")
        return mission
