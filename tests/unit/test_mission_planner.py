"""Unit tests for Solar Sentry Autonomous Mission Planner & Active Perception (Agent 9).

Validates:
1. Candidate evaluation & selection (e.g. LEFT=0.61, CENTER=0.82, RIGHT=0.73 -> SELECT CENTER -> PAN=90, TILT=82).
2. End-to-end successful mission execution & verification (quality_before=0.71, quality_after=0.86 -> SUCCESS).
3. Action timeout watchdog and graceful failure handling.
4. Transient action failure with automatic retry up to max_retries.
5. Degraded environment quality response.
6. Emergency suspension (Safety strictly overrides mission optimization; rain or hardware trip aborts mission & parks safe).
7. Safe recovery checklist and transition back to STANDBY.
8. Active perception scan selection triggered by elevated epistemic uncertainty.
9. Mission scheduler priority queue and preemption.
10. Schema compliance with docs/contracts/MissionPlan.json & docs/contracts/MissionResult.json.
"""

import os
import sys
import pytest
from datetime import datetime, timezone

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from mission import (
    AutonomousMissionPlanner,
    MissionExecutor,
    MissionScheduler,
    SimulatedCommandDispatcher,
    CandidateEvaluator,
    ActivePerceptionEvaluator,
    ActionVerifier,
    SafeRecoveryManager,
    Mission,
    MissionType,
    MissionState,
    ActionVerb,
    ActionStatus,
    VerificationStatus,
    Command,
    CommandResult,
    CandidateRegion,
)
from firmware.mock_edge.edge_simulator import SolarSentryEdgeDevice


@pytest.fixture
def edge_simulator():
    """Provides a clean Agent 1 ESP32 emulator instance."""
    return SolarSentryEdgeDevice(device_id="esp32-agent9-test")


@pytest.fixture
def dispatcher(edge_simulator):
    """Provides a simulated command dispatcher connected to the edge emulator."""
    return SimulatedCommandDispatcher(edge_device=edge_simulator)


@pytest.fixture
def planner():
    """Provides an autonomous mission planner."""
    return AutonomousMissionPlanner()


@pytest.fixture
def executor(dispatcher):
    """Provides a mission executor with real verification and safe recovery."""
    return MissionExecutor(dispatcher=dispatcher)


@pytest.fixture
def scheduler(executor):
    """Provides a mission scheduler."""
    return MissionScheduler(executor=executor)


# =============================================================================
# 1. Candidate Evaluation & Example Mission (User Specification)
# =============================================================================

def test_candidate_evaluation_and_selection(planner):
    """
    Validates exact user example:
    Candidates:
      LEFT: quality=0.61
      CENTER: quality=0.82
      RIGHT: quality=0.73
    Planner:
      SELECT CENTER
      Command: PAN=90, TILT=82
    """
    candidate_qualities = {
        "LEFT": 0.61,
        "CENTER": 0.82,
        "RIGHT": 0.73,
    }

    mission = planner.plan_observation_mission(
        current_pan=90,
        current_tilt=0,
        candidate_qualities=candidate_qualities,
    )

    assert mission.selected_candidate is not None
    assert mission.selected_candidate.region_id == "CENTER"
    assert mission.selected_candidate.pan == 90
    assert mission.selected_candidate.tilt == 82
    assert mission.selected_candidate.predicted_quality == 0.82

    # Verify generated command
    assert len(mission.actions) == 1
    action = mission.actions[0]
    cmd = action.command
    assert cmd.command == ActionVerb.OBSERVE
    assert cmd.pan == 90
    assert cmd.tilt == 82


def test_successful_mission_execution_and_verification(planner, executor):
    """
    Validates full end-to-end execution of the user example:
    Command: PAN=90, TILT=82
    After action:
      quality_before = 0.71
      quality_after = 0.86
    Verification:
      SUCCESS
    """
    candidate_qualities = {
        "LEFT": 0.61,
        "CENTER": 0.82,
        "RIGHT": 0.73,
    }

    mission = planner.plan_observation_mission(
        current_pan=90,
        current_tilt=0,
        candidate_qualities=candidate_qualities,
    )

    result = executor.execute_mission(
        mission=mission,
        quality_before=0.71,
        quality_after=0.86,
    )

    assert result.status == MissionState.COMPLETED
    assert result.actions_count == 1
    assert result.successful_actions == 1
    assert result.failed_actions == 0

    # Verification checks
    ver = result.verification_summary
    assert ver is not None
    assert ver["status"] == "SUCCESS"
    assert ver["converged"] is True
    assert ver["quality_before"] == 0.71
    assert ver["quality_after"] == 0.86
    assert abs(ver["delta_quality"] - 0.15) < 1e-4
    assert ver["pan_actual"] == 90
    assert ver["tilt_actual"] == 82


# =============================================================================
# 2. Action Timeout Watchdog
# =============================================================================

