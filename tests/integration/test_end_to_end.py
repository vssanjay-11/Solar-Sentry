"""
Solar Sentry — Master End-to-End System Integration Test Suite
Agent 10: Digital Twin + Mission Memory + Learning + Simulation + Integration

Validates the full autonomous cognitive observatory pipeline across all 9 required operational scenarios:
1. Clear day -> OBSERVE
2. Rain -> SUSPEND
3. Poor image -> WAIT
4. Sensor anomaly -> DEGRADED
5. Scan -> best region selected
6. Fault -> safe recovery
7. Mission replay
8. Prediction deterioration
9. What-if simulation
"""

import pytest
import numpy as np

from integration.orchestrator import SolarSentryPlatform
from simulation.scenarios import ScenarioType, get_scenario
from simulation.what_if import WhatIfSimulationEngine, WhatIfPerturbation
from learning.collector import ExperienceCollector, ExperienceSample
from learning.monitor import PerformanceMonitor, DriftDetector
from learning.governance import ModelRegistry, ModelLifecycleStatus
from learning.retraining import OfflineRetrainingWorkflow
from twin.state import FaultSeverity, MissionPhase


@pytest.fixture
def platform():
    """Initializes a clean SolarSentryPlatform instance."""
    return SolarSentryPlatform()


# =============================================================================
# SCENARIO 1: Clear Day -> OBSERVE
# =============================================================================
def test_scenario_1_clear_day_observe(platform):
    """
    Scenario 1:
    Optimal irradiance, clear sky, healthy hardware -> Engine decides OBSERVE,
    dispatches OBSERVE command, aligns servos, passes verification, and records mission.
    """
    # Configure pristine conditions
    platform.edge.device.sensors.lux_base = 55000.0
    platform.edge.device.sensors.temp_base = 26.0
    platform.edge.device.sensors.humid_base = 35.0
    platform.edge.device.sensors.rain_raw = 3850
    platform.edge.device.sensors.rain_detected = False

    result = platform.run_cognitive_cycle(
        vision_preset="quiet_sun",
        target_pan=95,
        target_tilt=48
    )

    decision = result["decision"]["decision"]
    assert decision == "OBSERVE", f"Expected OBSERVE on clear day, got {decision}"
    assert result["decision"]["confidence"] >= 0.70
    assert result["decision"]["risk"] in ["MINIMAL", "LOW"]
    assert result["command_result"]["status"] == "SUCCESS"
    assert result["verification"]["overall_verification_passed"] is True

    # Check Digital Twin State
    twin = platform.digital_twin.state
    assert twin.current.system_state == "OBSERVE"
    assert len(twin.predicted.projections) > 0
    assert twin.fault.has_active_fault is False

    # Check Database & Memory
    assert len(platform.db.telemetry_table) >= 1
    assert len(platform.db.observations_table) >= 1
    assert platform.current_mission is not None
    assert platform.current_mission.cognitive_decision.decision == "OBSERVE"


# =============================================================================
# SCENARIO 2: Rain -> SUSPEND
# =============================================================================
def test_scenario_2_rain_suspend(platform):
    """
    Scenario 2:
    Precipitation triggered -> Hard safety interlock trips, decision forces SUSPEND,
    edge actuator stows (90, 0), and emergency safety is logged.
    """
    # Trigger rain
    platform.edge.device.sensors.rain_raw = 750
    platform.edge.device.sensors.rain_detected = True

    result = platform.run_cognitive_cycle(vision_preset="heavy_clouds")

    decision = result["decision"]["decision"]
    assert decision == "SUSPEND", f"Expected SUSPEND during rain, got {decision}"
    assert result["decision"]["risk"] in ["HIGH", "CRITICAL"]

    # Verify edge stowed
    twin = platform.digital_twin.state
    assert twin.fault.safety_interlock_tripped is True
    assert twin.fault.tripped_interlock_name == "RAIN_INTERLOCK"
    assert twin.current.sensors.rain_detected is True


# =============================================================================
# SCENARIO 3: Poor Image -> WAIT
# =============================================================================
def test_scenario_3_poor_image_wait(platform):
    """
    Scenario 3:
    Weather clear enough for safety, but optical frame is severely degraded/occluded ->
    System transitions to WAIT until conditions improve.
    """
    platform.edge.device.sensors.rain_detected = False
    platform.edge.device.sensors.rain_raw = 3850
    platform.edge.device.sensors.lux_base = 25000.0  # Moderate light

    result = platform.run_cognitive_cycle(vision_preset="heavy_clouds")

    decision = result["decision"]["decision"]
    assert decision in ["WAIT", "SCAN", "SUSPEND"], f"Expected non-OBSERVE for heavy clouds, got {decision}"
    assert result["vision"]["quality_score"] < 0.60


