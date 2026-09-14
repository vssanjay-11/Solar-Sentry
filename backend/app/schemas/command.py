from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field, field_validator


class CommandVerb(str, Enum):
    OBSERVE = "OBSERVE"
    PARK = "PARK"
    SCAN = "SCAN"
    SET_SERVO = "SET_SERVO"
    SET_STATE = "SET_STATE"
    REBOOT = "REBOOT"
    CALIBRATE = "CALIBRATE"
    EMERGENCY_STOP = "EMERGENCY_STOP"


class TargetState(str, Enum):
    STANDBY = "STANDBY"
    OBSERVE = "OBSERVE"
    WAIT = "WAIT"
    SCAN = "SCAN"
    SUSPEND = "SUSPEND"
    SAFE = "SAFE"
    DEGRADED = "DEGRADED"


class CommandStatus(str, Enum):
    PENDING = "PENDING"
    DISPATCHED = "DISPATCHED"
    SUCCESS = "SUCCESS"
    REJECTED_SAFETY = "REJECTED_SAFETY"
    INVALID_PARAMS = "INVALID_PARAMS"
    EXECUTION_ERROR = "EXECUTION_ERROR"
    TIMEOUT = "TIMEOUT"


class Command(BaseModel):
    """Command schema matching docs/contracts/Command.json."""

    command_id: str = Field(default_factory=lambda: f"cmd-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')[:18]}", description="Unique identifier for tracing command execution")
    command: CommandVerb = Field(..., description="Command verb", example=CommandVerb.OBSERVE)
    device_id: Optional[str] = Field(default="esp32-sentry-01", description="Target device identifier")
    pan: Optional[int] = Field(default=None, ge=0, le=180, description="Target pan servo angle in degrees (0 to 180)")
    tilt: Optional[int] = Field(default=None, ge=0, le=180, description="Target tilt servo angle in degrees (0 to 180)")
    speed: Optional[int] = Field(default=100, ge=1, le=100, description="Speed factor percentage (1 to 100)")
    target_state: Optional[TargetState] = Field(default=None, description="Explicit state override if command is SET_STATE")
    timestamp: Optional[str] = Field(default=None, description="Dispatch ISO timestamp")

    @field_validator("timestamp", mode="before")
    @classmethod
    def set_timestamp(cls, v: Any) -> str:
        if v is None:
            return datetime.now(timezone.utc).isoformat()
        if isinstance(v, datetime):
            return v.astimezone(timezone.utc).isoformat()
        return str(v)


class CommandCreate(BaseModel):
    """User/Agent command request."""
    command: CommandVerb = Field(..., description="Command verb", example=CommandVerb.OBSERVE)
    device_id: Optional[str] = Field(default="esp32-sentry-01", description="Target device ID")
    pan: Optional[int] = Field(default=None, ge=0, le=180, description="Target pan angle")
    tilt: Optional[int] = Field(default=None, ge=0, le=180, description="Target tilt angle")
    speed: Optional[int] = Field(default=100, ge=1, le=100, description="Speed factor")
    target_state: Optional[TargetState] = Field(default=None, description="Target state if SET_STATE")


class CommandResult(BaseModel):
    """Execution confirmation matching docs/contracts/CommandResult.json."""

    command_id: str = Field(..., description="Identifier of the executed command")
    status: CommandStatus = Field(..., description="Execution outcome status")
    message: Optional[str] = Field(default="", description="Human-readable status or error description")
    current_pan: int = Field(..., ge=0, le=180, description="Achieved pan position")
    current_tilt: int = Field(..., ge=0, le=180, description="Achieved tilt position")
    current_state: str = Field(..., description="Current edge state following command execution")
    timestamp: Optional[str] = Field(default=None, description="Completion timestamp")

    @field_validator("timestamp", mode="before")
    @classmethod
    def set_timestamp(cls, v: Any) -> str:
        if v is None:
            return datetime.now(timezone.utc).isoformat()
        if isinstance(v, datetime):
            return v.astimezone(timezone.utc).isoformat()
        return str(v)


class CommandRecord(BaseModel):
    """Full server record tracking command status."""
    command: Command
    status: CommandStatus = CommandStatus.PENDING
    dispatched_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[CommandResult] = None
