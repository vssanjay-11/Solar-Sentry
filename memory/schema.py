"""
Solar Sentry — Mission Memory Data Schemas
Agent 10: Digital Twin + Mission Memory + Learning + Simulation + Integration

Defines structured, audit-grade models for storing and retrieving complete mission life cycles:
- mission objective
- conditions
- decisions
- actions
- observations
- results
- quality
- failures
- verification
- lessons
"""

from __future__ import annotations

import datetime
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MissionObjectiveType(str, Enum):
    SOLAR_SURVEY = "SOLAR_SURVEY"
    ACTIVE_REGION_TRACKING = "ACTIVE_REGION_TRACKING"
    HIGH_CADENCE_BURST = "HIGH_CADENCE_BURST"
    CALIBRATION = "CALIBRATION"
    RAPID_RESPONSE = "RAPID_RESPONSE"
    SAFE_SHUTDOWN = "SAFE_SHUTDOWN"
    SCAN_SEARCH = "SCAN_SEARCH"


class MissionStatus(str, Enum):
    PLANNED = "PLANNED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"
    FAILED = "FAILED"
    SUSPENDED = "SUSPENDED"


class MissionObjective(BaseModel):
    """Scientific objective and targets of the observation mission."""
    objective_type: MissionObjectiveType = Field(..., description="Target mission profile")
    target_description: str = Field("Routine full-disk solar survey", description="Human-readable description")
    target_pan: Optional[int] = Field(None, ge=0, le=180, description="Target pan angle")
    target_tilt: Optional[int] = Field(None, ge=0, le=180, description="Target tilt angle")
    cadence_seconds: float = Field(5.0, description="Requested observation capture cadence")
    max_duration_seconds: float = Field(300.0, description="Maximum permitted mission duration")
    priority: int = Field(2, ge=1, le=5, description="Scheduling priority (1=highest)")


class MissionCondition(BaseModel):
    """Environmental, atmospheric, and edge conditions at mission start."""
    temperature: float = Field(..., description="Ambient temperature (°C)")
    humidity: float = Field(..., description="Relative humidity (%)")
    pressure: float = Field(..., description="Barometric pressure (hPa)")
    lux: float = Field(..., description="Illuminance (lx)")
    solar_elevation_deg: float = Field(..., description="Solar elevation angle (°)")
    clearness_index: float = Field(..., description="Atmospheric clearness kt")
    predicted_quality_15m: float = Field(..., description="Agent 6 15m forecast")
    weather_risk: str = Field("LOW", description="Assessed weather risk level")
    hardware_health_score: int = Field(100, description="Edge health score (0-100)")


class MissionDecision(BaseModel):
    """Cognitive decision evaluating mission feasibility."""
    decision: str = Field(..., description="Authoritative decision: OBSERVE, WAIT, SCAN, SUSPEND, SAFE")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Calibrated confidence")
    risk_level: str = Field(..., description="Assessed risk level")
    operational_mode: str = Field(..., description="Operating mode: NORMAL, DEGRADED, UNCERTAIN, SAFE_MODE")
    reasons: List[str] = Field(default_factory=list, description="Justification factors")
    fused_utility: float = Field(..., description="Composite utility score")
    trace_id: Optional[str] = Field(None, description="Diagnostic trace identifier")


class MissionAction(BaseModel):
    """Control command dispatched to physical or virtual edge during mission."""
    command_id: str = Field(..., description="Unique command ID")
    command_verb: str = Field(..., description="Command verb: OBSERVE, PARK, SCAN, SET_SERVO, etc.")
    pan: Optional[int] = Field(None, description="Commanded pan")
    tilt: Optional[int] = Field(None, description="Commanded tilt")
    speed: int = Field(100, description="Servo speed scale percentage")
    dispatched_timestamp: str = Field(..., description="Dispatch ISO timestamp")
    execution_status: str = Field("SUCCESS", description="Execution result from edge: SUCCESS, REJECTED_SAFETY, etc.")
    edge_response_message: Optional[str] = Field(None, description="Status message from edge controller")