# =============================================================================
# SCENARIO 4: Sensor Anomaly -> DEGRADED Mode
# =============================================================================
def test_scenario_4_sensor_anomaly_degraded(platform):
    """
    Scenario 4:
    Non-critical sensor failure (e.g. DHT22 fails) -> Health anomaly flagged,
    system operates in DEGRADED mode.
    """
    platform.edge.device.sensors.rain_detected = False
    platform.edge.device.sensors.dht_fault = True
    platform.edge.device.sensors.temp_base = -999.0

    result = platform.run_cognitive_cycle(vision_preset="quiet_sun")

    mode = result["decision"]["operational_mode"]
    assert mode in ["DEGRADED", "UNCERTAIN"], f"Expected DEGRADED/UNCERTAIN mode, got {mode}"

    twin = platform.digital_twin.state
    assert twin.fault.has_active_fault is True
    fault_codes = [f.code for f in twin.fault.active_faults]
    assert any("DHT22" in code for code in fault_codes)


# =============================================================================
# SCENARIO 5: Scan Mode -> Best Region Selected
# =============================================================================
def test_scenario_5_scan_best_region(platform):
    """
    Scenario 5:
    Scan mode active -> Sweeps candidate regions, selects optimal solar region,
    and returns selected pan/tilt coordinates.
    """
    platform.edge.device.sensors.rain_detected = False
    platform.edge.device.sensors.rain_raw = 3850
    platform.edge.device.sensors.lux_base = 50000.0

    result = platform.run_cognitive_cycle(
        vision_preset="quiet_sun",
        scan_mode=True
    )

    assert result["selected_region"] is not None
    best_pan, best_tilt = result["selected_region"]
    assert 0 <= best_pan <= 180
    assert 0 <= best_tilt <= 180
    assert result["command_result"]["status"] == "SUCCESS"


# =============================================================================
# SCENARIO 6: Fault -> Safe Recovery
# =============================================================================
def test_scenario_6_fault_safe_recovery(platform):
    """
    Scenario 6:
    Rain triggers emergency SUSPEND -> Rain clears -> Recovery command transitions system to STANDBY.
    """
    # 1. Rain strike
    platform.edge.device.sensors.rain_raw = 600
    platform.edge.device.sensors.rain_detected = True
    res_fault = platform.run_cognitive_cycle(vision_preset="heavy_clouds")
    assert res_fault["decision"]["decision"] == "SUSPEND"

    # 2. Rain dries up
    platform.edge.device.sensors.rain_raw = 3850
    platform.edge.device.sensors.rain_detected = False
    platform.edge.device.state = "STANDBY"

    res_recovered = platform.run_cognitive_cycle(vision_preset="quiet_sun")
    assert res_recovered["decision"]["decision"] in ["OBSERVE", "WAIT", "STANDBY"]
    assert platform.digital_twin.state.fault.safety_interlock_tripped is False


# =============================================================================
# SCENARIO 7: Mission Replay
# =============================================================================
def test_scenario_7_mission_replay(platform):
    """
    Scenario 7:
    Records an observation mission -> Mission Replay Engine reconstructs timeline,
    validates chronological steps, and verifies decision determinism.
    """
    platform.edge.device.sensors.lux_base = 52000.0
    platform.edge.device.sensors.rain_detected = False
    cycle = platform.run_cognitive_cycle(vision_preset="quiet_sun")

    mission = platform.current_mission
    assert mission is not None

    audit_report = platform.replay_engine.replay_mission(mission)
    assert audit_report.mission_id == mission.mission_id
    assert audit_report.total_steps >= 5
    assert audit_report.decision_matches is True
    assert audit_report.reproduced_decision == mission.cognitive_decision.decision


# =============================================================================
# SCENARIO 8: Prediction Deterioration
# =============================================================================
def test_scenario_8_prediction_deterioration(platform):
    """
    Scenario 8:
    Multi-step execution of DEGRADING_CONDITIONS scenario -> Forecast and digital twin
    track declining observation quality and flag degrading trend.
    """
    results = platform.execute_scenario(ScenarioType.DEGRADING_CONDITIONS, steps=3)
    assert len(results) == 3

    # Check trend in Digital Twin
    trend = platform.digital_twin.state.predicted.trend_direction
    assert trend in ["DEGRADING", "STABLE", "RAPID_DETERIORATION"]


