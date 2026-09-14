"""Unit and Integration Tests for Agent 6: Environment Intelligence & Observation Quality Prediction.
"""

import os
import sys
import json
import pytest
from datetime import datetime, timezone

# Add repository root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from ai.environment.config import BASELINE_MODEL_VERSION, ML_MODEL_VERSION
from ai.environment.schemas import (
    TelemetryInput,
    VisionHints,
    RiskLevel,
    RiskFactor,
    TrendDirection,
)
from ai.environment.features import (
    calculate_solar_position,
    calculate_clear_sky_lux,
    calculate_dew_point,
    calculate_thermal_seeing_index,
    calculate_precipitation_imminence,
    extract_environmental_features,
)
from ai.environment.trends import TelemetryHistoryBuffer
from ai.environment.assessor import (
    score_current_observation_quality,
    assess_environmental_risks,
)
from ai.environment.models.physics_baseline import PhysicsBaselineModel
from ai.environment.models.ml_model import GradientBoostingQualityModel
from ai.environment.predictor import EnvironmentPredictor, predict_observation_quality
from ai.environment.simulator import EnvironmentalSimulator
from ai.environment.evaluation import evaluate_model_on_scenarios


@pytest.fixture
def clear_telemetry_snapshot():
    """Returns a realistic midday clear sky telemetry snapshot."""
    return {
        "device_id": "esp32-sentry-01",
        "timestamp": "2026-09-13T10:30:00Z",
        "temperature": 27.5,
        "humidity": 45.0,
        "pressure": 1013.25,
        "lux": 65000.0,
        "rain_raw": 3800,
        "rain_detected": False,
        "pan": 90,
        "tilt": 60,
        "state": "OBSERVE",
        "health": 100,
        "sensor_status": {"dht22": True, "bh1750": True, "bmp280": True, "rain": True},
        "firmware_version": "1.0.0"
    }


def test_solar_position_and_clear_sky_lux():
    """Verifies solar astronomical positioning and physical illuminance calculation."""
    # Midday near equinox
    dt_noon = datetime(2026, 9, 21, 6, 30, 0, tzinfo=timezone.utc)
    elev, zenith = calculate_solar_position(dt_noon, lat_deg=28.6, lon_deg=77.2)
    assert elev > 40.0
    assert zenith < 50.0

    clear_lux = calculate_clear_sky_lux(elev)
    assert clear_lux > 40000.0

    # Night test: sun below horizon
    dt_night = datetime(2026, 9, 21, 18, 30, 0, tzinfo=timezone.utc)
    elev_night, _ = calculate_solar_position(dt_night, lat_deg=28.6, lon_deg=77.2)
    assert elev_night < 0.0
    assert calculate_clear_sky_lux(elev_night) == 0.0


def test_dew_point_and_condensation_imminence():
    """Verifies Magnus formula dew point computation and condensation detection."""
    # T=25C, RH=50% -> Dew point ~ 13.9C
    dp = calculate_dew_point(25.0, 50.0)
    assert 13.0 <= dp <= 14.5

    # T=15C, RH=95% -> Dew point ~ 14.2C, depression < 1.0C (Critical Condensation)
    dp_high = calculate_dew_point(15.0, 95.0)
    depression = 15.0 - dp_high
    assert depression < 1.5


def test_precipitation_imminence_index():
    """Verifies multi-factor precipitation imminence indicator."""
    # Benign clear conditions
    benign = calculate_precipitation_imminence(
        humidity_pct=40.0,
        pressure_change_per_hour=0.1,
        clearness_index=0.95
    )
    assert benign < 0.2

    # Impending storm conditions (RH 92%, pressure dropping -2.5 hPa/hr, dark clouds)
    storm = calculate_precipitation_imminence(
        humidity_pct=92.0,
        pressure_change_per_hour=-2.5,
        clearness_index=0.15,
        rain_raw=2000
    )
    assert storm > 0.7


def test_historical_trend_analyzer():
    """Verifies rolling buffer trend direction and derivative calculations."""
    buffer = TelemetryHistoryBuffer(max_samples=20)
    base_time = datetime(2026, 9, 13, 10, 0, 0, tzinfo=timezone.utc)

    for i in range(10):
        buffer.add_snapshot({
            "timestamp": base_time.isoformat(),
            "temperature": 25.0 + i * 0.2,
            "humidity": 50.0 - i * 0.5,
            "pressure": 1013.0 - i * 0.3,
            "lux": 60000.0 - i * 500.0,
            "rain_detected": False
        })

    trends = buffer.analyze_trends()
    assert trends.pressure_trend == TrendDirection.FALLING
    assert trends.lux_trend == TrendDirection.FALLING
    assert trends.temperature_trend == TrendDirection.RISING


def test_current_observation_quality_scoring(clear_telemetry_snapshot):
    """Verifies that clear conditions yield a high quality score."""
    tel = TelemetryInput(**clear_telemetry_snapshot)
    feats = extract_environmental_features(tel)
    trends = TelemetryHistoryBuffer().analyze_trends()
    
    score, breakdown = score_current_observation_quality(feats, tel, trends)
    assert 0.70 <= score <= 1.0
    assert breakdown["clearness"] > 0.7
    assert breakdown["stability"] > 0.7


def test_rain_emergency_zeroes_quality(clear_telemetry_snapshot):
    """Verifies that active rain immediately zeroes quality and raises CRITICAL risk."""
    clear_telemetry_snapshot["rain_detected"] = True
    clear_telemetry_snapshot["rain_raw"] = 400

    tel = TelemetryInput(**clear_telemetry_snapshot)
    feats = extract_environmental_features(tel)
    trends = TelemetryHistoryBuffer().analyze_trends()

    score, _ = score_current_observation_quality(feats, tel, trends)
    risk, factors = assess_environmental_risks(feats, tel, trends)

    assert score == 0.0
    assert risk == RiskLevel.CRITICAL
    assert RiskFactor.RAIN_DETECTED in factors


