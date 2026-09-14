from datetime import datetime, timezone
from typing import Dict, Any, Optional

from app.schemas.ai_service import (
    SolarVisionAnalysis,
    WeatherForecastPrediction,
    SensorAnomalyReport,
    CognitiveDecisionTrace,
)
from app.services.observatory_service import observatory_service
from app.repositories.base import ImageRepository
from app.core.event_bus import event_bus, TOPIC_AI_UPDATE
from app.core.logging import logger


class AIIntegrationService:
    """Service integration interfaces for AI Agents 5 through 8."""

    def __init__(self, image_repository: Optional[ImageRepository] = None):
        self.image_repository = image_repository
        self._latest_vision: Optional[SolarVisionAnalysis] = None
        self._latest_forecast: Optional[WeatherForecastPrediction] = None
        self._latest_anomalies: Optional[SensorAnomalyReport] = None
        self._latest_decision: Optional[CognitiveDecisionTrace] = None

    async def ingest_solar_vision(self, analysis: SolarVisionAnalysis) -> Dict[str, Any]:
        """Interface for Agent 5 (Computer Vision & Solar Intelligence)."""
        logger.info(f"Ingested Solar Vision analysis for image '{analysis.image_id}' (disk_detected: {analysis.disk_detected})")
        self._latest_vision = analysis

        # Attach analysis to image record if repository is present
        if self.image_repository:
            try:
                await self.image_repository.update_analysis(analysis.image_id, analysis.model_dump())
            except Exception as e:
                logger.warning(f"Failed to attach vision analysis to image record: {e}")

        # Update observatory AI status
        await observatory_service.update_ai_status("agent_5_solar_vision", analysis.model_dump())

        # Publish event
        await event_bus.publish(TOPIC_AI_UPDATE, {
            "agent": "Agent 5 (Solar Vision)",
            "data": analysis.model_dump()
        })
        return {"status": "accepted", "agent": "Agent 5", "timestamp": analysis.timestamp}

    async def ingest_weather_forecast(self, prediction: WeatherForecastPrediction) -> Dict[str, Any]:
        """Interface for Agent 6 (Environment AI & Observation Quality Prediction)."""
        logger.info(f"Ingested Weather Forecast: {prediction.horizon_minutes}m readiness {prediction.observation_readiness_pct:.1f}%")
        self._latest_forecast = prediction

        await observatory_service.update_ai_status("agent_6_weather_prediction", prediction.model_dump())

        await event_bus.publish(TOPIC_AI_UPDATE, {
            "agent": "Agent 6 (Weather Prediction)",
            "data": prediction.model_dump()
        })
        return {"status": "accepted", "agent": "Agent 6", "timestamp": prediction.timestamp}

    async def ingest_sensor_anomalies(self, report: SensorAnomalyReport) -> Dict[str, Any]:
        """Interface for Agent 7 (Sensor Fusion & Health Anomaly AI)."""
        logger.info(f"Ingested Anomaly Report: detected={report.anomaly_detected}, score={report.overall_anomaly_score:.3f}")
        self._latest_anomalies = report

        await observatory_service.update_ai_status("agent_7_anomaly_ai", report.model_dump())

        await event_bus.publish(TOPIC_AI_UPDATE, {
            "agent": "Agent 7 (Anomaly AI)",
            "data": report.model_dump()
        })
        return {"status": "accepted", "agent": "Agent 7", "timestamp": report.timestamp}

    async def ingest_cognitive_decision(self, trace: CognitiveDecisionTrace) -> Dict[str, Any]:
        """Interface for Agent 8 (Cognitive Decision Engine & XAI)."""
        logger.info(f"Ingested Cognitive Decision: recommended_state={trace.recommended_state}")
        self._latest_decision = trace

        await observatory_service.update_ai_status("agent_8_decision_engine", trace.model_dump())

        await event_bus.publish(TOPIC_AI_UPDATE, {
            "agent": "Agent 8 (Decision Engine)",
            "data": trace.model_dump()
        })
        return {"status": "accepted", "agent": "Agent 8", "timestamp": trace.timestamp}

    def get_summary(self) -> Dict[str, Any]:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "solar_vision": self._latest_vision.model_dump() if self._latest_vision else None,
            "weather_forecast": self._latest_forecast.model_dump() if self._latest_forecast else None,
            "sensor_anomalies": self._latest_anomalies.model_dump() if self._latest_anomalies else None,
            "cognitive_decision": self._latest_decision.model_dump() if self._latest_decision else None,
        }
