"""Domain-specific meteorological and solar physical feature engineering.
Agent 6 Ownership.
"""

import math
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from ai.environment.config import (
    DEFAULT_LATITUDE,
    DEFAULT_LONGITUDE,
    MAX_SOLAR_ZENITH_LUX,
    MAGNUS_A,
    MAGNUS_B,
    CONDENSATION_DEPRESSION_CRITICAL,
    PRESSURE_DROP_HOURLY_STORM_HPA,
    HUMIDITY_CRITICAL_PERCENT,
)
from ai.environment.schemas import TelemetryInput, EnvironmentalFeatures, TrendSummary


def calculate_solar_position(
    dt: datetime,
    lat_deg: float = DEFAULT_LATITUDE,
    lon_deg: float = DEFAULT_LONGITUDE
) -> tuple[float, float]:
    """Computes solar elevation angle and zenith angle in degrees using NOAA solar positioning.
    
    Returns:
        tuple[float, float]: (elevation_deg, zenith_deg)
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    # Day of year and fractional hour
    day_of_year = dt.timetuple().tm_yday
    utc_hour = dt.hour + dt.minute / 60.0 + dt.second / 3600.0

    # Fractional year in radians (gamma)
    gamma = 2.0 * math.pi / 365.0 * (day_of_year - 1 + (utc_hour - 12.0) / 24.0)

    # Equation of time in minutes
    eqtime = 229.18 * (
        0.000075 +
        0.001868 * math.cos(gamma) -
        0.032077 * math.sin(gamma) -
        0.014615 * math.cos(2.0 * gamma) -
        0.040849 * math.sin(2.0 * gamma)
    )

    # Solar declination angle in radians
    decl = (
        0.006918 -
        0.399912 * math.cos(gamma) +
        0.070257 * math.sin(gamma) -
        0.006758 * math.cos(2.0 * gamma) +
        0.000907 * math.sin(2.0 * gamma) -
        0.002697 * math.cos(3.0 * gamma) +
        0.001480 * math.sin(3.0 * gamma)
    )

    # Time offset in minutes
    time_offset = eqtime + 4.0 * lon_deg
    true_solar_time = (utc_hour * 60.0 + time_offset) % 1440.0

    # Solar hour angle in degrees
    solar_hour_angle = (true_solar_time / 4.0) - 180.0
    ha_rad = math.radians(solar_hour_angle)

    # Convert latitude to radians
    lat_rad = math.radians(lat_deg)

    # Solar zenith angle
    cos_zenith = math.sin(lat_rad) * math.sin(decl) + math.cos(lat_rad) * math.cos(decl) * math.cos(ha_rad)
    cos_zenith = max(-1.0, min(1.0, cos_zenith))
    zenith_rad = math.acos(cos_zenith)
    zenith_deg = math.degrees(zenith_rad)

    elevation_deg = 90.0 - zenith_deg
    return elevation_deg, zenith_deg


def calculate_clear_sky_lux(elevation_deg: float) -> float:
    """Calculates theoretical clear-sky illuminance (lux) as a function of solar elevation.
    Uses atmospheric airmass extinction model.
    """
    if elevation_deg <= 0.0:
        return 0.0

    sin_elev = math.sin(math.radians(elevation_deg))
    # Relative airmass approximation (Kasten & Young 1989)
    airmass = 1.0 / max(0.01, (sin_elev + 0.50572 * pow(elevation_deg + 6.07995, -1.6364)))
    
    # Atmospheric extinction coefficient ~ 0.12 to 0.15 for clean atmosphere
    extinction = 0.14
    expected_lux = MAX_SOLAR_ZENITH_LUX * sin_elev * math.exp(-extinction * airmass)
    return max(0.0, expected_lux)


def calculate_dew_point(temperature_c: float, humidity_pct: float) -> float:
    """Calculates dew point temperature in degrees Celsius using the Magnus-Tetens formula."""
    rh = max(0.01, min(100.0, humidity_pct))
    alpha = ((MAGNUS_A * temperature_c) / (MAGNUS_B + temperature_c)) + math.log(rh / 100.0)
    dew_point = (MAGNUS_B * alpha) / (MAGNUS_A - alpha)
    return round(dew_point, 2)


def calculate_thermal_seeing_index(elevation_deg: float, temperature_c: float, pressure_hpa: float) -> float:
    """Estimates atmospheric thermal seeing turbulence index [0.0 to 1.0] where 1.0 is stable.
    Ground heating at high solar elevations and pressure instability drive convective boiling.
    """
    if elevation_deg <= 0.0:
        return 0.0

    # Strong sun elevation heats the surface, creating convective plumes
    thermal_stress = max(0.0, (elevation_deg - 30.0) / 60.0) if elevation_deg > 30.0 else 0.0
    
    # Extreme heat also worsens ground seeing
    heat_stress = max(0.0, (temperature_c - 28.0) / 15.0) if temperature_c > 28.0 else 0.0
    
    seeing_index = 1.0 - (0.25 * thermal_stress + 0.20 * heat_stress)
    return max(0.2, min(1.0, seeing_index))


def calculate_precipitation_imminence(
    humidity_pct: float,
    pressure_change_per_hour: float,
    clearness_index: float,
    rain_raw: Optional[int] = None
) -> float:
    """Estimates the probability index [0.0, 1.0] of imminent rain before drops hit the sensor.
    Combines high relative humidity, dropping barometric pressure, and dimming daylight.
    """
    imminence = 0.0

    # 1. Humidity contribution
    if humidity_pct >= HUMIDITY_CRITICAL_PERCENT:
        imminence += 0.50
    elif humidity_pct >= 85.0:
        imminence += 0.30
    elif humidity_pct >= 75.0:
        imminence += 0.15

    # 2. Barometric pressure drop contribution
    if pressure_change_per_hour <= PRESSURE_DROP_HOURLY_STORM_HPA:
        imminence += 0.35
    elif pressure_change_per_hour <= -1.0:
        imminence += 0.20

    # 3. Sudden daylight attenuation (thick clouds rolling in)
    if clearness_index < 0.25:
        imminence += 0.20
    elif clearness_index < 0.45:
        imminence += 0.10

    # 4. Pre-trip rain sensor moisture accumulation (if rain_raw < 2500 but threshold not yet tripped)
    if rain_raw is not None and rain_raw < 2200:
        imminence += 0.25

    return min(1.0, max(0.0, imminence))


def extract_environmental_features(
    telemetry: TelemetryInput,
    trends: Optional[TrendSummary] = None,
    lat_deg: float = DEFAULT_LATITUDE,
    lon_deg: float = DEFAULT_LONGITUDE
) -> EnvironmentalFeatures:
    """Transforms raw telemetry and historical trends into rich physical features."""
    if trends is None:
        trends = TrendSummary()

    # Parse timestamp
    dt = None
    if telemetry.timestamp:
        try:
            dt = datetime.fromisoformat(telemetry.timestamp.replace("Z", "+00:00"))
        except Exception:
            dt = datetime.now(timezone.utc)
    else:
        dt = datetime.now(timezone.utc)

    # 1. Solar geometry
    elevation_deg, zenith_deg = calculate_solar_position(dt, lat_deg, lon_deg)
    
    # 2. Clear sky benchmark & clearness index
    clear_sky_lux = calculate_clear_sky_lux(elevation_deg)
    if clear_sky_lux > 100.0:
        clearness_index = telemetry.lux / clear_sky_lux
    else:
        clearness_index = 0.0 if elevation_deg <= 0.0 else (telemetry.lux / 100.0)

    # 3. Psychrometric features
    dew_point = calculate_dew_point(telemetry.temperature, telemetry.humidity)
    dew_point_depression = telemetry.temperature - dew_point

    # 4. Thermal seeing
    thermal_seeing = calculate_thermal_seeing_index(elevation_deg, telemetry.temperature, telemetry.pressure)

    # 5. Precipitation imminence
    imminence = calculate_precipitation_imminence(
        humidity_pct=telemetry.humidity,
        pressure_change_per_hour=trends.pressure_change_hpa_per_hour,
        clearness_index=clearness_index,
        rain_raw=telemetry.rain_raw
    )

    return EnvironmentalFeatures(
        solar_elevation_deg=round(elevation_deg, 2),
        solar_zenith_deg=round(zenith_deg, 2),
        clear_sky_lux=round(clear_sky_lux, 1),
        clearness_index=round(clearness_index, 3),
        dew_point=dew_point,
        dew_point_depression=round(dew_point_depression, 2),
        pressure_delta_15m=round(trends.pressure_change_hpa_per_hour / 4.0, 3),
        pressure_delta_60m=round(trends.pressure_change_hpa_per_hour, 3),
        lux_rate_of_change=round(trends.lux_change_rate_per_min, 1),
        thermal_seeing_index=round(thermal_seeing, 3),
        precipitation_imminence=round(imminence, 3)
    )
