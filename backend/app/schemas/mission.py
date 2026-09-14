from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class MissionStatus(str, Enum):
    PENDING = "PENDING"
    SCHEDULED = "SCHEDULED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"
    FAILED = "FAILED"


class MissionType(str, Enum):
    SOLAR_DISK_SCAN = "SOLAR_DISK_SCAN"
    SUNSPOT_TRACKING = "SUNSPOT_TRACKING"
    LIMB_DARKENING = "LIMB_DARKENING"
    ENVIRONMENT_SURVEY = "ENVIRONMENT_SURVEY"
    CALIBRATION = "CALIBRATION"
    MANUAL = "MANUAL"


class MissionCreate(BaseModel):
    title: str = Field(..., example="Morning Solar Disk Scan")
    mission_type: MissionType = Field(default=MissionType.SOLAR_DISK_SCAN)
    priority: int = Field(default=5, ge=1, le=10)
    target_pan: Optional[int] = Field(default=90, ge=0, le=180)
    target_tilt: Optional[int] = Field(default=45, ge=0, le=180)
    duration_seconds: int = Field(default=60, ge=5, le=3600)
    parameters: Dict[str, Any] = Field(default_factory=dict)


class Mission(BaseModel):
    mission_id: str
    title: str
    mission_type: MissionType
    status: MissionStatus = MissionStatus.PENDING
    priority: int = 5
    target_pan: Optional[int] = 90
    target_tilt: Optional[int] = 45
    duration_seconds: int = 60
    parameters: Dict[str, Any] = Field(default_factory=dict)
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
