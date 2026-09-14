"""Current observation condition assessment, quality scoring, and risk categorization.
Agent 6 Ownership.
"""

from typing import Optional, List, Tuple, Dict, Any

from ai.environment.config import (
    CONDENSATION_DEPRESSION_CRITICAL,
    CONDENSATION_DEPRESSION_WARNING,
    HUMIDITY_HIGH_RISK_PERCENT,
    HUMIDITY_CRITICAL_PERCENT,
    MIN_OBSERVABLE_ELEVATION_DEG,
    HORIZON_ELEVATION_DEG,
    QUALITY_WEIGHT_CLEARNESS,
    QUALITY_WEIGHT_STABILITY,
    QUALITY_WEIGHT_SEEING,
    QUALITY_WEIGHT_VISION_HINT,
)
from ai.environment.schemas import (
    TelemetryInput,
    EnvironmentalFeatures,
    TrendSummary,
    VisionHints,
    RiskLevel,
    RiskFactor,
    TrendDirection,
)


def score_current_observation_quality(
    features: EnvironmentalFeatures,
    telemetry: TelemetryInput,
    trends: TrendSummary,
    vision: Optional[VisionHints] = None
) -> Tuple[float, Dict[str, float]]:
    """Calculates the composite observation quality score in range [0.0, 1.0].
    
    Returns:
        Tuple[float, Dict[str, float]]: (composite_score, component_breakdown)
    """
    # 1. Absolute safety gates
    if telemetry.rain_detected:
        return 0.0, {"clearness": 0.0, "seeing": 0.0, "stability": 0.0, "vision": 0.0, "reason": "RAIN_ACTIVE"}

    if features.solar_elevation_deg <= HORIZON_ELEVATION_DEG:
        return 0.0, {"clearness": 0.0, "seeing": 0.0, "stability": 0.0, "vision": 0.0, "reason": "SUN_BELOW_HORIZON"}

    # 2. Clearness quality score (Q_clearness)
    # kt ~ 1.0 is ideal. kt < 0.2 is overcast. kt > 1.2 may be cloud edge reflection enhancement.
    kt = features.clearness_index
    if kt >= 0.85:
        q_clearness = min(1.0, 0.85 + (kt - 0.85) * 0.15) if kt <= 1.15 else max(0.7, 1.0 - (kt - 1.15) * 0.5)
    elif kt >= 0.50:
        q_clearness = 0.50 + (kt - 0.50) / 0.35 * 0.35
    elif kt >= 0.20:
        q_clearness = 0.15 + (kt - 0.20) / 0.30 * 0.35
    else:
        q_clearness = max(0.0, kt / 0.20 * 0.15)

    # Elevation ramp: low elevations (< 10 deg) suffer higher atmospheric extinction
    if features.solar_elevation_deg < MIN_OBSERVABLE_ELEVATION_DEG:
        elevation_factor = max(0.1, features.solar_elevation_deg / MIN_OBSERVABLE_ELEVATION_DEG)
        q_clearness *= elevation_factor

    # 3. Seeing / thermal turbulence quality (Q_seeing)
    q_seeing = features.thermal_seeing_index

    # 4. Microclimate stability quality (Q_stability)
    q_stability = 1.0
    if trends.lux_trend == TrendDirection.VOLATILE:
        q_stability -= 0.40
    elif trends.lux_trend == TrendDirection.FALLING:
        q_stability -= 0.15

    if trends.pressure_trend == TrendDirection.FALLING:
        q_stability -= 0.20

    if features.precipitation_imminence > 0.4:
        q_stability -= (features.precipitation_imminence - 0.4) * 0.5

    q_stability = max(0.0, min(1.0, q_stability))

    # 5. Vision hint integration (if provided by Agent 5)
    q_vision = 1.0
    has_vision = False
    if vision is not None:
        if vision.image_quality is not None:
            q_vision = vision.image_quality
            has_vision = True
        elif vision.cloud_cover is not None:
            q_vision = max(0.0, 1.0 - vision.cloud_cover)
            has_vision = True
        if vision.solar_disk_visible is False:
            q_vision = min(q_vision, 0.1)
            has_vision = True

    # 6. Weighted blending
    if has_vision:
        composite = (
            QUALITY_WEIGHT_CLEARNESS * q_clearness +
            QUALITY_WEIGHT_SEEING * q_seeing +
            QUALITY_WEIGHT_STABILITY * q_stability +
            QUALITY_WEIGHT_VISION_HINT * q_vision
        )
    else:
        # Re-normalize weights when vision is absent
        w_sum = QUALITY_WEIGHT_CLEARNESS + QUALITY_WEIGHT_SEEING + QUALITY_WEIGHT_STABILITY
        composite = (
            (QUALITY_WEIGHT_CLEARNESS / w_sum) * q_clearness +
            (QUALITY_WEIGHT_SEEING / w_sum) * q_seeing +
            (QUALITY_WEIGHT_STABILITY / w_sum) * q_stability
        )

    # Penalize if condensation is imminent
    if features.dew_point_depression <= CONDENSATION_DEPRESSION_CRITICAL:
        composite *= 0.3
    elif features.dew_point_depression <= CONDENSATION_DEPRESSION_WARNING:
        composite *= 0.7

    composite = round(max(0.0, min(1.0, composite)), 3)
    
    breakdown = {
        "clearness": round(q_clearness, 3),
        "seeing": round(q_seeing, 3),
        "stability": round(q_stability, 3),
        "vision": round(q_vision, 3) if has_vision else 1.0
    }
    return composite, breakdown


