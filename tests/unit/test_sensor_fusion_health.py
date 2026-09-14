"""Comprehensive unit and integration tests for Solar Sentry Sensor Fusion & Health Anomaly AI (Agent 7).

Tests:
1. Sensor boundary validation and physical plausibility checks.
2. Per-sensor dynamic confidence scoring.
3. Cross-sensor physical consistency and thermodynamic checks.
4. Multimodal Bayesian/inverse-variance sensor fusion and uncertainty estimation.
5. Robust statistical anomaly detection (Median, MAD, Z-score).
6. Machine Learning anomaly scoring via Isolation Forest.
7. CUSUM calibration drift detection.
8. Communication link health, jitter, freshness, and timeout triggers.
9. Actuator telemetry tracking error, stall detection, and oscillation jitter.
10. Observatory health score (0-100) and authoritative state classification.
11. Degraded mode recommendations and root-cause evidence generation.
12. Simulated failures (DHT22 drop, BMP280 stale, rain stuck, comms timeout, sensor conflict).
13. Compatibility with Agent 8 Cognitive Decision Engine input contract.
14. Hardware-in-the-loop integration with Agent 1 Edge Simulator.
"""

import os
import sys
import time
import pytest
from datetime import datetime, timezone, timedelta

# Add root directory and firmware to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../firmware/mock_edge")))

from ai.health.schemas import (
    HealthState,
    FaultSeverity,
    AnomalyType,
    DegradedMode,
    ObservatoryHealthReport,
)
from ai.health.engine import ObservatoryHealthEngine
from ai.health.fault_injector import FaultInjector
from ai.health.cross_consistency import calculate_dew_point
from ai.health.fusion import calculate_vapor_pressure_deficit
from ai.decision.types import HealthFusionEvaluation
from edge_simulator import SolarSentryEdgeDevice


@pytest.fixture
def nominal_telemetry():
    """Generates a nominal, healthy telemetry payload."""
    return {
        "device_id": "esp32-sentry-01",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": 120,
        "temperature": 25.4,
        "humidity": 44.5,
        "pressure": 1013.25,
        "lux": 45000.0,
        "rain_raw": 3850,
        "rain_detected": False,
        "pan": 90,
        "tilt": 45,
        "state": "OBSERVE",
        "health": 100,
        "wifi_rssi": -62,
        "camera_online": True,
        "sensor_status": {
            "dht22": True,
            "bh1750": True,
            "bmp280": True,
            "rain": True
        },
        "firmware_version": "1.0.0"
    }


@pytest.fixture
def health_engine():
    return ObservatoryHealthEngine()


# ---------------------------------------------------------------------------
# 1. Nominal Operation & Health Scoring Tests
# ---------------------------------------------------------------------------

def test_nominal_observatory_health(health_engine, nominal_telemetry):
    """Verifies that flawless telemetry evaluates to HEALTHY state with score >= 85."""
    report = health_engine.process_telemetry(nominal_telemetry, bmp280_temp=25.2)

    assert report.health == HealthState.HEALTHY
    assert report.score >= 85
    assert report.confidence >= 0.85
    assert report.degraded_recommendation == DegradedMode.NORMAL_OPERATION
    assert report.fused_environment.primary_temp_source == "FUSED"
    assert len([a for a in report.anomalies if a.severity in [FaultSeverity.HIGH, FaultSeverity.CRITICAL]]) == 0


def test_dew_point_and_vpd_calculations():
    """Validates physical meteorological formulas for dew point and vapor pressure deficit."""
    # 25°C, 50% RH -> Dew point is approx 13.9°C
    dp = calculate_dew_point(25.0, 50.0)
    assert 13.5 <= dp <= 14.5

    # Vapor pressure deficit at 25°C, 50% RH
    vpd = calculate_vapor_pressure_deficit(25.0, 50.0)
    assert 1.4 <= vpd <= 1.8


# ---------------------------------------------------------------------------
# 2. Simulated Failure Scenarios (User Requirements)
# ---------------------------------------------------------------------------

