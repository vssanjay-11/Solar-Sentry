"""
Solar Sentry — Cognitive Decision Engine Data Types & Contracts
Agent 8: Cognitive Decision Engine + Explainable AI (XAI)
"""

from __future__ import annotations
from enum import Enum
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict


class DecisionType(str, Enum):
    """Core autonomous decisions for Solar Sentry observatory."""
    OBSERVE = "OBSERVE"
    WAIT = "WAIT"
    SCAN = "SCAN"
    SUSPEND = "SUSPEND"
    SAFE = "SAFE"


class RiskLevel(str, Enum):
    """Risk assessment for the planned operational state."""
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class OperationalMode(str, Enum):
    """Observatory cognitive operating mode."""
    NORMAL = "NORMAL"
    DEGRADED = "DEGRADED"
    UNCERTAIN = "UNCERTAIN"
    SAFE_MODE = "SAFE_MODE"


class SafetyGate(str, Enum):
    """Hard safety interlock triggers."""
    NONE = "NONE"
    RAIN_ACTIVE = "RAIN_ACTIVE"
    COMMS_TIMEOUT = "COMMS_TIMEOUT"
    CRITICAL_HARDWARE_FAULT = "CRITICAL_HARDWARE_FAULT"
    THERMAL_EXCURSION = "THERMAL_EXCURSION"


# Alias for backwards compatibility
SafetyTripCode = SafetyGate


# -----------------------------------------------------------------------------
# Upstream Input Models (Consumed from Agents 1, 5, 6, 7)
# -----------------------------------------------------------------------------

class VisionEvaluation(BaseModel):
    """Evaluation consumed from Agent 5 (Computer Vision & Solar Intelligence)."""
    model_config = ConfigDict(extra="ignore")

    vision_quality: float = Field(default=0.8, ge=0.0, le=1.0, description="Overall visual clarity & observation utility [0.0-1.0]")
    solar_disk_detected: bool = Field(default=True, description="True if sun disk is bounded within field of view")
    disk_confidence: float = Field(default=0.9, ge=0.0, le=1.0, description="Confidence of solar disk identification")
    cloud_coverage: float = Field(default=0.1, ge=0.0, le=1.0, description="Estimated cloud occlusion over solar disk [0.0-1.0]")
    clarity_score: float = Field(default=0.85, ge=0.0, le=1.0, description="Sharpness / limb-darkening contrast [0.0-1.0]")
    sunspot_count: int = Field(default=0, ge=0, description="Number of identifiable active solar regions/sunspots")
    uncertainty: float = Field(default=0.05, ge=0.0, le=1.0, description="Vision model epistemic uncertainty")


class EnvironmentPrediction(BaseModel):
    """Evaluation consumed from Agent 6 (Environment AI & Quality Prediction)."""
    model_config = ConfigDict(extra="ignore")

    environment_quality: float = Field(default=0.8, ge=0.0, le=1.0, description="Current local environmental suitability [0.0-1.0]")
    prediction_15m: float = Field(default=0.8, ge=0.0, le=1.0, description="Forecasted quality in 15 minutes [0.0-1.0]")
    prediction_30m: float = Field(default=0.75, ge=0.0, le=1.0, description="Forecasted quality in 30 minutes [0.0-1.0]")
    prediction_60m: float = Field(default=0.7, ge=0.0, le=1.0, description="Forecasted quality in 60 minutes [0.0-1.0]")
    solar_irradiance_trend: str = Field(default="STABLE", description="'RISING', 'STABLE', or 'DECLINING'")
    rain_probability_30m: float = Field(default=0.0, ge=0.0, le=1.0, description="Probability of rain precipitation within 30 min")
    uncertainty: float = Field(default=0.05, ge=0.0, le=1.0, description="Forecast model uncertainty")


class HealthFusionEvaluation(BaseModel):
    """Evaluation consumed from Agent 7 (Sensor Fusion & Observatory Health)."""
    model_config = ConfigDict(extra="ignore")

    overall_health: float = Field(default=0.95, ge=0.0, le=1.0, description="Consolidated observatory health [0.0-1.0]")
    sensor_agreement_score: float = Field(default=0.95, ge=0.0, le=1.0, description="Cross-sensor correlation/agreement [0.0-1.0]")
    anomaly_score: float = Field(default=0.05, ge=0.0, le=1.0, description="Isolation forest / statistical anomaly score [0.0-1.0]")
    is_healthy: bool = Field(default=True, description="True if no critical failures are active")
    failed_sensors: List[str] = Field(default_factory=list, description="List of sensors reporting hard offline/malfunction")
    degraded_sensors: List[str] = Field(default_factory=list, description="List of sensors showing partial drift or degradation")
    uncertainty: float = Field(default=0.05, ge=0.0, le=1.0, description="Fusion engine uncertainty")