def test_condensation_triggers_critical_risk(clear_telemetry_snapshot):
    """Verifies condensation threat lowers quality and flags risk."""
    clear_telemetry_snapshot["temperature"] = 14.0
    clear_telemetry_snapshot["humidity"] = 96.0  # Dew point depression < 1.0 C

    tel = TelemetryInput(**clear_telemetry_snapshot)
    feats = extract_environmental_features(tel)
    trends = TelemetryHistoryBuffer().analyze_trends()

    score, _ = score_current_observation_quality(feats, tel, trends)
    risk, factors = assess_environmental_risks(feats, tel, trends)

    assert RiskFactor.CONDENSATION_RISK in factors
    assert risk in [RiskLevel.HIGH, RiskLevel.CRITICAL]
    assert score < 0.5


def test_physics_baseline_multi_horizon_predictions(clear_telemetry_snapshot):
    """Verifies baseline multi-horizon predictions (15m, 30m, 60m)."""
    model = PhysicsBaselineModel()
    tel = TelemetryInput(**clear_telemetry_snapshot)
    feats = extract_environmental_features(tel)
    trends = TelemetryHistoryBuffer().analyze_trends()
    score, _ = score_current_observation_quality(feats, tel, trends)

    preds = model.predict_all_horizons(score, tel, feats, trends, horizons=(15, 30, 60))
    
    assert "15m" in preds
    assert "30m" in preds
    assert "60m" in preds
    for h in ["15m", "30m", "60m"]:
        assert 0.0 <= preds[h] <= 1.0


def test_public_interface_contract(clear_telemetry_snapshot):
    """Verifies clean functional facade conforms to contract schema."""
    result = predict_observation_quality(
        state=clear_telemetry_snapshot,
        horizons=(15, 30, 60)
    )

    # Check required keys
    assert "current_quality" in result
    assert "predictions" in result
    assert "confidence" in result
    assert "risk" in result
    assert "risk_factors" in result
    assert "trend" in result
    assert "model_version" in result
    assert "timestamp" in result

    # Check value types and bounds
    assert 0.0 <= result["current_quality"] <= 1.0
    assert 0.0 <= result["confidence"] <= 1.0
    assert result["risk"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    assert "15m" in result["predictions"]
    assert "30m" in result["predictions"]
    assert "60m" in result["predictions"]


def test_optional_vision_hints_integration(clear_telemetry_snapshot):
    """Verifies optional Agent 5 optical hints adjust the quality score."""
    # Without vision hints
    res_clean = predict_observation_quality(state=clear_telemetry_snapshot)

    # With high optical image quality
    res_good_vision = predict_observation_quality(
        state=clear_telemetry_snapshot,
        vision_hints={"image_quality": 0.95, "cloud_cover": 0.05, "solar_disk_visible": True}
    )

    # With heavy cloud obstruction from vision
    res_bad_vision = predict_observation_quality(
        state=clear_telemetry_snapshot,
        vision_hints={"image_quality": 0.15, "cloud_cover": 0.90, "solar_disk_visible": False}
    )

    assert res_good_vision["current_quality"] >= res_bad_vision["current_quality"]


def test_sensor_degradation_reduces_confidence(clear_telemetry_snapshot):
    """Verifies degraded sensor hardware lowers prediction confidence."""
    # Healthy
    healthy_res = predict_observation_quality(state=clear_telemetry_snapshot)

    # Degraded sensor
    degraded_state = dict(clear_telemetry_snapshot)
    degraded_state["sensor_status"] = {"dht22": False, "bh1750": True, "bmp280": True, "rain": True}
    degraded_res = predict_observation_quality(state=degraded_state)

    assert degraded_res["confidence"] < healthy_res["confidence"]


def test_environmental_simulator_and_evaluation():
    """Verifies weather scenario simulation generator and evaluation harness."""
    stream = EnvironmentalSimulator.generate_scenario("THUNDERSTORM_SQUALL", duration_minutes=150, step_seconds=60)
    assert len(stream) == 150
    # Last records must reflect rain onset
    assert stream[-1]["rain_detected"] is True
    assert stream[-1]["state"] == "SUSPEND"

    # Run evaluation on baseline
    baseline = PhysicsBaselineModel()
    metrics = evaluate_model_on_scenarios(baseline, scenarios=["CLEAR_DAY"], horizons=(15, 30))
    assert "15m" in metrics
    assert "30m" in metrics
    assert metrics["15m"]["mae"] < 0.20


def test_gradient_boosting_ml_model_training_and_serialization(tmp_path):
    """Verifies fitting, predicting, saving, and loading the Scikit-Learn ML Model."""
    X, y = EnvironmentalSimulator.build_training_dataset(num_scenarios_each=1, horizons=(15, 30))
    assert X.shape[0] > 50

    ml_model = GradientBoostingQualityModel()
    assert ml_model.is_ready is False

    ml_model.fit(X, y)
    assert ml_model.is_ready is True
    assert ml_model.model_version == ML_MODEL_VERSION

    # Test persistence
    model_file = str(tmp_path / "test_model.joblib")
    ml_model.save(model_file)
    assert os.path.exists(model_file)

    loaded_model = GradientBoostingQualityModel()
    success = loaded_model.load(model_file)
    assert success is True
    assert loaded_model.is_ready is True
