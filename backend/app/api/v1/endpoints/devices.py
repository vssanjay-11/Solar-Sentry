from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status

from app.schemas.device import (
    DeviceInfo,
    DeviceRegisterRequest,
    DeviceHeartbeatRequest,
    DeviceHeartbeatResponse,
)
from app.services.device_service import DeviceService
from app.api.deps import get_device_service
from app.core.security import verify_api_key

router = APIRouter(prefix="/devices", tags=["Devices & Edge Management"])


@router.post(
    "/register",
    response_model=DeviceInfo,
    status_code=status.HTTP_200_OK,
    summary="Register or update edge hardware node"
)
async def register_device(
    request: DeviceRegisterRequest,
    service: DeviceService = Depends(get_device_service),
    _auth: str = Depends(verify_api_key)
) -> DeviceInfo:
    """Registers an ESP32 or companion node with board specs and firmware version."""
    return await service.register_device(request)


@router.get(
    "",
    response_model=List[DeviceInfo],
    summary="List all registered edge devices"
)
async def list_devices(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    service: DeviceService = Depends(get_device_service)
) -> List[DeviceInfo]:
    """Retrieve list of all registered hardware and virtual devices."""
    return await service.list_devices(limit=limit, offset=offset)


@router.get(
    "/{device_id}",
    response_model=DeviceInfo,
    summary="Get single edge device information and status"
)
async def get_device(
    device_id: str,
    service: DeviceService = Depends(get_device_service)
) -> DeviceInfo:
    """Fetches device status, connectivity, uptime, and firmware version."""
    return await service.get_device(device_id)


@router.post(
    "/{device_id}/heartbeat",
    response_model=DeviceHeartbeatResponse,
    summary="Ingest edge device heartbeat"
)
async def device_heartbeat(
    device_id: str,
    heartbeat: DeviceHeartbeatRequest,
    service: DeviceService = Depends(get_device_service)
) -> DeviceHeartbeatResponse:
    """Pings server to renew lease, update RSSI/uptime, and retrieve pending command count."""
    return await service.process_heartbeat(device_id, heartbeat)


@router.get(
    "/{device_id}/health",
    summary="Get health score and diagnostic metrics for specific device"
)
async def get_device_health(
    device_id: str,
    service: DeviceService = Depends(get_device_service)
):
    device = await service.get_device(device_id)
    return {
        "device_id": device.device_id,
        "status": device.status,
        "health_score": device.health_score,
        "uptime_seconds": device.uptime_seconds,
        "wifi_rssi": device.wifi_rssi,
        "last_seen_at": device.last_seen_at
    }