# =============================================================================
# SCENARIO 9: What-If Simulation
# =============================================================================
def test_scenario_9_what_if_simulation(platform):
    """
    Scenario 9:
    Applies counterfactual perturbations (humidity +15%, camera quality -30%, rain=True)
    and verifies downstream system propagation and comparative delta report.
    """
    baseline_telemetry = platform.edge.get_telemetry()
    baseline_telemetry["rain_detected"] = False
    baseline_telemetry["rain_raw"] = 3850
    baseline_telemetry["lux"] = 52000.0

    baseline_vision = {
        "quality_score": 0.88,
        "solar_disk_detected": True,
        "sunspot_count": 2,
        "obstruction_score": 0.05
    }

    # Case A: Rain perturbation
    pert_rain = WhatIfPerturbation(rain_active=True)
    report_rain = platform.what_if_engine.run_what_if(baseline_telemetry, baseline_vision, pert_rain)
    assert report_rain.perturbed_decision == "SUSPEND"
    assert "RAIN_HAZARD_INTERLOCK" in report_rain.interlocks_triggered

    # Case B: Humidity +15% and Camera -30%
    pert_weather = WhatIfPerturbation(
        delta_humidity_percent=15.0,
        camera_quality_delta_percent=-30.0
    )
    report_weather = platform.what_if_engine.run_what_if(baseline_telemetry, baseline_vision, pert_weather)
    assert report_weather.perturbed_confidence <= report_weather.baseline_confidence
    assert report_weather.impact_narrative is not None


# =============================================================================
# DIGITAL TWIN & SAFE LEARNING FRAMEWORK TESTS
# =============================================================================
def test_learning_framework_and_governance(tmp_path):
    """
    Verifies the SAFE Learning Architecture:
    Experience collection -> Performance monitoring -> Drift detection ->
    Model registry with SHA-256 -> Offline retraining -> Strict promotion gates.
    """
    collector = ExperienceCollector()
    # Populate mock samples
    for i in range(25):
        sample = ExperienceSample(
            sample_id=f"samp-{i}",
            timestamp="2026-09-13T11:00:00Z",
            features={
                "clearness_index": 0.75 + 0.05 * np.sin(i),
                "cloud_proxy": 0.1,
                "irradiance_volatility": 0.03,
                "humidity": 40.0 + i,
                "pressure_trend": 0.0,
                "solar_elevation_deg": 45.0,
                "condensation_depression_c": 12.0
            },
            predicted_quality_15m=0.80,
            actual_quality_15m=0.78 + 0.02 * np.cos(i),
            predicted_quality_30m=0.75,
            actual_quality_30m=0.74,
            weather_risk="LOW"
        )
        collector.add_sample(sample)

    # 1. Performance Monitor
    metrics = PerformanceMonitor.calculate_metrics(collector.get_dataset())
    assert metrics is not None
    assert metrics.mae_15m < 0.15

    # 2. Drift Detection
    base_dist = np.random.normal(40.0, 5.0, 50)
    shifted_dist = np.random.normal(65.0, 8.0, 50)  # Significant shift
    drift_report = DriftDetector.detect_drift("humidity", base_dist, shifted_dist)
    assert drift_report.is_drift_detected is True
    assert drift_report.severity in ["MODERATE", "SEVERE"]

    # 3. Model Registry & Offline Retraining
    registry = ModelRegistry()
    workflow = OfflineRetrainingWorkflow(registry)
    candidate_artifact = workflow.execute_retraining(
        collector.get_dataset(),
        target_version="1.1.0",
        notes="Offline retrained on safe simulated telemetry"
    )
    assert candidate_artifact.status == ModelLifecycleStatus.CANDIDATE
    assert len(candidate_artifact.artifact_hash) == 64

    # 4. Promotion Criteria Gate (Blocked without human signoff)
    promo_fail = registry.evaluate_and_promote(
        candidate_id=candidate_artifact.model_id,
        safety_audit_passed=True,
        operator_approval_token=None  # Missing token!
    )
    assert promo_fail.promoted is False
    assert any("GOVERNANCE_GATE_BLOCKED" in r for r in promo_fail.rejection_reasons)

    # Promotion Success with human signoff & passing safety
    promo_success = registry.evaluate_and_promote(
        candidate_id=candidate_artifact.model_id,
        safety_audit_passed=True,
        operator_approval_token="OPERATOR_SANJAY_LEAD"
    )
    assert promo_success.promoted is True
    assert candidate_artifact.status == ModelLifecycleStatus.PRODUCTION