def test_simulated_failure_dht22_disconnected(health_engine, nominal_telemetry):
    """Simulates DHT22 disconnection (-999 error code).

    Must gracefully fall back to BMP280 temperature, report DEGRADED health,
    and recommend USE_BMP280_TEMPERATURE.
    """
    faulty_telem = FaultInjector.inject_dht22_disconnected(nominal_telemetry)
    report = health_engine.process_telemetry(faulty_telem, bmp280_temp=24.8)

    assert report.health == HealthState.DEGRADED
    assert report.fused_environment.primary_temp_source == "BMP280"
    assert report.fused_environment.temperature == 24.8
    assert report.sensor_confidences["temperature"] == 0.0
    assert report.degraded_recommendation == DegradedMode.USE_BMP280_TEMPERATURE

    # Check root cause evidence
    causes = [r for r in report.root_cause_evidence if "DHT22" in r.suspected_component]
    assert len(causes) > 0
    assert "GPIO4" in causes[0].root_cause


def test_simulated_failure_bmp280_stale(health_engine, nominal_telemetry):
    """Simulates BMP280 pressure reading frozen invariant across consecutive samples."""
    # Feed 16 invariant samples
    stale_telem = FaultInjector.inject_bmp280_stale(nominal_telemetry, frozen_pressure=1013.25)

    last_report = None
    for _ in range(16):
        last_report = health_engine.process_telemetry(stale_telem, bmp280_temp=25.0)

    stale_anoms = [
        a for a in last_report.anomalies
        if a.type == AnomalyType.STUCK_STALE and a.sensor == "pressure"
    ]
    assert len(stale_anoms) > 0
    assert last_report.score < 100


def test_simulated_failure_rain_sensor_stuck_conflict(health_engine, nominal_telemetry):
    """Simulates rain sensor stuck wet while humidity is arid (18%) and sky is blazing (72k lux).

    Must detect CROSS_SENSOR_INCONSISTENCY and recommend OPTICAL_CONFIRMATION_REQUIRED.
    """
    faulty_telem = FaultInjector.inject_rain_sensor_stuck(nominal_telemetry, stuck_wet=True)
    report = health_engine.process_telemetry(faulty_telem, bmp280_temp=25.0)

    conflicts = [
        a for a in report.anomalies
        if a.type == AnomalyType.CROSS_SENSOR_INCONSISTENCY and a.sensor == "rain"
    ]
    assert len(conflicts) > 0
    assert report.degraded_recommendation == DegradedMode.OPTICAL_CONFIRMATION_REQUIRED

    causes = [r for r in report.root_cause_evidence if "Rain" in r.suspected_component]
    assert len(causes) > 0


def test_simulated_failure_communication_interruption(health_engine, nominal_telemetry):
    """Simulates communication interruption where last received packet is >30s old.

    Must classify observatory health as OFFLINE.
    """
    stale_comms = FaultInjector.inject_communication_interruption(nominal_telemetry, delay_seconds=36.0)
    report = health_engine.process_telemetry(stale_comms, bmp280_temp=25.0)

    assert report.health == HealthState.OFFLINE
    assert report.comms_health.heartbeat_stalled is True
    assert report.comms_health.freshness_seconds >= 35.0


def test_simulated_failure_inconsistent_sensors(health_engine, nominal_telemetry):
    """Simulates large discrepancy between DHT22 (42°C) and BMP280 (23°C).

    Must detect CROSS_SENSOR_INCONSISTENCY on temperature redundancy.
    """
    faulty_telem, bmp_temp = FaultInjector.inject_inconsistent_temperatures(
        nominal_telemetry, dht_temp=42.0, bmp_temp=23.0
    )
    report = health_engine.process_telemetry(faulty_telem, bmp280_temp=bmp_temp)

    inconsistencies = [
        a for a in report.anomalies
        if a.type == AnomalyType.CROSS_SENSOR_INCONSISTENCY and "temperature" in a.sensor
    ]
    assert len(inconsistencies) > 0
    # Both sensors are somewhat penalized in confidence
    assert report.sensor_confidences["temperature"] <= 0.7


# ---------------------------------------------------------------------------
# 3. Drift & Statistical Checks
# ---------------------------------------------------------------------------

