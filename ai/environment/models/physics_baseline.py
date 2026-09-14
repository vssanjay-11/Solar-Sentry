"""Physics-informed rule-based baseline model for multi-horizon observation quality forecasting.
Agent 6 Ownership.

Operates with high fidelity even when zero historical training data is available.
Incorporates:
- Astronomical solar position progression across +15m, +30m, +60m.
- Extrapolation of barometric pressure, humidity, and lux trends.
- Future dew-point depression convergence (condensation risk forecasting).
- Precipitation imminence dynamics.
"""

import math
from datetime import datetime, timezone, timedelta
from typing import Optional

from ai.environment.config import (
    BASELINE_MODEL_VERSION,
    DEFAULT_LATITUDE,
    DEFAULT_LONGITUDE,
    HORIZON_ELEVATION_DEG,
    MIN_OBSERVABLE_ELEVATION_DEG,
    CONDENSATION_DEPRESSION_CRITICAL,
)
from ai.environment.schemas import (
    TelemetryInput,
    EnvironmentalFeatures,
    TrendSummary,
    VisionHints,
    TrendDirection,
)
from ai.environment.features import calculate_solar_position, calculate_clear_sky_lux
from ai.environment.models.base import ObservationQualityModel


class PhysicsBaselineModel(ObservationQualityModel):
    """Physics-informed baseline forecasting model (Version 1.0.0)."""

    def __init__(self, lat_deg: float = DEFAULT_LATITUDE, lon_deg: float = DEFAULT_LONGITUDE):
        self.lat_deg = lat_deg
        self.lon_deg = lon_deg

    @property
    def model_version(self) -> str:
        return BASELINE_MODEL_VERSION

    @property
    def is_ready(self) -> bool:
        return True

    def predict_horizon(
        self,
        current_quality: float,
        telemetry: TelemetryInput,
        features: EnvironmentalFeatures,
        trends: TrendSummary,
        horizon_minutes: int,
        vision: Optional[VisionHints] = None
    ) -> float:
        """Projects observation quality forward by horizon_minutes."""
        # 1. Hard safety: Active rain detected
        if telemetry.rain_detected:
            # Active rain typically persists for at least 15-45 minutes
            if horizon_minutes <= 15:
                return 0.0
            elif horizon_minutes <= 30:
                return 0.05 if trends.pressure_trend == TrendDirection.RISING else 0.0
            else:
                return 0.15 if trends.pressure_trend == TrendDirection.RISING else 0.0

        # Parse current time and compute future time
        try:
            dt = datetime.fromisoformat(str(telemetry.timestamp).replace("Z", "+00:00"))
        except Exception:
            dt = datetime.now(timezone.utc)

        future_dt = dt + timedelta(minutes=horizon_minutes)

        # 2. Astronomical progression: Future solar elevation
        future_elevation, _ = calculate_solar_position(future_dt, self.lat_deg, self.lon_deg)
        if future_elevation <= HORIZON_ELEVATION_DEG:
            return 0.0  # Sun sets below horizon

        # 3. Solar geometry and low-altitude factors
        # Current quality is already normalized by clear-sky lux (kt).
        # We only apply elevation scaling when transitioning near the horizon (< 10 deg).
        elevation_scale = 1.0
        if future_elevation < MIN_OBSERVABLE_ELEVATION_DEG:
            elevation_scale = max(0.0, future_elevation / MIN_OBSERVABLE_ELEVATION_DEG)
        elif features.solar_elevation_deg < MIN_OBSERVABLE_ELEVATION_DEG:
            # Morning rise: exiting low elevation constraint
            elevation_scale = min(1.0, future_elevation / max(1.0, features.solar_elevation_deg))

        # 4. Clearness trend persistence & cloud decay/build
        # Extrapolate clearness index forward
        decay_rate = 0.0
        if trends.lux_trend == TrendDirection.FALLING:
            decay_rate += 0.003 * horizon_minutes
        elif trends.lux_trend == TrendDirection.VOLATILE:
            decay_rate += 0.002 * horizon_minutes

        # Approaching front / squall penalty
        if trends.pressure_trend == TrendDirection.FALLING:
            # More negative rate -> faster quality decay
            p_drop = abs(trends.pressure_change_hpa_per_hour)
            decay_rate += (p_drop / 5.0) * (horizon_minutes / 60.0)

        # Pre-rain imminence decay
        if features.precipitation_imminence > 0.4:
            decay_rate += (features.precipitation_imminence * 0.4) * (horizon_minutes / 30.0)

        # 5. Future condensation risk
        # Narrowing dew point depression
        future_depression = features.dew_point_depression
        if trends.humidity_trend == TrendDirection.RISING:
            humidity_rise_rate = trends.humidity_change_pct_per_hour / 60.0  # % per min
            future_depression -= (humidity_rise_rate * horizon_minutes * 0.15)

        condensation_penalty = 0.0
        if future_depression <= CONDENSATION_DEPRESSION_CRITICAL:
            condensation_penalty = 0.45 * (horizon_minutes / 30.0)

        # 6. Future vision hint projection (e.g. cloud cover trend)
        vision_decay = 0.0
        if vision is not None and vision.cloud_cover is not None and vision.cloud_cover > 0.4:
            vision_decay = (vision.cloud_cover - 0.4) * 0.25 * (horizon_minutes / 60.0)

        # 7. Composite forward projection
        forecast = (current_quality * (1.0 - decay_rate) - condensation_penalty - vision_decay) * elevation_scale

        # Handle rising conditions (e.g. morning clearing)
        if trends.lux_trend == TrendDirection.RISING and trends.pressure_trend != TrendDirection.FALLING:
            boost = 0.003 * horizon_minutes
            forecast = min(1.0, forecast + boost)

        # Low solar altitude constraint in future
        if future_elevation < MIN_OBSERVABLE_ELEVATION_DEG:
            forecast *= max(0.1, future_elevation / MIN_OBSERVABLE_ELEVATION_DEG)

        return max(0.0, min(1.0, forecast))
