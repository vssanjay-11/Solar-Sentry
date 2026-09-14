"""Data schemas and types for Environment Intelligence and Observation Quality Prediction.
Agent 6 Ownership.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict


class RiskLevel(str, Enum):
    """Overall environmental risk level for solar observation."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TrendDirection(str, Enum):
    """Directional trend classification for meteorological parameters."""
    RISING = "RISING"
    FALLING = "FALLING"
    STEADY = "STEADY"
    VOLATILE = "VOLATILE"


class RiskFactor(str, Enum):
    """Specific environmental risk factors contributing to elevated risk."""
    RAIN_DETECTED = "RAIN_DETECTED"
    PRECIPITATION_IMMINENT = "PRECIPITATION_IMMINENT"
    CONDENSATION_RISK = "CONDENSATION_RISK"
    HIGH_HUMIDITY = "HIGH_HUMIDITY"
    RAPID_CLOUD_DEVELOPMENT = "RAPID_CLOUD_DEVELOPMENT"
    ATMOSPHERIC_TURBULENCE = "ATMOSPHERIC_TURBULENCE"
    LOW_SOLAR_ALTITUDE = "LOW_SOLAR_ALTITUDE"
    NIGHT_TIME = "NIGHT_TIME"
    SENSOR_DEGRADED = "SENSOR_DEGRADED"


class VisionHints(BaseModel):
    """Optional optical and image quality indicators provided by Agent 5."""
    model_config = ConfigDict(extra="ignore")

    image_quality: Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="Overall optical image quality score (0.0 to 1.0) from Agent 5"
    )
    cloud_cover: Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="Estimated fractional cloud cover / obstruction index (0.0=clear, 1.0=overcast)"
    )
    solar_disk_visible: Optional[bool] = Field(
        default=None,
        description="Whether solar disk was successfully localized by Agent 5"
    )


class TelemetryInput(BaseModel):
    """Standardized environment input snapshot.
    Supports either direct edge telemetry or normalized backend states.
    """
    model_config = ConfigDict(extra="ignore")

    temperature: float = Field(..., description="Ambient temperature in degrees Celsius")
    humidity: float = Field(..., description="Relative humidity percentage (may be negative sentinel on sensor failure)")
    pressure: float = Field(..., description="Barometric pressure in hPa")
    lux: float = Field(..., description="Ambient illuminance in Lux")
    rain_raw: Optional[int] = Field(default=3500, description="Raw 12-bit ADC rain sensor reading")
    rain_detected: bool = Field(default=False, description="Physical rain detection flag")
    timestamp: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 UTC timestamp"
    )
    device_id: Optional[str] = Field(default="esp32-sentry-01", description="Device identifier")
    sensor_status: Optional[Dict[str, bool]] = Field(
        default=None,
        description="Health flags for individual sensors (dht22, bh1750, bmp280, rain)"
    )


class EnvironmentalFeatures(BaseModel):
    """Engineered meteorological and physical features used by prediction models."""
    model_config = ConfigDict(extra="ignore")

    solar_elevation_deg: float = Field(..., description="Solar elevation angle above horizon in degrees")
    solar_zenith_deg: float = Field(..., description="Solar zenith angle in degrees")
    clear_sky_lux: float = Field(..., description="Theoretical clear-sky lux at current solar elevation")
    clearness_index: float = Field(..., ge=0.0, description="Ratio of measured lux to theoretical clear-sky lux")
    dew_point: float = Field(..., description="Calculated dew point in degrees Celsius")
    dew_point_depression: float = Field(..., description="Margin between ambient temp and dew point (T - Tdew)")
    pressure_delta_15m: float = Field(default=0.0, description="Rate of barometric pressure change (hPa / 15m)")
    pressure_delta_60m: float = Field(default=0.0, description="Rate of barometric pressure change (hPa / 60m)")
    lux_rate_of_change: float = Field(default=0.0, description="Rate of lux change (lux / min)")
    thermal_seeing_index: float = Field(..., ge=0.0, le=1.0, description="Atmospheric seeing quality index (1.0=steady, 0.0=turbulent)")
    precipitation_imminence: float = Field(..., ge=0.0, le=1.0, description="Estimated probability index of imminent precipitation")


class TrendSummary(BaseModel):
    """Historical trends of critical environmental parameters."""
    model_config = ConfigDict(extra="ignore")

    lux_trend: TrendDirection = Field(default=TrendDirection.STEADY)
    pressure_trend: TrendDirection = Field(default=TrendDirection.STEADY)
    humidity_trend: TrendDirection = Field(default=TrendDirection.STEADY)
    temperature_trend: TrendDirection = Field(default=TrendDirection.STEADY)
    lux_change_rate_per_min: float = Field(default=0.0)
    pressure_change_hpa_per_hour: float = Field(default=0.0)
    humidity_change_pct_per_hour: float = Field(default=0.0)


class ObservationQualityAssessment(BaseModel):
    """Structured output contract for Observation Quality Prediction.
    Consumed by Agent 8 (Cognitive Decision Engine).
    """
    model_config = ConfigDict(extra="ignore")

    current_quality: float = Field(
        ..., ge=0.0, le=1.0,
        description="Current composite observation quality score (0.0=unusable, 1.0=ideal)"
    )
    predictions: Dict[str, float] = Field(
        ...,
        description="Predicted observation quality scores across time horizons (e.g. {'15m': 0.82, '30m': 0.74, '60m': 0.51})"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0,
        description="Confidence score in the prediction based on sensor validity, trend volatility, and model uncertainty"
    )
    risk: RiskLevel = Field(
        ...,
        description="Overall environmental risk classification (LOW, MEDIUM, HIGH, CRITICAL)"
    )
    risk_factors: List[RiskFactor] = Field(
        default_factory=list,
        description="List of active environmental risk factors detected"
    )
    trend: TrendSummary = Field(
        default_factory=TrendSummary,
        description="Historical trend analysis summary"
    )
    model_version: str = Field(
        ...,
        description="Semantic version string of the model generating the predictions"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 UTC timestamp of the assessment"
    )
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Component scores and diagnostic metrics"
    )

    def __getitem__(self, item: str) -> Any:
        """Allow backward-compatible dictionary access for pipelines and adapters."""
        if item == "horizons":
            return {k: {"predicted_quality": v} for k, v in self.predictions.items()}
        if item == "weather_risk":
            return self.risk.value if hasattr(self.risk, "value") else str(self.risk)
        if hasattr(self, item):
            val = getattr(self, item)
            if hasattr(val, "value"):
                return val.value
            return val
        raise KeyError(item)

    def get(self, item: str, default: Any = None) -> Any:
        """Safe getter matching dict interface."""
        try:
            return self[item]
        except KeyError:
            return default

    def to_dict(self) -> Dict[str, Any]:
        """Serializes assessment with convenience horizons structure for consumers."""
        d = self.model_dump()
        d["horizons"] = {k: {"predicted_quality": v} for k, v in self.predictions.items()}
        d["weather_risk"] = self.risk.value if hasattr(self.risk, "value") else str(self.risk)
        return d