class EdgeTelemetryState(BaseModel):
    """Edge telemetry state consumed from Agent 1 / Agent 2."""
    model_config = ConfigDict(extra="ignore")

    rain_detected: bool = Field(default=False, description="Hardware rain sensor digital flag")
    rain_raw: int = Field(default=3800, ge=0, le=4095, description="Raw 12-bit ADC reading from rain sensor")
    comms_age_sec: float = Field(default=0.5, ge=0.0, description="Elapsed seconds since last edge telemetry heartbeat")
    ambient_temp_c: float = Field(default=28.0, description="Ambient temperature in Celsius")
    pressure_hpa: float = Field(default=1013.25, description="Atmospheric pressure in hPa")
    lux: float = Field(default=55000.0, ge=0.0, description="Ambient illuminance in Lux")
    humidity_pct: float = Field(default=45.0, ge=0.0, le=100.0, description="Relative humidity percentage")
    current_edge_state: str = Field(default="STANDBY", description="Reported state of ESP32 edge state machine")


class CognitiveInput(BaseModel):
    """Composite multimodal cognitive input container aggregating all upstream sources."""
    model_config = ConfigDict(extra="ignore")

    vision: VisionEvaluation = Field(default_factory=VisionEvaluation)
    environment: EnvironmentPrediction = Field(default_factory=EnvironmentPrediction)
    health: HealthFusionEvaluation = Field(default_factory=HealthFusionEvaluation)
    edge: EdgeTelemetryState = Field(default_factory=EdgeTelemetryState)
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @classmethod
    def from_flat_dict(cls, data: Dict[str, Any]) -> CognitiveInput:
        """
        Convenience builder to construct CognitiveInput from flat or nested dictionaries,
        supporting clean input like:
        {
            "health": 0.96,
            "environment_quality": 0.83,
            "vision_quality": 0.79,
            "prediction_30m": 0.74,
            "rain": False
        }
        """
        vision_kwargs: Dict[str, Any] = {}
        env_kwargs: Dict[str, Any] = {}
        health_kwargs: Dict[str, Any] = {}
        edge_kwargs: Dict[str, Any] = {}

        if "vision" in data and isinstance(data["vision"], dict):
            vision_kwargs.update(data["vision"])
        if "environment" in data and isinstance(data["environment"], dict):
            env_kwargs.update(data["environment"])
        if "health" in data and isinstance(data["health"], dict):
            health_kwargs.update(data["health"])
        if "edge" in data and isinstance(data["edge"], dict):
            edge_kwargs.update(data["edge"])

        # Map flat aliases
        if "vision_quality" in data:
            vision_kwargs["vision_quality"] = float(data["vision_quality"])
        if "solar_disk_detected" in data:
            vision_kwargs["solar_disk_detected"] = bool(data["solar_disk_detected"])
        if "cloud_coverage" in data:
            vision_kwargs["cloud_coverage"] = float(data["cloud_coverage"])

        if "environment_quality" in data:
            env_kwargs["environment_quality"] = float(data["environment_quality"])
        if "prediction_15m" in data:
            env_kwargs["prediction_15m"] = float(data["prediction_15m"])
        if "prediction_30m" in data:
            env_kwargs["prediction_30m"] = float(data["prediction_30m"])
        if "prediction_60m" in data:
            env_kwargs["prediction_60m"] = float(data["prediction_60m"])
        if "solar_irradiance_trend" in data:
            env_kwargs["solar_irradiance_trend"] = str(data["solar_irradiance_trend"])

        if "health" in data and isinstance(data["health"], (int, float)):
            health_kwargs["overall_health"] = float(data["health"])
        elif "overall_health" in data:
            health_kwargs["overall_health"] = float(data["overall_health"])
        if "sensor_agreement_score" in data:
            health_kwargs["sensor_agreement_score"] = float(data["sensor_agreement_score"])
        if "failed_sensors" in data:
            health_kwargs["failed_sensors"] = list(data["failed_sensors"])
        if "degraded_sensors" in data:
            health_kwargs["degraded_sensors"] = list(data["degraded_sensors"])

        if "rain" in data:
            edge_kwargs["rain_detected"] = bool(data["rain"])
        if "rain_detected" in data:
            edge_kwargs["rain_detected"] = bool(data["rain_detected"])
        if "comms_age_sec" in data:
            edge_kwargs["comms_age_sec"] = float(data["comms_age_sec"])
        if "lux" in data:
            edge_kwargs["lux"] = float(data["lux"])

        return cls(
            vision=VisionEvaluation(**vision_kwargs),
            environment=EnvironmentPrediction(**env_kwargs),
            health=HealthFusionEvaluation(**health_kwargs),
            edge=EdgeTelemetryState(**edge_kwargs),
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat())
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CognitiveInput:
        """Alias for from_flat_dict to support from_dict calls."""
        return cls.from_flat_dict(data)


