"""
Solar Sentry - Environment Prediction Repository
Data access operations for 15/30/60 minute observation quality forecasts.
"""

from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from backend.database.models.prediction import EnvironmentPrediction
from backend.database.repositories.base import BaseRepository


class EnvironmentPredictionRepository(BaseRepository[EnvironmentPrediction]):
    """Repository managing environmental quality forecasts (Agent 6)."""

    def __init__(self, session: Session):
        super().__init__(EnvironmentPrediction, session)

    def record_prediction(
        self,
        prediction_id: str,
        device_id: str,
        target_timestamp: datetime,
        horizon_minutes: int,
        predicted_quality_score: float,
        predicted_cloud_cover_pct: float,
        model_version: str,
        predicted_lux: Optional[float] = None,
        rain_probability: float = 0.0,
        uncertainty_bounds_json: Optional[dict] = None,
        generated_at: Optional[datetime] = None,
    ) -> EnvironmentPrediction:
        """Stores a multi-horizon forecast prediction."""
        pred = EnvironmentPrediction(
            prediction_id=prediction_id,
            device_id=device_id,
            generated_at=generated_at or datetime.now(timezone.utc),
            target_timestamp=target_timestamp,
            horizon_minutes=horizon_minutes,
            predicted_quality_score=predicted_quality_score,
            predicted_cloud_cover_pct=predicted_cloud_cover_pct,
            predicted_lux=predicted_lux,
            rain_probability=rain_probability,
            model_version=model_version,
            uncertainty_bounds_json=uncertainty_bounds_json,
            created_at=datetime.now(timezone.utc),
        )
        return self.create(pred)

    def get_latest_forecast(
        self,
        device_id: str,
        horizon_minutes: int = 15,
    ) -> Optional[EnvironmentPrediction]:
        """Returns the most recent forecast for a specific horizon."""
        stmt = (
            select(EnvironmentPrediction)
            .where(
                and_(
                    EnvironmentPrediction.device_id == device_id,
                    EnvironmentPrediction.horizon_minutes == horizon_minutes,
                )
            )
            .order_by(EnvironmentPrediction.generated_at.desc())
            .limit(1)
        )
        return self.session.scalars(stmt).first()

    def list_for_target_window(
        self,
        device_id: str,
        window_start: datetime,
        window_end: datetime,
    ) -> List[EnvironmentPrediction]:
        """Returns all predictions targeting a specific observation window."""
        stmt = (
            select(EnvironmentPrediction)
            .where(
                and_(
                    EnvironmentPrediction.device_id == device_id,
                    EnvironmentPrediction.target_timestamp >= window_start,
                    EnvironmentPrediction.target_timestamp <= window_end,
                )
            )
            .order_by(EnvironmentPrediction.target_timestamp.asc())
        )
        return list(self.session.scalars(stmt).all())