def test_action_timeout_handling(planner, dispatcher, executor):
    """Verifies that an edge response timeout triggers TIMED_OUT and halts gracefully."""
    mission = planner.plan_observation_mission(
        current_pan=90,
        current_tilt=0,
        candidate_qualities={"CENTER": 0.85},
    )

    # Inject timeout in dispatcher
    dispatcher.inject_timeout(enable=True)

    result = executor.execute_mission(
        mission=mission,
        quality_before=0.70,
        quality_after=0.70,
    )

    assert result.status == MissionState.FAILED
    assert result.failed_actions == 1
    assert "timed out" in result.failure_reason.lower()


# =============================================================================
# 3. Failed Action with Retries
# =============================================================================

def test_action_failure_and_retry(planner, dispatcher, executor):
    """Verifies automatic action retrying upon transient failure."""
    mission = planner.plan_observation_mission(
        current_pan=90,
        current_tilt=0,
        candidate_qualities={"CENTER": 0.85},
    )
    mission.actions[0].max_retries = 2

    # Inject a failure that will be consumed on first attempt
    dispatcher.inject_failure(error_type="EXECUTION_ERROR")

    result = executor.execute_mission(
        mission=mission,
        quality_before=0.70,
        quality_after=0.85,
    )

    # Should have retried and succeeded on attempt 2
    assert result.status == MissionState.COMPLETED
    assert mission.actions[0].retry_count == 1


# =============================================================================
# 4. Degraded Environment Response
# =============================================================================

def test_degraded_environment_verification(planner, executor):
    """
    Verifies that when observation quality drops unexpectedly below threshold,
    the verifier detects quality degradation.
    """
    mission = planner.plan_observation_mission(
        current_pan=90,
        current_tilt=0,
        candidate_qualities={"CENTER": 0.82},
    )
    # Set high quality requirement
    mission.objective.target_quality_min = 0.80

    # Simulate severe degradation post-action
    result = executor.execute_mission(
        mission=mission,
        quality_before=0.75,
        quality_after=0.45,  # Cloud rolled in
    )

    assert result.status == MissionState.FAILED
    ver = result.verification_summary
    assert ver["status"] == "DEGRADED"
    assert ver["delta_quality"] == -0.30


# =============================================================================
# 5. Emergency Suspension (Safety Strictly Overrides Optimization)
# =============================================================================

def test_emergency_suspension_on_rain_interlock(planner, dispatcher, executor):
    """
    Validates that if rain precipitation appears:
    1. Mission is immediately aborted.
    2. Emergency park (pan=90, tilt=0) is commanded.
    3. Failure reason is logged.
    """
    # Trigger rain detection on mock edge simulator
    dispatcher.device.sensors.rain_raw = 1200
    dispatcher.device.sensors.rain_detected = True
    dispatcher.device.state = "SUSPEND"

    mission = planner.plan_observation_mission(
        current_pan=90,
        current_tilt=0,
        candidate_qualities={"CENTER": 0.90},
    )

    result = executor.execute_mission(
        mission=mission,
        quality_before=0.80,
        quality_after=0.85,
    )

    assert result.status == MissionState.ABORTED
    assert result.safe_recovery_executed is True
    assert "rain" in result.failure_reason.lower()

    # Verify edge device stowed to safe position
    telem = dispatcher.device.generate_telemetry()
    assert telem["pan"] == 90
    assert telem["tilt"] == 0
    assert telem["state"] == "SUSPEND"


def test_pre_execution_safety_trip(planner, executor):
    """Safety interlock active prior to execution prevents any dispatch."""
    mission = planner.plan_observation_mission()
    result = executor.execute_mission(mission, safety_interlock_active=True)

    assert result.status == MissionState.ABORTED
    assert result.safe_recovery_executed is True
    assert "safety interlock" in result.failure_reason.lower()


# =============================================================================
# 6. Safe Recovery Verification
# =============================================================================

def test_safe_recovery_flow(dispatcher, edge_simulator):
    """
    Verifies that recovery from SUSPEND / SAFE into STANDBY:
    - Is blocked while rain or hazard is active
    - Succeeds once environmental conditions clear
    """
    recovery_mgr = SafeRecoveryManager(dispatcher)

    # 1. Blocked when rain active
    rainy_telem = edge_simulator.generate_telemetry()
    rainy_telem["rain_detected"] = True
    ready, blockers = recovery_mgr.check_recovery_readiness(rainy_telem)
    assert ready is False
    assert any("rain" in b.lower() or "moisture" in b.lower() for b in blockers)

    # 2. Succeeds when dry and clear
    edge_simulator.sensors.rain_raw = 3800
    edge_simulator.sensors.rain_detected = False
    edge_simulator.state = "STANDBY"
    clean_telem = edge_simulator.generate_telemetry()

    success, msg = recovery_mgr.execute_recovery(clean_telem)
    assert success is True
    assert "completed successfully" in msg


