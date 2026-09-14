from datetime import datetime, timezone
from typing import List, Optional

from app.schemas.device import (
    DeviceInfo,
    DeviceRegisterRequest,
    DeviceHeartbeatRequest,
    DeviceHeartbeatResponse,
    DeviceStatus,
)
from app.repositories.base import DeviceRepository, CommandRepository
from app.core.exceptions import DeviceNotFoundError
from app.core.logging import logger


class DeviceService:
    """Manages physical edge device lifecycles and registration."""

    def __init__(self, repository: DeviceRepository, command_repository: CommandRepository):
        self.repository = repository
        self.command_repository = command_repository

    async def register_device(self, request: DeviceRegisterRequest) -> DeviceInfo:
        logger.info(f"Registering edge device '{request.device_id}' (firmware: {request.firmware_version})")
        return await self.repository.register_or_update(request)

    async def get_device(self, device_id: str) -> DeviceInfo:
        device = await self.repository.get_by_id(device_id)
        if not device:
            raise DeviceNotFoundError(device_id)
        return device

    async def list_devices(self, limit: int = 100, offset: int = 0) -> List[DeviceInfo]:
        return await self.repository.list_all(limit=limit, offset=offset)

    async def process_heartbeat(
        self,
        device_id: str,
        heartbeat: DeviceHeartbeatRequest
    ) -> DeviceHeartbeatResponse:
        device = await self.repository.get_by_id(device_id)
        if not device:
            # Auto-register device as ESP32_CONTROLLER with default profile if not registered
            from app.schemas.device import DeviceType
            reg = DeviceRegisterRequest(
                device_id=device_id,
                device_type=DeviceType.ESP32_CONTROLLER,
                firmware_version="1.0.0",
                ip_address=heartbeat.ip_address
            )
            device = await self.repository.register_or_update(reg)

        await self.repository.update_heartbeat(
            device_id=device_id,
            uptime=heartbeat.uptime_seconds,
            rssi=heartbeat.wifi_rssi,
            health=heartbeat.health or 100,
            current_state=heartbeat.current_state
        )

        # Count pending commands
        pending = await self.command_repository.list_commands(
            device_id=device_id,
            status=None
        )
        from app.schemas.command import CommandStatus
        pending_count = sum(1 for c in pending if c.status == CommandStatus.PENDING)

        return DeviceHeartbeatResponse(
            status="acknowledged",
            device_id=device_id,
            server_time=datetime.now(timezone.utc).isoformat(),
            pending_commands_count=pending_count
        )