def assess_environmental_risks(
    features: EnvironmentalFeatures,
    telemetry: TelemetryInput,
    trends: TrendSummary,
    vision: Optional[VisionHints] = None
) -> Tuple[RiskLevel, List[RiskFactor]]:
    """Evaluates environmental threats and returns overall risk level and active risk factors."""
    factors: List[RiskFactor] = []

    # 1. Physical Rain
    if telemetry.rain_detected:
        factors.append(RiskFactor.RAIN_DETECTED)
        return RiskLevel.CRITICAL, factors

    # 2. Nighttime
    if features.solar_elevation_deg <= HORIZON_ELEVATION_DEG:
        factors.append(RiskFactor.NIGHT_TIME)
        return RiskLevel.CRITICAL, factors

    # 3. Imminent Precipitation
    if features.precipitation_imminence >= 0.70:
        factors.append(RiskFactor.PRECIPITATION_IMMINENT)
    elif features.precipitation_imminence >= 0.45:
        factors.append(RiskFactor.PRECIPITATION_IMMINENT)

    # 4. Condensation Threat
    if features.dew_point_depression <= CONDENSATION_DEPRESSION_CRITICAL:
        factors.append(RiskFactor.CONDENSATION_RISK)
    elif features.dew_point_depression <= CONDENSATION_DEPRESSION_WARNING:
        factors.append(RiskFactor.CONDENSATION_RISK)

    # 5. Humidity Risk
    if telemetry.humidity >= HUMIDITY_CRITICAL_PERCENT:
        factors.append(RiskFactor.HIGH_HUMIDITY)
    elif telemetry.humidity >= HUMIDITY_HIGH_RISK_PERCENT:
        factors.append(RiskFactor.HIGH_HUMIDITY)

    # 6. Rapid Cloud / Sky Volatility
    if trends.lux_trend == TrendDirection.VOLATILE or trends.lux_change_rate_per_min < -300.0:
        factors.append(RiskFactor.RAPID_CLOUD_DEVELOPMENT)

    # 7. Thermal Turbulence
    if features.thermal_seeing_index < 0.55:
        factors.append(RiskFactor.ATMOSPHERIC_TURBULENCE)

    # 8. Low Solar Altitude
    if 0.0 < features.solar_elevation_deg < MIN_OBSERVABLE_ELEVATION_DEG:
        factors.append(RiskFactor.LOW_SOLAR_ALTITUDE)

    # 9. Hardware sensor degradation
    if telemetry.sensor_status and any(not ok for ok in telemetry.sensor_status.values()):
        factors.append(RiskFactor.SENSOR_DEGRADED)

    # Risk level classification
    if RiskFactor.PRECIPITATION_IMMINENT in factors and features.precipitation_imminence >= 0.70:
        overall_level = RiskLevel.CRITICAL
    elif RiskFactor.CONDENSATION_RISK in factors and features.dew_point_depression <= CONDENSATION_DEPRESSION_CRITICAL:
        overall_level = RiskLevel.CRITICAL
    elif len(factors) >= 3 or RiskFactor.PRECIPITATION_IMMINENT in factors or RiskFactor.CONDENSATION_RISK in factors:
        overall_level = RiskLevel.HIGH
    elif len(factors) >= 1:
        overall_level = RiskLevel.MEDIUM
    else:
        overall_level = RiskLevel.LOW

    return overall_level, factors