# =============================================================================
# 7. Active Perception: Scan Selection under Uncertainty
# =============================================================================

def test_active_perception_uncertainty_trigger(planner):
    """
    'The current image is uncertain, therefore perform a scan.'
    When epistemic uncertainty is high, planner chooses active perception scan
    rather than blindly executing a fixed observation.
    """
    uncertain_context = {
        "vision_uncertainty": 0.42,  # > threshold 0.30
        "forecast_uncertainty": 0.35,
        "solar_disk_confidence": 0.60,  # < threshold 0.70
        "solar_disk_detected": True,
        "vision_quality": 0.55,
    }

    mission = planner.plan_from_decision(
        cognitive_decision="OBSERVE",
        current_pan=90,
        current_tilt=80,
        perception_context=uncertain_context,
    )

    # Planner must have selected ACTIVE_PERCEPTION instead of fixed OBSERVE
    assert mission.mission_type == MissionType.ACTIVE_PERCEPTION
    assert mission.active_perception is not None
    assert mission.active_perception.triggered is True
    assert "uncertain" in mission.active_perception.trigger_reason.lower()

    # Must have generated exploratory scan actions
    assert len(mission.actions) == 3
    assert all(a.command.command == ActionVerb.SCAN for a in mission.actions)


def test_active_perception_information_gain():
    """Verifies information gain computation post-probe."""
    evaluator = ActivePerceptionEvaluator()
    insight = evaluator.evaluate(vision_uncertainty=0.45)
    assert insight.triggered is True

    # Scan executed, uncertainty dropped to 0.10
    updated = evaluator.record_post_probe(insight, uncertainty_after=0.10)
    assert updated.information_gain == 0.35
    assert updated.uncertainty_after == 0.10


# =============================================================================
# 8. Mission Scheduler Priority & Preemption
# =============================================================================

def test_mission_scheduler_priority_and_preemption(planner, scheduler):
    """
    Verifies that the scheduler executes higher-priority missions first,
    and preempts observation missions with emergency/safety missions.
    """
    obs_mission = planner.plan_observation_mission(
        candidate_qualities={"CENTER": 0.80}
    )
    obs_mission.priority = 50

    safe_mission = planner.plan_safe_mission(reason="Hardware watchdog triggered")
    safe_mission.priority = 100

    # Submit routine observation first, then high-priority safe mission
    scheduler.submit_mission(obs_mission)
    scheduler.submit_mission(safe_mission)

    # First step should execute SAFE mission due to higher priority
    res1 = scheduler.step()
    assert res1.mission_id == safe_mission.mission_id

    # Second step should execute observation mission
    res2 = scheduler.step()
    assert res2.mission_id == obs_mission.mission_id


# =============================================================================
# 9. Schema & Contract Compliance
# =============================================================================

def test_mission_plan_and_result_schema_fields(planner, executor):
    """Verifies that MissionPlan and MissionResult contain all contract fields."""
    mission = planner.plan_observation_mission(
        candidate_qualities={"LEFT": 0.60, "CENTER": 0.85, "RIGHT": 0.70}
    )
    plan_dict = mission.to_plan_dict()

    # Required by MissionPlan.json
    plan_required = [
        "mission_id", "mission_type", "priority", "objective",
        "status", "actions", "created_at"
    ]
    for k in plan_required:
        assert k in plan_dict, f"Missing required plan key: {k}"

    result = executor.execute_mission(mission, quality_before=0.70, quality_after=0.88)
    res_dict = result.to_dict()

    # Required by MissionResult.json
    result_required = [
        "mission_id", "objective", "status", "total_duration_sec",
        "actions_count", "successful_actions", "failed_actions",
        "verification_summary", "timestamp"
    ]
    for k in result_required:
        assert k in res_dict, f"Missing required result key: {k}"


# =============================================================================
# 10. Agent 8 Cognitive Decision Integration
# =============================================================================

def test_agent8_cognitive_decision_integration(planner):
    """Verifies seamless consumption of Agent 8's CognitiveDecision output."""
    from ai.decision.engine import CognitiveDecisionEngine

    engine = CognitiveDecisionEngine()
    input_data = {
        "health": 0.96,
        "environment_quality": 0.83,
        "vision_quality": 0.79,
        "prediction_30m": 0.74,
        "rain": False,
    }
    cog_decision = engine.evaluate(input_data)

    mission = planner.plan_from_decision(
        cognitive_decision=cog_decision,
        current_pan=90,
        current_tilt=0,
        candidate_qualities={"LEFT": 0.65, "CENTER": 0.85, "RIGHT": 0.72},
    )

    assert mission.mission_type == MissionType.OBSERVE
    assert mission.selected_candidate.region_id == "CENTER"
    assert mission.actions[0].command.pan == 90
    assert mission.actions[0].command.tilt == 82