# -----------------------------------------------------------------------------
# Output Models & Explainability Contracts (Consumed by Agent 9 & Agent 4)
# -----------------------------------------------------------------------------

class DecisionTraceStep(BaseModel):
    """Individual atomic check in the hierarchical decision trace."""
    step: str
    level: str  # e.g., "SAFETY", "HEALTH", "DATA_QUALITY", "OBSERVATION_UTILITY"
    gate: str
    passed: bool
    details: str
    metric_value: Optional[float] = None
    threshold: Optional[float] = None


class DecisionTrace(BaseModel):
    """Complete auditable decision trace showing evaluation across all hierarchy levels."""
    trace_id: str
    timestamp: str
    hierarchy_levels_evaluated: List[str]
    steps: List[DecisionTraceStep]
    gating_interlock: SafetyGate = SafetyGate.NONE
    fused_utility_score: float
    total_uncertainty: float

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class FactorAttribution(BaseModel):
    """Impact of a single multimodal feature on the decision."""
    feature: str
    weight: float
    value: float
    impact_score: float
    direction: str  # "POSITIVE" (promotes observation) or "NEGATIVE" (inhibits observation)


class Counterfactual(BaseModel):
    """Counterfactual scenario answering what change would alter the decision."""
    condition: str
    projected_decision: DecisionType
    required_delta: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "target_decision": self.projected_decision.value,
            "condition": self.condition,
            "delta_required": self.required_delta,
        }


class DecisionExplanation(BaseModel):
    """Explainable AI breakdown explaining why a decision was reached."""
    primary_reason: str
    reasons: List[str]  # Human-readable justifications
    positive_factors: List[FactorAttribution]
    negative_factors: List[FactorAttribution]
    counterfactuals: List[Counterfactual]
    uncertainty_summary: str


class RecommendedAction(BaseModel):
    """Structured action recommendation passed to Agent 9 (Mission Planner)."""
    action: str  # e.g. "START_OBSERVATION_RUN", "PARK_TELESCOPE", "COMMENCE_GRID_SEARCH", "HOLD_POSE"
    suggested_duration_sec: int
    safe_stow_required: bool
    priority: int  # 1 (Critical) to 5 (Routine)
    guidance: str


class CognitiveDecision(BaseModel):
    """Authoritative output of Agent 8: Cognitive Decision Engine."""
    decision: DecisionType
    confidence: float = Field(ge=0.0, le=1.0)
    risk: RiskLevel
    mode: OperationalMode
    reasons: List[str]
    fused_utility: float = Field(ge=0.0, le=1.0)
    total_uncertainty: float = Field(ge=0.0, le=1.0)
    recommended_action: RecommendedAction
    explanation: DecisionExplanation
    trace: DecisionTrace
    timestamp: str

    @property
    def operational_mode(self) -> OperationalMode:
        """Alias for mode attribute."""
        return self.mode

    def to_summary_dict(self) -> Dict[str, Any]:
        """Returns the concise structured format requested in the specification."""
        return {
            "decision": self.decision.value,
            "confidence": round(self.confidence, 2),
            "risk": self.risk.value,
            "reasons": self.reasons
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serializes full decision into dictionary matching CognitiveDecision.json schema."""
        return self.model_dump()


# Alias for backwards compatibility
CognitiveDecisionResult = CognitiveDecision
CounterfactualExplanation = Counterfactual
