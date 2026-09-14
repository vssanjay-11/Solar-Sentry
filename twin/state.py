"""
Solar Sentry — Digital Twin State Models
Agent 10: Digital Twin + Mission Memory + Learning + Simulation + Integration

Defines the authoritative computational observatory state models:
- CURRENT STATE: Real-time telemetry, environment, optical vision, health, decision, action.
- PREDICTED STATE: Projected future states at multi-horizon (15m, 30m, 60m).
- FAULT STATE: Active faults, severity tiers, root causes, safety interlocks.
- MISSION STATE: Current mission goals, execution phase, active commands, metrics.
"""

from __future__ import annotations

import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class FaultSeverity(str, Enum):
    """Severity classification for observatory faults."""
    INFO = "INFO"
    WARNING = "WARNING"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"
    FATAL = "FATAL"


class MissionPhase(str, Enum):
    """Lifecycle phase of an autonomous observation mission."""
    IDLE = "IDLE"
    PREPARING = "PREPARING"
    SLEWING = "SLEWING"
    ACQUIRING = "ACQUIRING"
    VERIFYING = "VERIFYING"
    STOWING = "STOWING"
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"
    SUSPENDED = "SUSPENDED"


class ActiveFault(BaseModel):
    """Description of an active subsystem fault or anomaly."""
    fault_id: str = Field(..., description="Unique fault identifier")
    subsystem: str = Field(..., description="Subsystem originating fault: SENSOR, ACTUATOR, COMMS, VISION, ENVIRONMENT, SAFETY")
    severity: FaultSeverity = Field(..., description="Assessed severity level")
    code: str = Field(..., description="Diagnostic error code")
    message: str = Field(..., description="Human-readable explanation of the fault condition")
    timestamp: str = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat(),
        description="Detection timestamp"
    )
    is_recoverable: bool = Field(True, description="Whether automated recovery is permitted")
    recovery_action: Optional[str] = Field(None, description="Suggested recovery command")


class SensorSubsystemState(BaseModel):
    """State of all physical and virtual sensors."""
    temperature: float = Field(25.0, description="Ambient temperature (°C)")
    humidity: float = Field(45.0, description="Relative humidity (%)")
    pressure: float = Field(1013.25, description="Atmospheric barometric pressure (hPa)")
    lux: float = Field(50000.0, description="Solar illuminance (lux)")
    rain_raw: int = Field(3850, description="Raw ADC rain reading (dry > 2000, wet < 2000)")
    rain_detected: bool = Field(False, description="Binary rain interlock flag")
    dht22_healthy: bool = Field(True, description="DHT22 health status")
    bh1750_healthy: bool = Field(True, description="BH1750 health status")
    bmp280_healthy: bool = Field(True, description="BMP280 health status")
    rain_sensor_healthy: bool = Field(True, description="Rain sensor health status")


class ActuatorSubsystemState(BaseModel):
    """Pan/Tilt dual-axis tracking mechanism state."""
    current_pan: int = Field(90, ge=0, le=180, description="Current pan angle in degrees")
    current_tilt: int = Field(0, ge=0, le=180, description="Current tilt angle in degrees")
    target_pan: int = Field(90, ge=0, le=180, description="Commanded target pan angle")
    target_tilt: int = Field(0, ge=0, le=180, description="Commanded target tilt angle")
    is_moving: bool = Field(False, description="True if servos are currently transitioning")
    speed_percent: int = Field(100, ge=1, le=100, description="Servo speed scale")
    is_stowed: bool = Field(True, description="True if parked in safe stow position (90, 0)")


class VisionSubsystemState(BaseModel):
    """State of camera and computer vision intelligence."""
    camera_online: bool = Field(True, description="Camera connectivity state")
    image_id: Optional[str] = Field(None, description="Last processed image ID")
    quality_score: float = Field(0.0, ge=0.0, le=1.0, description="Composite optical quality score")
    solar_disk_detected: bool = Field(False, description="True if solar disk was identified")
    sunspot_count: int = Field(0, ge=0, description="Number of detected sunspot candidates")
    obstruction_score: float = Field(0.0, ge=0.0, le=1.0, description="Visual occlusion score")
    cloud_fraction: float = Field(0.0, ge=0.0, le=1.0, description="Cloud fraction estimate")
    optical_artifacts: List[str] = Field(default_factory=list, description="Active optical artifacts (glare, blur, etc.)")


class HealthSubsystemState(BaseModel):
    """Hardware health and anomaly detection state."""
    composite_health_score: int = Field(100, ge=0, le=100, description="Device overall health score (0-100)")
    anomaly_score: float = Field(0.0, ge=0.0, le=1.0, description="Multivariate anomaly probability")
    wifi_rssi: int = Field(-64, description="Wi-Fi signal strength (dBm)")
    comms_age_seconds: float = Field(0.0, description="Time elapsed since last edge heartbeat")
    is_comms_timed_out: bool = Field(False, description="True if comms age > 30 seconds")


