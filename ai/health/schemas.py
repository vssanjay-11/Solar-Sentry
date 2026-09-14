"""Data schemas and type definitions for Solar Sentry Sensor Fusion & Health Anomaly AI.

Agent 7 Ownership.
Adheres strictly to the multi-agent contracts and produces structured health evaluations
consumed downstream by Agent 8 (Cognitive Decision Engine).
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict


class HealthState(str, Enum):
    """Authoritative observatory health states."""
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    OFFLINE = "OFFLINE"


class FaultSeverity(str, Enum):
    """Categorization of fault severity level."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AnomalyType(str, Enum):
    """Types of detected sensor, communication, or actuator anomalies."""
    OUT_OF_RANGE = "OUT_OF_RANGE"
    STUCK_STALE = "STUCK_STALE"
    SPIKE = "SPIKE"
    DRIFT = "DRIFT"
    CROSS_SENSOR_INCONSISTENCY = "CROSS_SENSOR_INCONSISTENCY"
    DROPOUT_DISCONNECTED = "DROPOUT_DISCONNECTED"
    COMMS_ANOMALY = "COMMS_ANOMALY"
    ACTUATOR_ANOMALY = "ACTUATOR_ANOMALY"
    NOISE_VARIANCE = "NOISE_VARIANCE"


class DegradedMode(str, Enum):
    """Degraded mode operational recommendations for downstream cognitive decisions."""
    NORMAL_OPERATION = "NORMAL_OPERATION"
    USE_BMP280_TEMPERATURE = "USE_BMP280_TEMPERATURE"
    USE_DHT22_TEMPERATURE = "USE_DHT22_TEMPERATURE"
    INFER_HUMIDITY_FROM_HISTORY = "INFER_HUMIDITY_FROM_HISTORY"
    INFER_PRESSURE_FROM_HISTORY = "INFER_PRESSURE_FROM_HISTORY"
    OPTICAL_CONFIRMATION_REQUIRED = "OPTICAL_CONFIRMATION_REQUIRED"
    REDUCED_SLEW_VELOCITY = "REDUCED_SLEW_VELOCITY"
    SAFE_STOW_RECOMMENDED = "SAFE_STOW_RECOMMENDED"
    COMMS_FAILSAFE_RECOMMENDED = "COMMS_FAILSAFE_RECOMMENDED"


class AnomalyReport(BaseModel):
    """Structured report for an individual detected anomaly."""
    model_config = ConfigDict(extra="ignore")

    sensor: str = Field(..., description="Target sensor or subsystem (e.g. 'humidity', 'temperature', 'rain', 'comms', 'pan_servo')")
    type: AnomalyType = Field(..., description="Classification of anomaly")
    severity: FaultSeverity = Field(..., description="Assessed severity level")
    description: str = Field(..., description="Human-readable explanation of the anomaly")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence in anomaly diagnosis (0.0 to 1.0)")
    metric_name: Optional[str] = Field(default=None, description="Specific telemetry variable name")
    observed_value: Optional[float] = Field(default=None, description="Actual observed metric value")
    expected_range: Optional[List[float]] = Field(default=None, description="Expected min/max boundary or normal interval")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Detection timestamp in ISO-8601 UTC"
    )


class SensorConfidence(BaseModel):
    """Per-sensor health and confidence tracking."""
    model_config = ConfigDict(extra="ignore")

    sensor: str = Field(..., description="Sensor identifier ('dht22', 'bmp280', 'bh1750', 'rain')")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Dynamic confidence score from 0.0 (unusable) to 1.0 (perfect)")
    status: str = Field(default="HEALTHY", description="Status string: HEALTHY, DEGRADED, FAULTY, or DROPPED")
    dropout: bool = Field(default=False, description="Whether sensor has dropped out or disconnected")
    stale: bool = Field(default=False, description="Whether sensor reading is stuck / unchanging")
    drift: bool = Field(default=False, description="Whether long-term calibration drift is suspected")
    last_valid_value: Optional[float] = Field(default=None, description="Last known trustworthy value")
    degradation_reason: Optional[str] = Field(default=None, description="Reason if confidence < 1.0")


class FusedEnvironmentalState(BaseModel):
    """Multimodal fused environmental state combining redundant sensors and physical laws."""
    model_config = ConfigDict(extra="ignore")

    temperature: float = Field(..., description="Best estimate ambient temperature in Celsius (Bayesian/Inverse-variance fused)")
    temperature_uncertainty: float = Field(default=0.5, description="1-sigma uncertainty in temperature (°C)")
    humidity: float = Field(..., ge=0.0, le=100.0, description="Relative humidity percentage")
    humidity_uncertainty: float = Field(default=2.0, description="1-sigma uncertainty in humidity (%)")
    pressure: float = Field(..., description="Atmospheric barometric pressure in hPa")
    pressure_uncertainty: float = Field(default=1.0, description="1-sigma uncertainty in pressure (hPa)")
    lux: float = Field(..., ge=0.0, description="Ambient illuminance in Lux")
    lux_uncertainty: float = Field(default=50.0, description="Estimated lux measurement uncertainty")
    dew_point: float = Field(..., description="Computed dew point in Celsius using Magnus formula")
    vapor_pressure_deficit_kpa: float = Field(default=0.0, description="Vapor pressure deficit in kPa")
    rain_confirmed: bool = Field(default=False, description="Cross-validated precipitation confirmation flag")
    primary_temp_source: str = Field(default="FUSED", description="Source of temperature: 'FUSED', 'DHT22', 'BMP280'")


