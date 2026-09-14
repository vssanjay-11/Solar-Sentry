"""
Solar Sentry — Cognitive Decision Engine & XAI Test Suite
Agent 8: Cognitive Decision Engine + Explainable AI (XAI)
"""

import pytest
from ai.decision.types import (
    DecisionType,
    RiskLevel,
    OperationalMode,
    SafetyGate,
    CognitiveInput,
    VisionEvaluation,
    EnvironmentPrediction,
    HealthFusionEvaluation,
    EdgeTelemetryState,
)
from ai.decision.engine import CognitiveDecisionEngine


@pytest.fixture
def engine():
    return CognitiveDecisionEngine()


def test_user_request_example_case(engine):
    """
    Validates exact scenario given in the specification:
    Inputs:
      health = 0.96
      environment_quality = 0.83
      vision_quality = 0.79
      prediction_30m = 0.74
      rain = false
    Output:
      decision: OBSERVE
      confidence: ~0.91
      risk: LOW
      reasons: [
        "environment suitable",
        "sensor health normal",
        "image quality acceptable",
        "future conditions declining"
      ]
    """
    input_data = {
        "health": 0.96,
        "environment_quality": 0.83,
        "vision_quality": 0.79,
        "prediction_30m": 0.74,
        "rain": False
    }

    result = engine.evaluate(input_data)
    summary = result.to_summary_dict()

    assert summary["decision"] == "OBSERVE"
    assert summary["risk"] == "LOW"
    assert 0.88 <= summary["confidence"] <= 0.94

    expected_reasons = [
        "environment suitable",
        "sensor health normal",
        "image quality acceptable",
        "future conditions declining"
    ]
    for reason in expected_reasons:
        assert reason in summary["reasons"], f"Expected reason '{reason}' not found in {summary['reasons']}"


def test_rain_emergency_override(engine):
    """Rain detected on edge sensor must trigger immediate SUSPEND with CRITICAL risk."""
    cog_input = CognitiveInput(
        vision=VisionEvaluation(vision_quality=0.95),
        environment=EnvironmentPrediction(environment_quality=0.90),
        health=HealthFusionEvaluation(overall_health=0.98),
        edge=EdgeTelemetryState(rain_detected=True, rain_raw=1200)
    )

    decision = engine.evaluate(cog_input)

    assert decision.decision == DecisionType.SUSPEND
    assert decision.risk == RiskLevel.CRITICAL
    assert decision.mode == OperationalMode.SAFE_MODE
    assert decision.confidence >= 0.95
    assert decision.recommended_action.action == "EMERGENCY_PARK"
    assert decision.recommended_action.safe_stow_required is True
    assert any("rain" in r.lower() or "precipitation" in r.lower() for r in decision.reasons)
    assert decision.trace.gating_interlock == SafetyGate.RAIN_ACTIVE


def test_comms_timeout_safe_mode(engine):
    """Comms loss exceeding 30 seconds must trigger fail-safe SAFE mode."""
    cog_input = CognitiveInput(
        vision=VisionEvaluation(vision_quality=0.85),
        environment=EnvironmentPrediction(environment_quality=0.85),
        health=HealthFusionEvaluation(overall_health=0.95),
        edge=EdgeTelemetryState(rain_detected=False, comms_age_sec=42.5)
    )

    decision = engine.evaluate(cog_input)

    assert decision.decision == DecisionType.SAFE
    assert decision.risk == RiskLevel.CRITICAL
    assert decision.mode == OperationalMode.SAFE_MODE
    assert decision.confidence >= 0.95
    assert decision.recommended_action.action == "ENTER_SAFE_MODE"
    assert any("comms" in r.lower() or "heartbeat" in r.lower() for r in decision.reasons)
    assert decision.trace.gating_interlock == SafetyGate.COMMS_TIMEOUT


