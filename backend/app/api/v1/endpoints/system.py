"""
Solar Sentry — System Status, Mode Toggle & Health API Endpoints
Module: Agent 2 (Backend API & Communication)
"""

from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.providers import provider_manager, SystemMode
from app.services.observatory_service import observatory_service
from app.schemas.observatory import ObservatoryState, ObservatoryHealthResponse


router = APIRouter(prefix="/system", tags=["System Status & Mode Control"])


class ModeSwitchRequest(BaseModel):
    mode: str  # "DEMO" or "HARDWARE"


class ModeSwitchResponse(BaseModel):
    status: str
    mode: str
    active_mode: str
    message: str


@router.get(
    "/status",
    response_model=Dict[str, Any],
    summary="Get aggregated system and observatory status"
)
async def get_system_status() -> Dict[str, Any]:
    """Provides authoritative system-level health, current mode, and state."""
    obs_state = await observatory_service.get_state()
    is_connected = await provider_manager.sensor_provider.is_connected()
    cam_status = await provider_manager.camera_provider.get_status()

    return {
        "project": "Solar Sentry",
        "mode": provider_manager.mode.value,
        "system_mode": provider_manager.mode.value,
        "status": "ONLINE" if (provider_manager.mode == SystemMode.DEMO or is_connected) else "OFFLINE",
        "device_connected": is_connected,
        "observatory_state": obs_state.model_dump(),
        "camera_status": cam_status,
        "active_device_id": obs_state.active_device_id,
        "hardware_verified": provider_manager.mode == SystemMode.HARDWARE and is_connected
    }


@router.get(
    "/mode",
    response_model=Dict[str, str],
    summary="Query active system mode (DEMO or HARDWARE)"
)
async def get_system_mode() -> Dict[str, str]:
    return {
        "mode": provider_manager.mode.value,
        "description": "Simulation without hardware" if provider_manager.mode == SystemMode.DEMO else "Live Physical Prototype"
    }


@router.post(
    "/mode",
    response_model=ModeSwitchResponse,
    summary="Switch system mode between DEMO and HARDWARE"
)
async def switch_system_mode(req: ModeSwitchRequest) -> ModeSwitchResponse:
    """Seamlessly switches active system mode without requiring application restart."""
    target = req.mode.upper().strip()
    if target not in ["DEMO", "HARDWARE"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid system mode '{req.mode}'. Must be 'DEMO' or 'HARDWARE'."
        )

    new_mode = provider_manager.set_mode(target)
    msg = (
        "System transitioned to DEMO MODE. Simulating sensors, camera, and missions."
        if new_mode == SystemMode.DEMO else
        "System transitioned to LIVE HARDWARE MODE. Awaiting physical ESP32 and ESP32-CAM telemetry."
    )

    return ModeSwitchResponse(
        status="SUCCESS",
        mode=new_mode.value,
        active_mode=new_mode.value,
        message=msg
    )


@router.get(
    "/health",
    response_model=ObservatoryHealthResponse,
    summary="Subsystem health diagnosis matrix"
)
async def get_system_health() -> ObservatoryHealthResponse:
    return await observatory_service.get_health_status()
