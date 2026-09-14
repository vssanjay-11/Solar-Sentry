"""Abstract base class and evaluation interfaces for Observation Quality Prediction Models.
Agent 6 Ownership.
"""

from abc import ABC, abstractmethod
from typing import Dict, Tuple, Optional, Any, List

from ai.environment.schemas import (
    TelemetryInput,
    EnvironmentalFeatures,
    TrendSummary,
    VisionHints,
)


class ObservationQualityModel(ABC):
    """Abstract base class for all observation quality forecasting models."""

    @property
    @abstractmethod
    def model_version(self) -> str:
        """Returns the semantic version of this model."""
        pass

    @property
    @abstractmethod
    def is_ready(self) -> bool:
        """Returns True if the model is fitted and ready to generate predictions."""
        pass

    @abstractmethod
    def predict_horizon(
        self,
        current_quality: float,
        telemetry: TelemetryInput,
        features: EnvironmentalFeatures,
        trends: TrendSummary,
        horizon_minutes: int,
        vision: Optional[VisionHints] = None
    ) -> float:
        """Predicts observation quality at a specific horizon in the future."""
        pass

    def predict_all_horizons(
        self,
        current_quality: float,
        telemetry: TelemetryInput,
        features: EnvironmentalFeatures,
        trends: TrendSummary,
        horizons: Tuple[int, ...] = (15, 30, 60),
        vision: Optional[VisionHints] = None
    ) -> Dict[str, float]:
        """Predicts observation quality across multiple horizons.
        
        Returns:
            Dict[str, float]: e.g. {"15m": 0.82, "30m": 0.74, "60m": 0.51}
        """
        predictions: Dict[str, float] = {}
        for h in horizons:
            score = self.predict_horizon(
                current_quality=current_quality,
                telemetry=telemetry,
                features=features,
                trends=trends,
                horizon_minutes=h,
                vision=vision
            )
            predictions[f"{h}m"] = round(max(0.0, min(1.0, score)), 2)
        return predictions

    def evaluate(self, y_true: List[float], y_pred: List[float]) -> Dict[str, float]:
        """Calculates standard regression metrics: MAE, RMSE, Pearson Correlation."""
        import numpy as np
        yt = np.array(y_true)
        yp = np.array(y_pred)
        
        mae = float(np.mean(np.abs(yt - yp)))
        rmse = float(np.sqrt(np.mean((yt - yp) ** 2)))
        
        # Pearson correlation
        if np.std(yt) > 1e-6 and np.std(yp) > 1e-6:
            r = float(np.corrcoef(yt, yp)[0, 1])
        else:
            r = 1.0 if np.allclose(yt, yp, atol=1e-3) else 0.0

        # Directional agreement (did both go up/down compared to current quality)
        return {
            "mae": round(mae, 4),
            "rmse": round(rmse, 4),
            "pearson_r": round(r, 4)
        }
