"""High-level Orchestrator & Public API for Solar Observation Quality Prediction.
Agent 6 Ownership.

Interface:
    predict_observation_quality(state, history, vision_hints, horizons) -> Dict[str, Any]
"""

from typing import Union, Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

from ai.environment.config import (
    DEFAULT_HORIZONS,
    BASELINE_MODEL_VERSION,
    ML_MODEL_VERSION,
)
from ai.environment.schemas import (
    TelemetryInput,
    VisionHints,
    ObservationQualityAssessment,
    TrendSummary,
    TrendDirection,
)
from ai.environment.features import extract_environmental_features
from ai.environment.trends import TelemetryHistoryBuffer
from ai.environment.assessor import (
    score_current_observation_quality,
    assess_environmental_risks,
)
from ai.environment.models.base import ObservationQualityModel
from ai.environment.models.physics_baseline import PhysicsBaselineModel
from ai.environment.models.ml_model import GradientBoostingQualityModel


class EnvironmentPredictor:
    """Manages feature extraction, rolling trends, model selection, confidence, and risk evaluation."""

    def __init__(self, ml_weights_path: Optional[str] = None):
        self.physics_model = PhysicsBaselineModel()
        self.ml_model = GradientBoostingQualityModel()
        if ml_weights_path:
            self.ml_model.load(ml_weights_path)
        self.history_buffer = TelemetryHistoryBuffer()

    def calculate_confidence(
        self,
        telemetry: TelemetryInput,
        trends: TrendSummary,
        history_count: int,
        model: ObservationQualityModel
    ) -> float:
        """Calculates prediction confidence score [0.0, 1.0]."""
        confidence = 0.95

        # 1. Sensor health penalty
        if telemetry.sensor_status:
            for s_name, ok in telemetry.sensor_status.items():
                if not ok:
                    confidence -= 0.20

        # 2. Volatility penalty
        if trends.lux_trend == TrendDirection.VOLATILE:
            confidence -= 0.15

        # 3. History sparsity penalty
        if history_count < 3:
            confidence -= 0.08
        elif history_count < 10:
            confidence -= 0.03

        # 4. Out-of-bounds telemetry clamp penalty
        if telemetry.lux < 0 or telemetry.humidity > 100 or telemetry.pressure < 700:
            confidence -= 0.25

        return round(max(0.1, min(1.0, confidence)), 2)

    def predict(
        self,
        state: Optional[Union[Dict[str, Any], TelemetryInput]] = None,
        history: Optional[List[Union[Dict[str, Any], TelemetryInput]]] = None,
        vision_hints: Optional[Union[Dict[str, Any], VisionHints]] = None,
        horizons: Tuple[int, ...] = DEFAULT_HORIZONS,
        use_ml: bool = False,
        telemetry: Optional[Union[Dict[str, Any], TelemetryInput]] = None,
    ) -> ObservationQualityAssessment:
        """Executes full environment assessment and multi-horizon prediction."""
        target_state = state if state is not None else telemetry
        if target_state is None:
            raise ValueError("predict() requires either 'state' or 'telemetry' input argument.")

        # Normalize input state
        if isinstance(target_state, dict):
            telemetry_input = TelemetryInput(**target_state)
        else:
            telemetry_input = target_state
        telemetry = telemetry_input

        # Normalize vision hints
        vision: Optional[VisionHints] = None
        if vision_hints is not None:
            if isinstance(vision_hints, dict):
                vision = VisionHints(**vision_hints)
            else:
                vision = vision_hints

        # Populate and update history buffer
        if history:
            self.history_buffer.populate(history)
        self.history_buffer.add_snapshot(telemetry)

        # 1. Analyze historical trends
        trends = self.history_buffer.analyze_trends()

        # 2. Extract engineered features
        features = extract_environmental_features(telemetry, trends)

        # 3. Assess current condition score
        current_quality, breakdown = score_current_observation_quality(
            features=features,
            telemetry=telemetry,
            trends=trends,
            vision=vision
        )

        # 4. Assess environmental risks
        risk_level, risk_factors = assess_environmental_risks(
            features=features,
            telemetry=telemetry,
            trends=trends,
            vision=vision
        )

        # 5. Select active prediction model (ML if ready and requested, otherwise physics baseline)
        active_model: ObservationQualityModel = self.physics_model
        if use_ml and self.ml_model.is_ready:
            active_model = self.ml_model

        # 6. Generate multi-horizon predictions
        predictions = active_model.predict_all_horizons(
            current_quality=current_quality,
            telemetry=telemetry,
            features=features,
            trends=trends,
            horizons=horizons,
            vision=vision
        )

        # 7. Compute prediction confidence
        confidence = self.calculate_confidence(
            telemetry=telemetry,
            trends=trends,
            history_count=self.history_buffer.count(),
            model=active_model
        )

        # Timestamp
        ts = telemetry.timestamp or datetime.now(timezone.utc).isoformat()

        return ObservationQualityAssessment(
            current_quality=current_quality,
            predictions=predictions,
            confidence=confidence,
            risk=risk_level,
            risk_factors=risk_factors,
            trend=trends,
            model_version=active_model.model_version,
            timestamp=str(ts),
            details={
                "components": breakdown,
                "features": features.model_dump(),
                "history_points": self.history_buffer.count(),
            }
        )


# Global singleton instance for clean stateless functional calls
_DEFAULT_PREDICTOR = EnvironmentPredictor()


def predict_observation_quality(
    state: Union[Dict[str, Any], TelemetryInput],
    history: Optional[List[Union[Dict[str, Any], TelemetryInput]]] = None,
    vision_hints: Optional[Union[Dict[str, Any], VisionHints]] = None,
    horizons: Tuple[int, ...] = DEFAULT_HORIZONS,
    use_ml: bool = False
) -> Dict[str, Any]:
    """Clean functional interface for Agent 8 and external callers.
    
    Returns structured dictionary matching the required contract:
    {
        "current_quality": 0.86,
        "predictions": {
            "15m": 0.82,
            "30m": 0.74,
            "60m": 0.51
        },
        "confidence": 0.88,
        "risk": "MEDIUM"
    }
    """
    assessment = _DEFAULT_PREDICTOR.predict(
        state=state,
        history=history,
        vision_hints=vision_hints,
        horizons=horizons,
        use_ml=use_ml
    )
    return assessment.model_dump()
