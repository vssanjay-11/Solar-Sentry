"""
Solar Sentry — Mission Planning & Active Perception API Endpoints
Module: Agent 9 (Mission Planner & Active Perception)
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.providers import provider_manager
from app.schemas.command import Command


router = APIRouter(prefix="/mission", tags=["Mission Planning & Operations"])

# In-memory active mission state
_active_mission: Dict[str, Any] = {
    "mission_id": "msn-solar-track-01",
    "name": "Autonomous Active Tracking & Spectral Monitoring",
    "status": "RUNNING",
    "phase": "TRACKING",
    "target": {
        "name": "Sun (Sol)",
        "azimuth_deg": 182.4,
        "elevation_deg": 48.2,
        "airmass": 1.34,
        "solar_noon_utc": "12:15:00 UTC",
        "apparent_magnitude": -26.74
    },
    "progress_percent": 68.0,
    "started_at": datetime.now(timezone.utc).isoformat(),
    "timeline": [
        {"id": "step-1", "phase": "CALIBRATION", "title": "Sensor Calibration & Zeroing", "status": "COMPLETED", "duration_sec": 30},
        {"id": "step-2", "phase": "SLEW", "title": "Slew Gimbal to Solar Coordinates", "status": "COMPLETED", "duration_sec": 45},
        {"id": "step-3", "phase": "TRACKING", "title": "Closed-Loop Optical Tracking", "status": "RUNNING", "duration_sec": 300},
        {"id": "step-4", "phase": "VERIFICATION", "title": "Solar Disk Quality Verification", "status": "PENDING", "duration_sec": 30},
        {"id": "step-5", "phase": "STOW", "title": "Safe Horizon Park Position", "status": "PENDING", "duration_sec": 45}
    ]
}


class MissionCreateRequest(BaseModel):
    objective: str = Field(default="SOLAR_OBSERVATION")
    target_pan: Optional[int] = Field(default=90, ge=0, le=180)
    target_tilt: Optional[int] = Field(default=45, ge=0, le=180)


@router.get("/active", summary="Get active mission plan and execution timeline")
async def get_active_mission() -> Dict[str, Any]:
    telem = await provider_manager.sensor_provider.get_telemetry()
    _active_mission["target"]["pan_actual"] = telem.pan
    _active_mission["target"]["tilt_actual"] = telem.tilt
    return _active_mission


@router.post("/create", summary="Initiate new solar observation mission")
async def create_mission(req: MissionCreateRequest) -> Dict[str, Any]:
    global _active_mission
    _active_mission["status"] = "RUNNING"
    _active_mission["phase"] = "SLEW"
    _active_mission["started_at"] = datetime.now(timezone.utc).isoformat()
    _active_mission["progress_percent"] = 10.0

    # Dispatch command to actuators
    cmd = Command(
        command_id=f"cmd-msn-{int(datetime.now(timezone.utc).timestamp())}",
        command="OBSERVE",
        pan=req.target_pan,
        tilt=req.target_tilt,
        speed=100
    )
    cmd_res = await provider_manager.actuator_provider.execute_command(cmd)

    return {
        "status": "CREATED",
        "mission": _active_mission,
        "command_result": cmd_res.model_dump()
    }


@router.post("/abort", summary="Abort active mission and park actuators safely")
async def abort_mission() -> Dict[str, Any]:
    global _active_mission
    _active_mission["status"] = "ABORTED"
    _active_mission["phase"] = "STOW"

    cmd = Command(
        command_id=f"cmd-abort-{int(datetime.now(timezone.utc).timestamp())}",
        command="PARK",
        pan=90,
        tilt=0,
        speed=100
    )
    cmd_res = await provider_manager.actuator_provider.execute_command(cmd)

    return {
        "status": "ABORTED",
        "command_result": cmd_res.model_dump()
    }