class MissionObservation(BaseModel):
    """Scientific observation record captured during mission."""
    image_id: str = Field(..., description="Unique image identifier")
    timestamp: str = Field(..., description="Acquisition timestamp")
    pan_actual: int = Field(..., description="Actual achieved pan angle")
    tilt_actual: int = Field(..., description="Actual achieved tilt angle")
    quality_score: float = Field(..., description="Composite visual quality score")
    solar_disk_detected: bool = Field(..., description="Whether solar disk was recognized")
    sunspot_count: int = Field(0, description="Detected sunspots")
    obstruction_score: float = Field(0.0, description="Occlusion fraction")
    cloud_fraction: float = Field(0.0, description="Cloud fraction")


class MissionFailure(BaseModel):
    """Failure, trip, or exception occurred during mission."""
    failure_type: str = Field(..., description="Failure category: SAFETY_INTERLOCK, COMMS_TIMEOUT, HARDWARE_FAULT, POOR_IMAGE")
    error_code: str = Field(..., description="Specific diagnostic error code")
    description: str = Field(..., description="Human-readable explanation")
    occurred_at_sec: float = Field(..., description="Elapsed mission seconds when failure occurred")
    recovery_attempted: bool = Field(False, description="Whether automated recovery was initiated")
    recovery_successful: bool = Field(False, description="Whether recovery succeeded")


class MissionVerification(BaseModel):
    """Post-action closed-loop verification results."""
    actuator_aligned: bool = Field(True, description="Whether pan/tilt servos reached target within tolerance")
    optical_disk_verified: bool = Field(True, description="Whether solar disk was localized in optical center")
    quality_threshold_met: bool = Field(True, description="Whether composite quality met science requirements")
    environmental_safety_confirmed: bool = Field(True, description="Whether weather remained safe throughout")
    overall_verification_passed: bool = Field(True, description="Composite verification verdict")
    verification_score: float = Field(1.0, ge=0.0, le=1.0, description="Normalized verification fidelity score")
    notes: List[str] = Field(default_factory=list, description="Verification observations and audit notes")


class MissionLesson(BaseModel):
    """Synthesized retrospective lessons learned from mission execution."""
    observation_yield_rating: str = Field("OPTIMAL", description="OPTIMAL, ACCEPTABLE, SUBOPTIMAL, UNUSABLE")
    forecast_accuracy_delta: float = Field(0.0, description="Actual quality minus predicted quality (positive = better than expected)")
    weather_risk_assessment_accuracy: str = Field("ACCURATE", description="ACCURATE, OVERESTIMATED, UNDERESTIMATED")
    key_takeaway: str = Field(..., description="High-level lesson distilled for continual learning")
    feedback_notes: Optional[str] = Field(None, description="Operator or AI notes")


class MissionRecord(BaseModel):
    """Master audit-grade record for an autonomous solar observation mission."""
    mission_id: str = Field(
        default_factory=lambda: f"msn-{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6]}",
        description="Globally unique mission ID"
    )
    created_at: str = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat(),
        description="Mission creation timestamp"
    )
    completed_at: Optional[str] = Field(None, description="Mission completion timestamp")
    status: MissionStatus = Field(MissionStatus.PLANNED, description="Final mission status")
    objective: MissionObjective = Field(..., description="Target objective")
    initial_conditions: MissionCondition = Field(..., description="Initial observatory conditions")
    cognitive_decision: MissionDecision = Field(..., description="Authoritative cognitive decision")
    actions: List[MissionAction] = Field(default_factory=list, description="Dispatched commands")
    observations: List[MissionObservation] = Field(default_factory=list, description="Acquired observations")
    failures: List[MissionFailure] = Field(default_factory=list, description="Failures or safety trips")
    verification: Optional[MissionVerification] = Field(None, description="Post-action verification")
    lessons: Optional[MissionLesson] = Field(None, description="Post-mission retrospective lessons")
    composite_quality_score: float = Field(0.0, description="Overall achieved quality score")

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()
