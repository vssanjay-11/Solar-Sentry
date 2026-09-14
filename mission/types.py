"""Solar Sentry — Autonomous Mission Planner Types & Contracts.

Agent 9 Ownership.
Defines data structures for missions, objectives, candidate evaluations,
action sequences, command abstractions, and closed-loop verification.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import uuid


class MissionState(str, Enum):
    """Lifecycle states of an autonomous mission."""
    PENDING = "PENDING"
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ABORTED = "ABORTED"
    SUSPENDED = "SUSPENDED"


class MissionType(str, Enum):
    """Supported mission categories aligned with Agent 8 cognitive directives."""
    OBSERVE = "OBSERVE"
    SCAN = "SCAN"
    WAIT = "WAIT"
    SUSPEND = "SUSPEND"
    SAFE = "SAFE"
    ACTIVE_PERCEPTION = "ACTIVE_PERCEPTION"
    CALIBRATE = "CALIBRATE"


class ActionVerb(str, Enum):
    """Hardware command verbs conforming to docs/contracts/Command.json."""
    OBSERVE = "OBSERVE"
    PARK = "PARK"
    SCAN = "SCAN"
    SET_SERVO = "SET_SERVO"
    SET_STATE = "SET_STATE"
    REBOOT = "REBOOT"
    CALIBRATE = "CALIBRATE"
    EMERGENCY_STOP = "EMERGENCY_STOP"


class ActionStatus(str, Enum):
    """Execution status for an individual mission action."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    SKIPPED = "SKIPPED"


class VerificationStatus(str, Enum):
    """Post-action verification outcomes."""
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    DEGRADED = "DEGRADED"
    SKIPPED = "SKIPPED"


class FailureReason(str, Enum):
    """Root causes for mission failure or interruption."""
    NONE = "NONE"
    TIMEOUT = "TIMEOUT"
    ACTUATOR_ERROR = "ACTUATOR_ERROR"
    QUALITY_DEGRADATION = "QUALITY_DEGRADATION"
    SAFETY_INTERLOCK = "SAFETY_INTERLOCK"
    RAIN_OVERRIDE = "RAIN_OVERRIDE"
    COMMS_FAILURE = "COMMS_FAILURE"
    THERMAL_FAULT = "THERMAL_FAULT"
    UNKNOWN = "UNKNOWN"


@dataclass
class CandidateRegion:
    """Observation direction / region candidate with multi-factor scoring."""
    region_id: str
    pan: int
    tilt: int
    predicted_quality: float = 0.0
    confidence: float = 1.0
    uncertainty: float = 0.0
    displacement_cost: float = 0.0
    composite_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "region_id": self.region_id,
            "pan": self.pan,
            "tilt": self.tilt,
            "predicted_quality": round(self.predicted_quality, 4),
            "confidence": round(self.confidence, 4),
            "uncertainty": round(self.uncertainty, 4),
            "displacement_cost": round(self.displacement_cost, 4),
            "composite_score": round(self.composite_score, 4),
            "metadata": dict(self.metadata),
        }


@dataclass
class Command:
    """Control command conforming strictly to docs/contracts/Command.json."""
    command_id: str
    command: ActionVerb | str
    pan: Optional[int] = None
    tilt: Optional[int] = None
    speed: int = 100
    target_state: Optional[str] = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        cmd_verb = self.command.value if isinstance(self.command, ActionVerb) else str(self.command)
        d: Dict[str, Any] = {
            "command_id": self.command_id,
            "command": cmd_verb,
            "timestamp": self.timestamp,
        }
        if self.pan is not None:
            d["pan"] = int(self.pan)
        if self.tilt is not None:
            d["tilt"] = int(self.tilt)
        if self.speed is not None:
            d["speed"] = int(self.speed)
        if self.target_state is not None:
            d["target_state"] = str(self.target_state)
        return d


@dataclass
class CommandResult:
    """Execution confirmation conforming strictly to docs/contracts/CommandResult.json."""
    command_id: str
    status: str
    message: str = ""
    current_pan: int = 90
    current_tilt: int = 0
    current_state: str = "STANDBY"
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CommandResult:
        return cls(
            command_id=data.get("command_id", "unknown"),
            status=data.get("status", "EXECUTION_ERROR"),
            message=data.get("message", ""),
            current_pan=int(data.get("current_pan", 90)),
            current_tilt=int(data.get("current_tilt", 0)),
            current_state=data.get("current_state", "STANDBY"),
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat())
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "command_id": self.command_id,
            "status": self.status,
            "message": self.message,
            "current_pan": self.current_pan,
            "current_tilt": self.current_tilt,
            "current_state": self.current_state,
            "timestamp": self.timestamp,
        }


@dataclass
class VerificationResult:
    """Outcome of closed-loop post-action verification."""
    success: bool
    status: VerificationStatus = VerificationStatus.SUCCESS
    quality_before: float = 0.0
    quality_after: float = 0.0
    delta_quality: float = 0.0
    pan_target: Optional[int] = None
    pan_actual: Optional[int] = None
    tilt_target: Optional[int] = None
    tilt_actual: Optional[int] = None
    converged: bool = True
    message: str = "Verification passed"
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "status": self.status.value if isinstance(self.status, VerificationStatus) else str(self.status),
            "quality_before": round(self.quality_before, 4),
            "quality_after": round(self.quality_after, 4),
            "delta_quality": round(self.delta_quality, 4),
            "pan_target": self.pan_target,
            "pan_actual": self.pan_actual,
            "tilt_target": self.tilt_target,
            "tilt_actual": self.tilt_actual,
            "converged": self.converged,
            "message": self.message,
            "timestamp": self.timestamp,
        }