def test_cusum_drift_detection(health_engine, nominal_telemetry):
    """Verifies that persistent statistical offset triggers CUSUM drift detection."""
    # Feed 20 baseline samples
    for _ in range(20):
        health_engine.process_telemetry(nominal_telemetry, bmp280_temp=25.0)

    # Now inject persistent upward drift on humidity (+25%)
    drifted_telem = FaultInjector.inject_humidity_drift(nominal_telemetry, drift_offset_pct=25.0)
    drift_detected = False

    for _ in range(10):
        rep = health_engine.process_telemetry(drifted_telem, bmp280_temp=25.0)
        if any(a.type == AnomalyType.DRIFT for a in rep.anomalies):
            drift_detected = True
            break

    assert drift_detected is True


def test_isolation_forest_scoring(health_engine, nominal_telemetry):
    """Verifies Isolation Forest scores normal vectors low and unphysical combinations high."""
    normal_score, is_norm_anom = health_engine.anomaly_suite.iso_forest.score(nominal_telemetry)
    assert normal_score < 0.6
    assert is_norm_anom is False

    # Outlier telemetry: freezing temp (-15°C) with 95% humidity and extreme 120,000 lux
    bizarre_telem = dict(nominal_telemetry)
    bizarre_telem["temperature"] = -15.0
    bizarre_telem["humidity"] = 98.0
    bizarre_telem["lux"] = 125000.0
    outlier_score, is_out_anom = health_engine.anomaly_suite.iso_forest.score(bizarre_telem)
    assert outlier_score > normal_score


# ---------------------------------------------------------------------------
# 4. Actuator Health Monitoring
# ---------------------------------------------------------------------------

def test_actuator_stall_detection(health_engine, nominal_telemetry):
    """Verifies actuator stall detection when pan target is 120° but telemetry remains 45°."""
    health_engine.command_actuator_target(pan=120, tilt=45)
    health_engine.actuator_monitor.command_time = time.time() - 8.0  # commanded 8 seconds ago

    stalled_telem = FaultInjector.inject_actuator_stall(nominal_telemetry, frozen_pan=45)

    # Process 6 iterations
    rep = None
    for _ in range(6):
        rep = health_engine.process_telemetry(stalled_telem, bmp280_temp=25.0)

    assert rep.actuator_health.stall_suspected is True
    assert any(a.sensor == "pan_servo" and a.type == AnomalyType.ACTUATOR_ANOMALY for a in rep.anomalies)


# ---------------------------------------------------------------------------
# 5. Agent 8 Contract Compatibility
# ---------------------------------------------------------------------------

def test_agent8_health_input_compatibility(health_engine, nominal_telemetry):
    """Verifies that to_health_fusion_evaluation() seamlessly instantiates Agent 8's HealthFusionEvaluation."""
    report = health_engine.process_telemetry(nominal_telemetry, bmp280_temp=25.0)
    agent8_dict = report.to_health_fusion_evaluation()

    # Must unpack cleanly into HealthFusionEvaluation Pydantic model
    agent8_eval = HealthFusionEvaluation(**agent8_dict)
    assert isinstance(agent8_eval.overall_health, float)
    assert agent8_eval.overall_health >= 0.8
    assert agent8_eval.is_healthy is True
    assert len(agent8_eval.failed_sensors) == 0
    assert agent8_eval.sensor_agreement_score >= 0.9


# ---------------------------------------------------------------------------
# 6. Hardware-In-The-Loop Integration with Agent 1 Edge Simulator
# ---------------------------------------------------------------------------

def test_hardware_in_the_loop_with_edge_simulator(health_engine):
    """Feeds streaming telemetry directly from SolarSentryEdgeDevice (Agent 1) into Agent 7."""
    edge_device = SolarSentryEdgeDevice(device_id="esp32-sentry-01")

    # Step simulation across 10 cycles
    for _ in range(10):
        edge_device.update(0.2)
        telemetry = edge_device.generate_telemetry()
        report = health_engine.process_telemetry(telemetry, bmp280_temp=telemetry["temperature"])

        assert isinstance(report, ObservatoryHealthReport)
        assert report.health in [HealthState.HEALTHY, HealthState.DEGRADED, HealthState.WARNING]
        assert 0 <= report.score <= 100
