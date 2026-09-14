"""Scikit-Learn Machine Learning Predictor for Multi-Horizon Quality Forecasting.
Agent 6 Ownership.

Implements HistGradientBoostingRegressor / RandomForest multi-horizon forecasting (Version 1.1.0).
Provides persistence, feature vector serialization, and automatic fallback capability.
"""

import os
from typing import Dict, Optional, List, Tuple, Any
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
import joblib

from ai.environment.config import ML_MODEL_VERSION
from ai.environment.schemas import (
    TelemetryInput,
    EnvironmentalFeatures,
    TrendSummary,
    VisionHints,
)
from ai.environment.models.base import ObservationQualityModel


FEATURE_NAMES = [
    "current_quality",
    "temperature",
    "humidity",
    "pressure",
    "lux",
    "solar_elevation_deg",
    "clearness_index",
    "dew_point",
    "dew_point_depression",
    "thermal_seeing_index",
    "precipitation_imminence",
    "lux_change_rate_per_min",
    "pressure_change_hpa_per_hour",
    "humidity_change_pct_per_hour",
    "vision_quality_hint",
]


class GradientBoostingQualityModel(ObservationQualityModel):
    """Gradient Boosting ML Model for multi-horizon solar observation forecasting."""

    def __init__(self, version: Optional[str] = None):
        self._version = version or ML_MODEL_VERSION
        # Horizon in minutes -> HistGradientBoostingRegressor
        self.regressors: Dict[int, HistGradientBoostingRegressor] = {}
        self._fitted = False
        self.model = HistGradientBoostingRegressor(
            max_iter=100,
            max_depth=6,
            learning_rate=0.08,
            min_samples_leaf=10,
            random_state=42
        )
        self.is_fitted = False

    @property
    def model_version(self) -> str:
        return self._version

    @property
    def is_ready(self) -> bool:
        return self._fitted and len(self.regressors) > 0

    @staticmethod
    def extract_feature_vector(
        current_quality: float,
        telemetry: TelemetryInput,
        features: EnvironmentalFeatures,
        trends: TrendSummary,
        vision: Optional[VisionHints] = None
    ) -> np.ndarray:
        """Flattens input state into a normalized numerical feature vector."""
        vision_hint = 1.0
        if vision is not None:
            if vision.image_quality is not None:
                vision_hint = vision.image_quality
            elif vision.cloud_cover is not None:
                vision_hint = max(0.0, 1.0 - vision.cloud_cover)

        vec = [
            float(current_quality),
            float(telemetry.temperature),
            float(telemetry.humidity),
            float(telemetry.pressure),
            float(telemetry.lux),
            float(features.solar_elevation_deg),
            float(features.clearness_index),
            float(features.dew_point),
            float(features.dew_point_depression),
            float(features.thermal_seeing_index),
            float(features.precipitation_imminence),
            float(trends.lux_change_rate_per_min),
            float(trends.pressure_change_hpa_per_hour),
            float(trends.humidity_change_pct_per_hour),
            float(vision_hint)
        ]
        return np.array(vec, dtype=np.float32)

    def fit(self, X: np.ndarray, y_horizons: Dict[int, np.ndarray]) -> None:
        """Trains individual regressors for each forecast horizon (e.g. 15, 30, 60 min)."""
        self.regressors.clear()
        for horizon, y in y_horizons.items():
            reg = HistGradientBoostingRegressor(
                max_iter=100,
                max_depth=6,
                learning_rate=0.08,
                min_samples_leaf=10,
                random_state=42
            )
            reg.fit(X, y)
            self.regressors[horizon] = reg
        self._fitted = True

    def predict_horizon(
        self,
        current_quality: float,
        telemetry: TelemetryInput,
        features: EnvironmentalFeatures,
        trends: TrendSummary,
        horizon_minutes: int,
        vision: Optional[VisionHints] = None
    ) -> float:
        """Predicts observation quality at horizon_minutes using trained regressor."""
        if not self.is_ready or horizon_minutes not in self.regressors:
            raise RuntimeError(f"ML Model is not trained for horizon {horizon_minutes}m")

        if telemetry.rain_detected or features.solar_elevation_deg <= 0.0:
            return 0.0

        x = self.extract_feature_vector(current_quality, telemetry, features, trends, vision).reshape(1, -1)
        pred = float(self.regressors[horizon_minutes].predict(x)[0])
        return max(0.0, min(1.0, pred))

    def save(self, model_path: str) -> None:
        """Persists trained model weights to disk."""
        os.makedirs(os.path.dirname(os.path.abspath(model_path)), exist_ok=True)
        payload = {
            "version": self._version,
            "regressors": self.regressors,
            "fitted": self._fitted
        }
        joblib.dump(payload, model_path)

    def load(self, model_path: str) -> bool:
        """Loads trained weights from disk. Returns True on success, False if file not found."""
        if not os.path.exists(model_path):
            return False
        try:
            payload = joblib.load(model_path)
            self._version = payload.get("version", ML_MODEL_VERSION)
            self.regressors = payload.get("regressors", {})
            self._fitted = payload.get("fitted", False)
            return self._fitted
        except Exception:
            return False