@dataclass
class MissionAction:
    """Discrete action inside a planned mission action sequence."""
    action_id: str
    action_type: str
    command: Command
    timeout_sec: float = 5.0
    max_retries: int = 2
    retry_count: int = 0
    status: ActionStatus = ActionStatus.PENDING
    result: Optional[CommandResult] = None
    verification: Optional[VerificationResult] = None
    error_message: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "command": self.command.to_dict(),
            "timeout_sec": self.timeout_sec,
            "max_retries": self.max_retries,
            "retry_count": self.retry_count,
            "status": self.status.value if isinstance(self.status, ActionStatus) else str(self.status),
        }
        if self.result is not None:
            d["result"] = self.result.to_dict()
        if self.verification is not None:
            d["verification"] = self.verification.to_dict()
        if self.error_message:
            d["error_message"] = self.error_message
        return d


@dataclass
class MissionObjective:
    """Structured mission goal with target thresholds."""
    name: str
    description: str = ""
    target_quality_min: float = 0.70
    max_uncertainty: float = 0.25
    target_region: Optional[str] = None
    active_perception_required: bool = False
    criteria: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "target_quality_min": self.target_quality_min,
            "max_uncertainty": self.max_uncertainty,
            "target_region": self.target_region,
            "active_perception_required": self.active_perception_required,
            "criteria": dict(self.criteria),
        }


@dataclass
class ActivePerceptionInsight:
    """Epistemic state and information gain from an active perception probe."""
    triggered: bool = False
    trigger_reason: str = ""
    uncertainty_before: float = 0.0
    uncertainty_after: float = 0.0
    information_gain: float = 0.0
    recommended_scan_pattern: str = "BRACKET_3PT"
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "triggered": self.triggered,
            "trigger_reason": self.trigger_reason,
            "uncertainty_before": round(self.uncertainty_before, 4),
            "uncertainty_after": round(self.uncertainty_after, 4),
            "information_gain": round(self.information_gain, 4),
            "recommended_scan_pattern": self.recommended_scan_pattern,
            "notes": self.notes,
        }


@dataclass
class MissionResult:
    """Complete post-execution audit and metrics result."""
    mission_id: str
    objective: str
    status: MissionState
    total_duration_sec: float
    actions_count: int
    successful_actions: int
    failed_actions: int
    candidate_evaluations: List[Dict[str, Any]] = field(default_factory=list)
    selected_candidate: Optional[Dict[str, Any]] = None
    commands_dispatched: List[Dict[str, Any]] = field(default_factory=list)
    command_results: List[Dict[str, Any]] = field(default_factory=list)
    verification_summary: Optional[Dict[str, Any]] = None
    active_perception_insights: Optional[Dict[str, Any]] = None
    failure_reason: Optional[str] = None
    safe_recovery_executed: bool = False
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "objective": self.objective,
            "status": self.status.value if isinstance(self.status, MissionState) else str(self.status),
            "total_duration_sec": round(self.total_duration_sec, 3),
            "actions_count": self.actions_count,
            "successful_actions": self.successful_actions,
            "failed_actions": self.failed_actions,
            "candidate_evaluations": list(self.candidate_evaluations),
            "selected_candidate": self.selected_candidate,
            "commands_dispatched": list(self.commands_dispatched),
            "command_results": list(self.command_results),
            "verification_summary": self.verification_summary,
            "active_perception_insights": self.active_perception_insights,
            "failure_reason": self.failure_reason,
            "safe_recovery_executed": self.safe_recovery_executed,
            "timestamp": self.timestamp,
        }


@dataclass
class Mission:
    """The master Mission entity planned and managed by Agent 9."""
    mission_id: str
    name: str
    objective: MissionObjective
    mission_type: MissionType
    priority: int = 50
    actions: List[MissionAction] = field(default_factory=list)
    candidates: List[CandidateRegion] = field(default_factory=list)
    selected_candidate: Optional[CandidateRegion] = None
    status: MissionState = MissionState.PENDING
    timeout_sec: float = 60.0
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    audit_trail: List[str] = field(default_factory=list)
    active_perception: Optional[ActivePerceptionInsight] = None
    result: Optional[MissionResult] = None

    def log(self, entry: str) -> None:
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3]
        self.audit_trail.append(f"[{ts}] {entry}")

    def to_plan_dict(self) -> Dict[str, Any]:
        """Conforms to docs/contracts/MissionPlan.json."""
        return {
            "mission_id": self.mission_id,
            "name": self.name,
            "mission_type": self.mission_type.value,
            "priority": self.priority,
            "objective": self.objective.to_dict(),
            "status": self.status.value,
            "candidates": [c.to_dict() for c in self.candidates],
            "selected_candidate": self.selected_candidate.to_dict() if self.selected_candidate else None,
            "actions": [a.to_dict() for a in self.actions],
            "created_at": self.created_at,
            "timeout_sec": self.timeout_sec,
        }