def test_critical_sensor_failure(engine):
    """Failure of a critical sensor (e.g. lux BH1750 or core failure) must trigger SAFE."""
    cog_input = CognitiveInput(
        vision=VisionEvaluation(vision_quality=0.85),
        environment=EnvironmentPrediction(environment_quality=0.85),
        health=HealthFusionEvaluation(
            overall_health=0.35,
            is_healthy=False,
            failed_sensors=["bh1750"]
        ),
        edge=EdgeTelemetryState(rain_detected=False)
    )

    decision = engine.evaluate(cog_input)

    assert decision.decision == DecisionType.SAFE
    assert decision.risk == RiskLevel.CRITICAL
    assert decision.mode == OperationalMode.SAFE_MODE
    assert any("hardware" in r.lower() or "critical fault" in r.lower() for r in decision.reasons)


def test_degraded_mode_operation(engine):
    """
    Failure of a non-critical sensor (e.g. BMP280 pressure sensor) should transition
    observatory to DEGRADED mode without halting observations when skies are clear.
    """
    cog_input = CognitiveInput(
        vision=VisionEvaluation(vision_quality=0.85, solar_disk_detected=True),
        environment=EnvironmentPrediction(environment_quality=0.85, prediction_30m=0.82),
        health=HealthFusionEvaluation(
            overall_health=0.78,
            is_healthy=True,
            failed_sensors=["bmp280"],
            degraded_sensors=["pressure"]
        ),
        edge=EdgeTelemetryState(rain_detected=False)
    )

    decision = engine.evaluate(cog_input)

    assert decision.mode == OperationalMode.DEGRADED
    assert decision.decision == DecisionType.OBSERVE
    assert decision.risk in (RiskLevel.LOW, RiskLevel.MODERATE)
    assert any("degraded" in r.lower() for r in decision.reasons)


def test_conflicting_sensors_uncertainty(engine):
    """Severe conflict among sensors (low agreement) forces UNCERTAIN mode and conservative decision."""
    cog_input = CognitiveInput(
        vision=VisionEvaluation(vision_quality=0.75),
        environment=EnvironmentPrediction(environment_quality=0.75),
        health=HealthFusionEvaluation(
            overall_health=0.80,
            sensor_agreement_score=0.40  # Conflict!
        ),
        edge=EdgeTelemetryState(rain_detected=False)
    )

    decision = engine.evaluate(cog_input)

    assert decision.mode == OperationalMode.UNCERTAIN
    assert decision.decision == DecisionType.WAIT
    assert any("conflicting" in r.lower() for r in decision.reasons)


def test_high_uncertainty_handling(engine):
    """High epistemic uncertainty across upstream models prevents rash observation."""
    cog_input = CognitiveInput(
        vision=VisionEvaluation(vision_quality=0.75, uncertainty=0.65),
        environment=EnvironmentPrediction(environment_quality=0.75, uncertainty=0.60),
        health=HealthFusionEvaluation(overall_health=0.90, uncertainty=0.10),
        edge=EdgeTelemetryState(rain_detected=False)
    )

    decision = engine.evaluate(cog_input)

    assert decision.mode == OperationalMode.UNCERTAIN
    assert decision.decision == DecisionType.WAIT
    assert decision.total_uncertainty > 0.35
    assert any("uncertainty" in r.lower() for r in decision.reasons)


def test_poor_image_cloud_transit_wait(engine):
    """Poor image quality with cloud passage while prediction indicates upcoming clearance triggers WAIT."""
    cog_input = CognitiveInput(
        vision=VisionEvaluation(
            vision_quality=0.35,
            cloud_coverage=0.75,
            solar_disk_detected=True
        ),
        environment=EnvironmentPrediction(
            environment_quality=0.55,
            prediction_15m=0.70,
            prediction_30m=0.80  # Clearing expected
        ),
        health=HealthFusionEvaluation(overall_health=0.95),
        edge=EdgeTelemetryState(rain_detected=False)
    )

    decision = engine.evaluate(cog_input)

    assert decision.decision == DecisionType.WAIT
    assert any("cloud" in r.lower() or "image quality poor" in r.lower() for r in decision.reasons)
    assert decision.recommended_action.action in ("HOLD_TRACKING_STANDBY", "HOLD_AND_REASSESS")


