from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from app.schemas.telemetry import DeviceState


class SubsystemHealthStatus(BaseModel):
    name: str
    status: str = "OK"  # OK, WARNING, ERROR, DEGRADED
    score: int = 100
    details: Optional[Dict[str, Any]] = None


class ObservatoryHealthResponse(BaseModel):
    overall_status: str = "HEALTHY"  # HEALTHY, DEGRADED, CRITICAL
    health_score: int = 100
    timestamp: str
    subsystems: List[SubsystemHealthStatus] = []
    active_alarms: List[str] = []


class ObservatoryPose(BaseModel):
    pan: int = 90
    tilt: int = 0
    moving: bool = False
    target_pan: Optional[int] = None
    target_tilt: Optional[int] = None


class EnvironmentalSummary(BaseModel):
    temperature_c: float = 0.0
    humidity_pct: float = 0.0
    pressure_hpa: float = 1013.25
    lux: float = 0.0
    rain_detected: bool = False
    rain_raw: int = 4095


class SafetyStatus(BaseModel):
    rain_emergency: bool = False
    comms_timeout: bool = False
    edge_overheat: bool = False
    interlocks_triggered: List[str] = []
    failsafe_active: bool = False


class ObservatoryState(BaseModel):
    """Authoritative cognitive observatory state matching contracts/system-state.md."""

    state: DeviceState = DeviceState.STANDBY
    state_description: str = "Ready, awaiting observation or mission directives"
    timestamp: str
    pose: ObservatoryPose = Field(default_factory=ObservatoryPose)
    environment: EnvironmentalSummary = Field(default_factory=EnvironmentalSummary)
    safety: SafetyStatus = Field(default_factory=SafetyStatus)
    active_device_id: Optional[str] = None
    device_online: bool = False
    camera_online: bool = False
    health_score: int = 100
    active_mission_id: Optional[str] = None
    ai_status: Dict[str, Any] = Field(default_factory=dict)
