"""Configuration and meteorological constants for Environment Intelligence & Observation Quality Prediction.
Agent 6 Ownership.
"""

from typing import Tuple, Dict, Any

# Observatory Geographic Defaults (can be overridden via environment variables or runtime state)
DEFAULT_LATITUDE: float = 28.6139      # Latitude in decimal degrees (default: mid-latitude reference)
DEFAULT_LONGITUDE: float = 77.2090     # Longitude in decimal degrees
DEFAULT_ELEVATION_M: float = 216.0     # Elevation above sea level in meters

# Solar Irradiance & Illuminance Constants
MAX_SOLAR_ZENITH_LUX: float = 120000.0 # Peak theoretical illuminance at solar zenith (lux)
MIN_OBSERVABLE_ELEVATION_DEG: float = 10.0 # Minimum solar elevation angle above horizon for observation
HORIZON_ELEVATION_DEG: float = 0.0     # True geometric horizon

# Magnus-Tetens Dew Point Approximation Constants (Sonntag 1990)
MAGNUS_A: float = 17.27
MAGNUS_B: float = 237.7  # degrees C

# Environmental Risk Thresholds
CONDENSATION_DEPRESSION_CRITICAL: float = 1.5  # T - Tdew <= 1.5 C -> Critical condensation
CONDENSATION_DEPRESSION_WARNING: float = 3.0   # T - Tdew <= 3.0 C -> High condensation risk
PRESSURE_DROP_HOURLY_STORM_HPA: float = -2.0  # hPa/hr drop indicating approaching storm/squall
PRESSURE_DROP_HOURLY_MODERATE_HPA: float = -1.0 # hPa/hr moderate front
HUMIDITY_HIGH_RISK_PERCENT: float = 85.0       # RH > 85% elevates risk
HUMIDITY_CRITICAL_PERCENT: float = 93.0        # RH > 93% imminent rain / fog

# Observation Quality Scoring Weights
QUALITY_WEIGHT_CLEARNESS: float = 0.50
QUALITY_WEIGHT_STABILITY: float = 0.20
QUALITY_WEIGHT_SEEING: float = 0.15
QUALITY_WEIGHT_VISION_HINT: float = 0.15

# Default Prediction Horizons (in minutes)
DEFAULT_HORIZONS: Tuple[int, int, int] = (15, 30, 60)

# Model Version Identifiers
BASELINE_MODEL_VERSION: str = "1.0.0-physics-baseline"
ML_MODEL_VERSION: str = "1.1.0-gb-predictor"
ACTIVE_MODEL_VERSION: str = BASELINE_MODEL_VERSION
