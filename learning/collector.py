"""
Solar Sentry — Learning Framework: Data & Feedback Collection
Agent 10: Digital Twin + Mission Memory + Learning + Simulation + Integration

Safely collects observation telemetry, prediction pairs (forecast vs ground truth),
and operator/verification feedback for offline analysis.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ExperienceSample(BaseModel):
    """Paired environmental forecast and verified outcome sample."""
    sample_id: str = Field(..., description="Unique sample ID")
    timestamp: str = Field(..., description="Observation timestamp")
    features: Dict[str, float] = Field(..., description="Extracted input feature vector")
    predicted_quality_15m: float = Field(..., description="15-minute horizon prediction")
    actual_quality_15m: Optional[float] = Field(None, description="Ground truth quality achieved 15m later")
    predicted_quality_30m: float = Field(..., description="30-minute horizon prediction")
    actual_quality_30m: Optional[float] = Field(None, description="Ground truth quality achieved 30m later")
    operator_rating: Optional[float] = Field(None, ge=0.0, le=1.0, description="Optional human operator feedback rating")
    verification_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Automated post-action verification score")
    weather_risk: str = Field("LOW", description="Assessed weather risk")
    rain_occurred: bool = Field(False, description="Whether rain occurred during observation window")


class ExperienceCollector:
    """
    In-memory and buffer collector for training data and operator feedback.
    Validates and sanctions samples before offline training.
    """

    def __init__(self, max_buffer_size: int = 5000):
        self.max_buffer_size = max_buffer_size
        self._samples: List[ExperienceSample] = []
        self._pending_verifications: Dict[str, Dict[str, Any]] = {}

    def log_prediction(
        self,
        sample_id: str,
        features: Dict[str, float],
        pred_15m: float,
        pred_30m: float,
        weather_risk: str = "LOW"
    ) -> None:
        """Logs a prediction snapshot to be reconciled when future ground truth arrives."""
        self._pending_verifications[sample_id] = {
            "sample_id": sample_id,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "features": features,
            "pred_15m": pred_15m,
            "pred_30m": pred_30m,
            "weather_risk": weather_risk
        }

    def reconcile_ground_truth(
        self,
        sample_id: str,
        actual_15m: float,
        actual_30m: Optional[float] = None,
        rain_occurred: bool = False,
        verification_score: Optional[float] = None,
        operator_rating: Optional[float] = None
    ) -> Optional[ExperienceSample]:
        """Reconciles a pending prediction with ground truth outcome and saves sample."""
        pending = self._pending_verifications.pop(sample_id, None)
        if not pending:
            return None

        sample = ExperienceSample(
            sample_id=sample_id,
            timestamp=pending["timestamp"],
            features=pending["features"],
            predicted_quality_15m=pending["pred_15m"],
            actual_quality_15m=actual_15m,
            predicted_quality_30m=pending["pred_30m"],
            actual_quality_30m=actual_30m if actual_30m is not None else actual_15m,
            operator_rating=operator_rating,
            verification_score=verification_score,
            weather_risk=pending["weather_risk"],
            rain_occurred=rain_occurred
        )
        self.add_sample(sample)
        return sample

    def add_sample(self, sample: ExperienceSample) -> None:
        """Appends a validated experience sample."""
        self._samples.append(sample)
        if len(self._samples) > self.max_buffer_size:
            self._samples.pop(0)

    def get_dataset(self) -> List[ExperienceSample]:
        """Returns all accumulated experience samples."""
        return list(self._samples)

    def get_paired_dataset(self) -> List[ExperienceSample]:
        """Returns only samples with verified actual ground truth."""
        return [s for s in self._samples if s.actual_quality_15m is not None]

    def clear(self) -> None:
        self._samples.clear()
        self._pending_verifications.clear()
