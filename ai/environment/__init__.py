"""Solar Sentry Environment Intelligence & Observation Quality Prediction.
Agent 6 Ownership.

Public API:
    predict_observation_quality(state, history, vision_hints, horizons) -> Dict[str, Any]
    EnvironmentPredictor
    PhysicsBaselineModel
    GradientBoostingQualityModel
    EnvironmentalSimulator
"""

from ai.environment.predictor import predict_observation_quality, EnvironmentPredictor
from ai.environment.schemas import (
    TelemetryInput,
    VisionHints,
    ObservationQualityAssessment,
    EnvironmentalFeatures,
    TrendSummary,
    RiskLevel,
    RiskFactor,
    TrendDirection,
)
from ai.environment.models.base import ObservationQualityModel
from ai.environment.models.physics_baseline import PhysicsBaselineModel
from ai.environment.models.ml_model import GradientBoostingQualityModel
from ai.environment.simulator import EnvironmentalSimulator

__all__ = [
    "predict_observation_quality",
    "EnvironmentPredictor",
    "TelemetryInput",
    "VisionHints",
    "ObservationQualityAssessment",
    "EnvironmentalFeatures",
    "TrendSummary",
    "RiskLevel",
    "RiskFactor",
    "TrendDirection",
    "ObservationQualityModel",
    "PhysicsBaselineModel",
    "GradientBoostingQualityModel",
    "EnvironmentalSimulator",
]
