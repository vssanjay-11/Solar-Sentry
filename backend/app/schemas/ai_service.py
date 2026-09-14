from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

from app.schemas.telemetry import SensorTelemetry


class SolarVisionAnalysis(BaseModel):
    """Payload produced by Agent 5 (Computer Vision)."""
    image_id: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    disk_detected: bool = True
    disk_center_x: Optional[float] = None
    disk_center_y: Optional[float] = None
    disk_radius: Optional[float] = None
    sunspot_count: int = 0
    sunspot_coordinates: List[Dict[str, float]] = []
    sharpness_score: float = 0.85
    cloud_occlusion_pct: float = 0.0
    quality_grade: str = "EXCELLENT"  # EXCELLENT, GOOD, POOR, BLOCKED
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WeatherForecastPrediction(BaseModel):
    """Payload produced by Agent 6 (Environment Prediction)."""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    horizon_minutes: int = Field(15, description="Prediction horizon: 15, 30, or 60 min")
    observation_readiness_pct: float = Field(..., ge=0.0, le=100.0)
    cloud_transit_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    precipitation_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    expected_lux: Optional[float] = None
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    recommendation: str = "PROCEED"  # PROCEED, DELAY, SUSPEND


class SensorAnomalyReport(BaseModel):
    """Payload produced by Agent 7 (Sensor Fusion & Anomaly AI)."""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    anomaly_detected: bool = False
    overall_anomaly_score: float = Field(default=0.05, ge=0.0, le=1.0)
    compromised_sensors: List[str] = []
    sensor_health_scores: Dict[str, float] = Field(default_factory=dict)
    fusion_state: str = "NOMINAL"  # NOMINAL, DEGRADED, CRITICAL
    message: str = "All sensors within nominal multi-modal correlation envelope"


class CognitiveDecisionTrace(BaseModel):
    """Payload produced by Agent 8 (Cognitive Decision Engine & XAI)."""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    recommended_state: str = "OBSERVE"
    suggested_action: str = "TRACK_SUN"
    confidence: float = Field(default=0.95, ge=0.0, le=1.0)
    reasoning_chain: List[str] = []
    explanation: str = "Solar illuminance optimal, no rain or cloud occlusion detected."
    safety_override: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SimulationTelemetryBatch(BaseModel):
    """Payload submitted by Agent 10 (Digital Twin & Simulation)."""
    scenario_id: str = "synthetic-run-001"
    description: Optional[str] = "Simulated solar transit with convective cloud passage"
    injected_events: List[str] = []
    frames: List[SensorTelemetry]