class ActuatorHealthIndicator(BaseModel):
    """Actuator tracking performance and mechanical health telemetry."""
    model_config = ConfigDict(extra="ignore")

    pan_healthy: bool = Field(default=True, description="Pan servo operational validity")
    tilt_healthy: bool = Field(default=True, description="Tilt servo operational validity")
    pan_tracking_error_deg: float = Field(default=0.0, description="Discrepancy between commanded and actual pan angle")
    tilt_tracking_error_deg: float = Field(default=0.0, description="Discrepancy between commanded and actual tilt angle")
    slew_in_progress: bool = Field(default=False, description="Whether actuators are actively slewing")
    stall_suspected: bool = Field(default=False, description="True if movement commanded but no angle change observed")
    jitter_score: float = Field(default=0.0, ge=0.0, le=1.0, description="High-frequency mechanical hunting / oscillation score")


class CommsHealthIndicator(BaseModel):
    """Edge-to-backend communication link health and telemetry freshness."""
    model_config = ConfigDict(extra="ignore")

    freshness_seconds: float = Field(..., ge=0.0, description="Seconds elapsed since last received telemetry")
    packet_jitter_seconds: float = Field(default=0.0, ge=0.0, description="Variance in packet inter-arrival intervals")
    rssi_dbm: int = Field(default=-65, description="Edge Wi-Fi RSSI in dBm")
    rssi_quality: str = Field(default="GOOD", description="Categorized Wi-Fi signal quality (EXCELLENT, GOOD, FAIR, POOR, CRITICAL)")
    dropout_count: int = Field(default=0, ge=0, description="Number of missed telemetry intervals")
    heartbeat_stalled: bool = Field(default=False, description="True if comms interval exceeded safety timeout")


class RootCauseEvidence(BaseModel):
    """Diagnosed root cause evidence for detected faults and anomalies."""
    model_config = ConfigDict(extra="ignore")

    anomaly_id: str = Field(..., description="Unique fault or anomaly identifier")
    suspected_component: str = Field(..., description="Hardware component or interface at fault")
    root_cause: str = Field(..., description="Technical diagnosis of the failure mechanism")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in this diagnosis")
    evidence_metrics: Dict[str, Any] = Field(default_factory=dict, description="Numerical / diagnostic evidence")
    recommended_action: str = Field(..., description="Suggested remediation or mitigating operational mode")


class ObservatoryHealthReport(BaseModel):
    """Authoritative structured output produced by Agent 7.

    Adheres strictly to docs/contracts/ObservatoryHealthReport.json and provides
    the bridge into Agent 8's Cognitive Decision Engine.
    """
    model_config = ConfigDict(extra="ignore")

    health: HealthState = Field(..., description="Current observatory health classification")
    score: int = Field(..., ge=0, le=100, description="Composite health score from 0 (failed) to 100 (optimal)")
    anomalies: List[AnomalyReport] = Field(default_factory=list, description="List of active anomalies")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Composite observatory sensory confidence")
    sensor_confidences: Dict[str, float] = Field(
        default_factory=dict,
        description="Per-sensor confidence scores (0.0 to 1.0)"
    )
    fused_environment: FusedEnvironmentalState = Field(..., description="Multimodal fused physical parameters")
    actuator_health: ActuatorHealthIndicator = Field(
        default_factory=ActuatorHealthIndicator,
        description="Actuator performance indicators"
    )
    comms_health: CommsHealthIndicator = Field(
        default_factory=lambda: CommsHealthIndicator(freshness_seconds=0.0),
        description="Communication and telemetry freshness indicators"
    )
    degraded_recommendation: Optional[DegradedMode] = Field(
        default=DegradedMode.NORMAL_OPERATION,
        description="Recommended operational degraded mode"
    )
    root_cause_evidence: List[RootCauseEvidence] = Field(
        default_factory=list,
        description="Evidence records explaining diagnosed root causes"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 UTC timestamp of the health assessment"
    )

    def to_health_fusion_evaluation(self) -> Dict[str, Any]:
        """Maps output to Agent 8's HealthFusionEvaluation schema in ai/decision/types.py."""
        failed = [s for s, c in self.sensor_confidences.items() if c <= 0.1]
        degraded = [s for s, c in self.sensor_confidences.items() if 0.1 < c < 0.8]

        # Sensor agreement score (penalized by cross-sensor inconsistencies)
        disagreement_count = sum(1 for a in self.anomalies if a.type == AnomalyType.CROSS_SENSOR_INCONSISTENCY)
        agreement_score = max(0.0, 1.0 - disagreement_count * 0.35)

        anomaly_score = 0.0
        for a in self.anomalies:
            if a.severity == FaultSeverity.CRITICAL:
                anomaly_score = max(anomaly_score, 0.95)
            elif a.severity == FaultSeverity.HIGH:
                anomaly_score = max(anomaly_score, 0.70)
            elif a.severity == FaultSeverity.MEDIUM:
                anomaly_score = max(anomaly_score, 0.35)
            elif a.severity == FaultSeverity.LOW:
                anomaly_score = max(anomaly_score, 0.15)

        is_healthy = (
            self.health in [HealthState.HEALTHY, HealthState.DEGRADED]
            and not any(a.severity == FaultSeverity.CRITICAL for a in self.anomalies)
            and not self.comms_health.heartbeat_stalled
        )

        return {
            "overall_health": round(self.score / 100.0, 4),
            "sensor_agreement_score": round(agreement_score, 4),
            "anomaly_score": round(anomaly_score, 4),
            "is_healthy": is_healthy,
            "failed_sensors": failed,
            "degraded_sensors": degraded,
            "uncertainty": round(max(0.01, 1.0 - self.confidence), 4)
        }

    def to_agent8_health_input(self) -> Dict[str, Any]:
        """Maps output to Agent 8's Agent7HealthInput or HealthFusionEvaluation dictionary."""
        return self.to_health_fusion_evaluation()

