"""Environmental & Solar Observatory Simulation Suite.
Agent 6 Ownership.

Generates realistic physical time-series scenarios for offline evaluation,
automated regression testing, and ML model training.
"""

import math
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Tuple, Optional
import numpy as np

from ai.environment.config import (
    DEFAULT_LATITUDE,
    DEFAULT_LONGITUDE,
    MAX_SOLAR_ZENITH_LUX,
)
from ai.environment.features import calculate_solar_position, calculate_clear_sky_lux, calculate_dew_point
from ai.environment.trends import TelemetryHistoryBuffer
from ai.environment.assessor import score_current_observation_quality
from ai.environment.schemas import TelemetryInput, EnvironmentalFeatures


class EnvironmentalSimulator:
    """Generates synthetic multi-modal meteorological and solar telemetry scenarios."""

    @staticmethod
    def generate_scenario(
        scenario_type: str = "CLEAR_DAY",
        start_time: Optional[datetime] = None,
        duration_minutes: int = 240,
        step_seconds: int = 60
    ) -> List[Dict[str, Any]]:
        """Generates a sequential stream of telemetry snapshots for a chosen scenario.
        
        Scenarios:
            - CLEAR_DAY: High quality diurnal solar tracking.
            - AFTERNOON_CLOUDS: Passing cloud deck causing lux fluctuations.
            - THUNDERSTORM_SQUALL: Rapid pressure drop, humidity rise, then rain arrival.
            - MORNING_CONDENSATION: Near 100% humidity, T ~ Tdew lens fogging.
            - THERMAL_TURBULENCE: Intense solar noon seeing boiling.
        """
        if start_time is None:
            # Default to 10:00 AM UTC
            start_time = datetime(2026, 9, 13, 10, 0, 0, tzinfo=timezone.utc)

        records: List[Dict[str, Any]] = []
        steps = int((duration_minutes * 60) / step_seconds)

        base_pressure = 1013.25
        base_temp = 25.0
        base_humidity = 45.0

        for i in range(steps):
            current_dt = start_time + timedelta(seconds=i * step_seconds)
            t_min = (i * step_seconds) / 60.0

            # Astronomical solar position
            elevation, zenith = calculate_solar_position(current_dt)
            clear_sky_lux = calculate_clear_sky_lux(elevation)

            # Scenario modifications
            temp = base_temp + 5.0 * math.sin(math.pi * i / steps)
            humidity = base_humidity - 10.0 * math.sin(math.pi * i / steps)
            pressure = base_pressure
            rain_raw = 3800
            rain_detected = False
            cloud_factor = 1.0

            if scenario_type == "CLEAR_DAY":
                # Clean clear sky with micro-noise
                noise = np.random.normal(0, 0.02)
                cloud_factor = max(0.0, 1.0 + noise)

            elif scenario_type == "AFTERNOON_CLOUDS":
                # Clouds pass between minute 60 and 150
                if 60 <= t_min <= 150:
                    cloud_pattern = 0.35 + 0.30 * math.sin(0.15 * t_min) + np.random.normal(0, 0.08)
                    cloud_factor = max(0.1, min(0.9, cloud_pattern))
                else:
                    cloud_factor = 0.95 + np.random.normal(0, 0.02)

            elif scenario_type == "THUNDERSTORM_SQUALL":
                # Gradual pressure drop from minute 30 onwards
                if t_min > 30:
                    pressure -= (t_min - 30) * 0.05  # -3.0 hPa per hour
                    humidity += (t_min - 30) * 0.45  # rising rapidly
                    humidity = min(98.0, humidity)
                    cloud_factor = max(0.05, 1.0 - (t_min - 30) * 0.012)
                # Rain onset at minute 120
                if t_min >= 120:
                    rain_raw = 650
                    rain_detected = True
                    cloud_factor = 0.05

            elif scenario_type == "MORNING_CONDENSATION":
                # Low temperature, high humidity, dew point depression < 1.5 C
                temp = 12.0 + 0.02 * t_min
                humidity = 95.0 - 0.05 * t_min
                cloud_factor = 0.85

            elif scenario_type == "THERMAL_TURBULENCE":
                temp = 38.0 + 2.0 * math.sin(0.05 * t_min)
                humidity = 25.0
                cloud_factor = 0.98

            lux = max(0.0, clear_sky_lux * cloud_factor)

            record = {
                "device_id": "esp32-sentry-01",
                "timestamp": current_dt.isoformat(),
                "temperature": round(float(temp), 2),
                "humidity": round(float(humidity), 2),
                "pressure": round(float(pressure), 2),
                "lux": round(float(lux), 1),
                "rain_raw": int(rain_raw),
                "rain_detected": bool(rain_detected),
                "pan": 90,
                "tilt": max(0, min(90, int(elevation))),
                "state": "OBSERVE" if not rain_detected else "SUSPEND",
                "health": 100,
                "sensor_status": {"dht22": True, "bh1750": True, "bmp280": True, "rain": True},
                "firmware_version": "1.0.0"
            }
            records.append(record)

        return records

    @staticmethod
    def build_training_dataset(
        num_scenarios_each: int = 5,
        horizons: Tuple[int, int, int] = (15, 30, 60)
    ) -> Tuple[np.ndarray, Dict[int, np.ndarray]]:
        """Generates paired (feature_vectors, future_quality_targets) for training ML models."""
        from ai.environment.features import extract_environmental_features
        from ai.environment.models.ml_model import GradientBoostingQualityModel

        scenarios = ["CLEAR_DAY", "AFTERNOON_CLOUDS", "THUNDERSTORM_SQUALL", "MORNING_CONDENSATION", "THERMAL_TURBULENCE"]
        all_feature_rows: List[np.ndarray] = []
        target_dict: Dict[int, List[float]] = {h: [] for h in horizons}

        for sc in scenarios:
            for rep in range(num_scenarios_each):
                start = datetime(2026, 6, 1, 8, 0, 0, tzinfo=timezone.utc) + timedelta(days=rep * 10)
                stream = EnvironmentalSimulator.generate_scenario(sc, start_time=start, duration_minutes=240, step_seconds=60)
                
                # Precompute ground truth quality for every step
                history = TelemetryHistoryBuffer()
                qualities: List[float] = []
                features_list: List[EnvironmentalFeatures] = []
                telemetry_list: List[TelemetryInput] = []
                trends_list: List[Any] = []

                for row in stream:
                    tel = TelemetryInput(**row)
                    history.add_snapshot(tel)
                    trends = history.analyze_trends()
                    feats = extract_environmental_features(tel, trends)
                    q, _ = score_current_observation_quality(feats, tel, trends)

                    qualities.append(q)
                    features_list.append(feats)
                    telemetry_list.append(tel)
                    trends_list.append(trends)

                # Form lag features and future targets
                max_h = max(horizons)
                for idx in range(15, len(stream) - max_h):
                    tel = telemetry_list[idx]
                    feats = features_list[idx]
                    trends = trends_list[idx]
                    q_curr = qualities[idx]

                    vec = GradientBoostingQualityModel.extract_feature_vector(q_curr, tel, feats, trends)
                    all_feature_rows.append(vec)

                    for h in horizons:
                        future_idx = idx + h
                        target_dict[h].append(qualities[future_idx])

        X = np.array(all_feature_rows, dtype=np.float32)
        y = {h: np.array(target_dict[h], dtype=np.float32) for h in horizons}
        return X, y