class CognitiveDecisionState(BaseModel):
    """Current cognitive evaluation and actionable recommendation."""
    decision: str = Field("STANDBY", description="Authoritative cognitive decision (OBSERVE, WAIT, SCAN, SUSPEND, SAFE)")
    confidence: float = Field(0.95, ge=0.0, le=1.0, description="Calibrated decision confidence")
    risk_level: str = Field("LOW", description="Risk level (LOW, MODERATE, HIGH, CRITICAL)")
    operational_mode: str = Field("NORMAL", description="Operating mode (NORMAL, DEGRADED, UNCERTAIN, SAFE_MODE)")
    reasons: List[str] = Field(default_factory=list, description="Human-readable decision justifications")
    fused_utility: float = Field(0.5, ge=0.0, le=1.0, description="Fused observation utility score")
    total_uncertainty: float = Field(0.05, ge=0.0, le=1.0, description="Consolidated uncertainty score")
    recommended_action: Optional[str] = Field(None, description="Recommended executive command")


class MissionState(BaseModel):
    """Mission planning and execution state."""
    mission_id: Optional[str] = Field(None, description="Unique mission execution ID")
    objective: str = Field("IDLE", description="Current mission objective: SOLAR_SURVEY, ACTIVE_REGION_TRACKING, RAPID_RESPONSE, SAFE_SHUTDOWN")
    phase: MissionPhase = Field(MissionPhase.IDLE, description="Current mission lifecycle phase")
    active_command_id: Optional[str] = Field(None, description="In-flight command ID dispatched to edge")
    active_command_verb: Optional[str] = Field(None, description="Active command verb")
    progress_percent: float = Field(0.0, ge=0.0, le=100.0, description="Mission completion progress")
    target_pan: Optional[int] = Field(None, description="Mission targeted pan position")
    target_tilt: Optional[int] = Field(None, description="Mission targeted tilt position")
    observations_captured: int = Field(0, description="Count of science observations gathered in mission")
    mission_start_time: Optional[str] = Field(None, description="Timestamp mission commenced")


class FaultState(BaseModel):
    """Consolidated observatory fault tracking state."""
    has_active_fault: bool = Field(False, description="True if any unrecovered fault exists")
    active_faults: List[ActiveFault] = Field(default_factory=list, description="List of currently active faults")
    safety_interlock_tripped: bool = Field(False, description="True if rain, comms timeout, or critical fault tripped interlock")
    tripped_interlock_name: Optional[str] = Field(None, description="Identifier of tripped safety interlock")


class ProjectedStateSnapshot(BaseModel):
    """Projected future snapshot of observatory conditions."""
    horizon_minutes: int = Field(..., description="Projection time horizon (+15, +30, +60)")
    projected_timestamp: str = Field(..., description="Projected target ISO timestamp")
    projected_sun_elevation: float = Field(..., description="Projected solar elevation angle (°)")
    predicted_quality_score: float = Field(..., ge=0.0, le=1.0, description="Predicted observation quality")
    predicted_clearness_index: float = Field(..., ge=0.0, description="Projected clearness index kt")
    predicted_cloud_probability: float = Field(..., ge=0.0, le=1.0, description="Projected cloud occlusion probability")
    predicted_decision: str = Field(..., description="Predicted likely decision at horizon (OBSERVE, WAIT, SUSPEND)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in this horizon projection")


class PredictedFutureState(BaseModel):
    """Container for multi-horizon future predictions."""
    projections: Dict[str, ProjectedStateSnapshot] = Field(default_factory=dict, description="Projections keyed by horizon: '15m', '30m', '60m'")
    trend_direction: str = Field("STABLE", description="Overall atmospheric trend: IMPROVING, STABLE, DEGRADING")
    next_action_recommendation: str = Field("PROCEED", description="Strategic recommendation based on multi-horizon forecast")


class CurrentState(BaseModel):
    """Complete, coherent snapshot of the current physical and computational observatory state."""
    timestamp: str = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat(),
        description="State snapshot timestamp"
    )
    device_id: str = Field("esp32-sentry-01", description="Identifier of associated physical or virtual edge node")
    system_state: str = Field("STANDBY", description="Authoritative system state: BOOT, SELF_CHECK, STANDBY, OBSERVE, WAIT, SCAN, SUSPEND, FAULT, SAFE, DEGRADED")
    sensors: SensorSubsystemState = Field(default_factory=SensorSubsystemState)
    actuators: ActuatorSubsystemState = Field(default_factory=ActuatorSubsystemState)
    vision: VisionSubsystemState = Field(default_factory=VisionSubsystemState)
    health: HealthSubsystemState = Field(default_factory=HealthSubsystemState)
    decision: CognitiveDecisionState = Field(default_factory=CognitiveDecisionState)
    current_action: Optional[str] = Field(None, description="Current hardware or software action in progress")


class ObservatoryDigitalTwinState(BaseModel):
    """Master computational Digital Twin model integrating Current, Predicted, Fault, and Mission states."""
    twin_id: str = Field("twin-sentry-01", description="Unique identifier of this digital twin")
    created_at: str = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat(),
        description="Initialization timestamp"
    )
    last_updated: str = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat(),
        description="Last state update timestamp"
    )
    current: CurrentState = Field(default_factory=CurrentState)
    predicted: PredictedFutureState = Field(default_factory=PredictedFutureState)
    fault: FaultState = Field(default_factory=FaultState)
    mission: MissionState = Field(default_factory=MissionState)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()