def test_excellent_conditions(engine):
    """Optimal conditions produce OBSERVE with maximum confidence and lowest risk."""
    cog_input = CognitiveInput(
        vision=VisionEvaluation(vision_quality=0.96, cloud_coverage=0.02, clarity_score=0.95),
        environment=EnvironmentPrediction(environment_quality=0.94, prediction_30m=0.92),
        health=HealthFusionEvaluation(overall_health=0.98, sensor_agreement_score=0.98),
        edge=EdgeTelemetryState(rain_detected=False, lux=62000.0)
    )

    decision = engine.evaluate(cog_input)

    assert decision.decision == DecisionType.OBSERVE
    assert decision.confidence >= 0.93
    assert decision.risk == RiskLevel.LOW
    assert decision.mode == OperationalMode.NORMAL
    assert any("optimal" in r.lower() for r in decision.reasons)


def test_solar_disk_missing_triggers_scan(engine):
    """When daylight is strong and environment is clear but solar disk is missing, engine orders SCAN."""
    cog_input = CognitiveInput(
        vision=VisionEvaluation(
            vision_quality=0.40,
            solar_disk_detected=False,  # Disk lost
            cloud_coverage=0.05
        ),
        environment=EnvironmentPrediction(
            environment_quality=0.85,
            prediction_30m=0.85
        ),
        health=HealthFusionEvaluation(overall_health=0.95),
        edge=EdgeTelemetryState(rain_detected=False, lux=55000.0)
    )

    decision = engine.evaluate(cog_input)

    assert decision.decision == DecisionType.SCAN
    assert decision.recommended_action.action == "ACTIVE_SOLAR_SEARCH"
    assert any("solar disk not acquired" in r.lower() for r in decision.reasons)


def test_xai_explanations_attributions_and_trace(engine):
    """Verifies that decision explanation, factor attributions, counterfactuals, and trace are complete."""
    cog_input = CognitiveInput(
        vision=VisionEvaluation(vision_quality=0.72),
        environment=EnvironmentPrediction(environment_quality=0.80, prediction_30m=0.65),
        health=HealthFusionEvaluation(overall_health=0.95),
        edge=EdgeTelemetryState(rain_detected=False)
    )

    decision = engine.evaluate(cog_input)

    # Check Trace
    assert decision.trace.trace_id.startswith("trace-")
    assert "SAFETY" in decision.trace.hierarchy_levels_evaluated
    assert "HEALTH" in decision.trace.hierarchy_levels_evaluated
    assert "OBSERVATION_QUALITY" in decision.trace.hierarchy_levels_evaluated
    assert len(decision.trace.steps) >= 5

    # Check Explanation Attributions
    assert len(decision.explanation.positive_factors) > 0
    assert any(f.feature == "overall_health" for f in decision.explanation.positive_factors)

    # Check Counterfactuals
    assert len(decision.explanation.counterfactuals) > 0


def test_cognitive_state_memory_and_reset(engine):
    """Verifies history tracking, streak counting, and state reset."""
    engine.reset_state()
    assert len(engine.decision_history) == 0
    assert engine.consecutive_observations == 0

    cog_input = CognitiveInput(
        vision=VisionEvaluation(vision_quality=0.90),
        environment=EnvironmentPrediction(environment_quality=0.90),
        health=HealthFusionEvaluation(overall_health=0.95),
        edge=EdgeTelemetryState(rain_detected=False)
    )

    engine.evaluate(cog_input)
    engine.evaluate(cog_input)

    assert len(engine.decision_history) == 2
    assert engine.consecutive_observations == 2

    # Interrupt with rain
    rain_input = CognitiveInput(edge=EdgeTelemetryState(rain_detected=True))
    engine.evaluate(rain_input)

    assert len(engine.decision_history) == 3
    assert engine.consecutive_observations == 0
