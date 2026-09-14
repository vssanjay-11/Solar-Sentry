import uuid
from datetime import datetime, timezone
from typing import List, Optional

from app.schemas.command import (
    Command,
    CommandCreate,
    CommandRecord,
    CommandResult,
    CommandStatus,
    CommandVerb,
)
from app.schemas.telemetry import DeviceState
from app.repositories.base import CommandRepository
from app.services.observatory_service import observatory_service
from app.core.exceptions import InvalidCommandError, SafetyViolationError
from app.core.event_bus import (
    event_bus,
    TOPIC_COMMAND_DISPATCHED,
    TOPIC_COMMAND_RESULT,
)
from app.core.logging import logger


class CommandService:
    """Manages command dispatch, safety gatekeeping, edge polling, and execution feedback."""

    def __init__(self, repository: CommandRepository):
        self.repository = repository

    async def dispatch_command(self, request: CommandCreate) -> CommandRecord:
        # Check current observatory state and safety interlocks
        current_state = await observatory_service.get_state()
        
        # Rule 1: If rain is detected, only PARK, REBOOT, or EMERGENCY_STOP are allowed
        if current_state.safety.rain_emergency:
            if request.command not in [CommandVerb.PARK, CommandVerb.EMERGENCY_STOP, CommandVerb.REBOOT]:
                raise SafetyViolationError(
                    message=f"Command '{request.command.value}' rejected: Active rain emergency interlock is engaged.",
                    details={"interlock": "RAIN_DETECTED", "state": current_state.state}
                )

        # Rule 2: Validate pan/tilt angles if provided
        if request.pan is not None and not (0 <= request.pan <= 180):
            raise InvalidCommandError(
                message=f"Pan angle {request.pan} is outside physical actuator boundary (0-180 deg).",
                details={"pan": request.pan}
            )
        if request.tilt is not None and not (0 <= request.tilt <= 180):
            raise InvalidCommandError(
                message=f"Tilt angle {request.tilt} is outside physical actuator boundary (0-180 deg).",
                details={"tilt": request.tilt}
            )

        command_id = f"cmd-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6]}"
        command = Command(
            command_id=command_id,
            command=request.command,
            device_id=request.device_id or "esp32-sentry-01",
            pan=request.pan,
            tilt=request.tilt,
            speed=request.speed or 100,
            target_state=request.target_state,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        record = await self.repository.create_command(command)
        logger.info(f"Dispatched command {command.command_id} ({command.command.value}) to {command.device_id}")

        # Broadcast event
        await event_bus.publish(TOPIC_COMMAND_DISPATCHED, record.model_dump())
        return record

    async def poll_next_command(self, device_id: str) -> Optional[Command]:
        """Edge polling endpoint handler: fetches next pending command in queue."""
        record = await self.repository.get_next_pending(device_id)
        if record:
            return record.command
        return None

    async def record_result(self, result: CommandResult) -> CommandRecord:
        """Process execution feedback from ESP32 edge controller."""
        logger.info(f"Command execution result received for {result.command_id}: {result.status.value}")
        record = await self.repository.update_result(result)
        if not record:
            raise InvalidCommandError(
                message=f"Command with ID '{result.command_id}' not found for result update.",
                details={"command_id": result.command_id}
            )

        # Broadcast completion
        await event_bus.publish(TOPIC_COMMAND_RESULT, record.model_dump())
        return record

    async def get_command(self, command_id: str) -> Optional[CommandRecord]:
        return await self.repository.get_by_id(command_id)

    async def list_commands(
        self,
        device_id: Optional[str] = None,
        status: Optional[CommandStatus] = None,
        limit: int = 50
    ) -> List[CommandRecord]:
        return await self.repository.list_commands(device_id=device_id, status=status, limit=limit)
