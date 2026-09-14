from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status, HTTPException

from app.schemas.command import (
    Command,
    CommandCreate,
    CommandRecord,
    CommandResult,
    CommandStatus,
)
from app.services.command_service import CommandService
from app.api.deps import get_command_service
from app.core.security import verify_api_key

router = APIRouter(tags=["Actuator & Observatory Commands"])


@router.post(
    "/commands",
    response_model=CommandRecord,
    status_code=status.HTTP_201_CREATED,
    summary="Dispatch new physical actuator or state command"
)
async def dispatch_command(
    request: CommandCreate,
    service: CommandService = Depends(get_command_service),
    _auth: str = Depends(verify_api_key)
) -> CommandRecord:
    """Dispatches a command conforming to docs/contracts/Command.json.
    
    Performs safety interlock evaluation (e.g. rain detection lock) before queueing.
    """
    return await service.dispatch_command(request)


@router.get(
    "/commands",
    response_model=List[CommandRecord],
    summary="List dispatched commands"
)
async def list_commands(
    device_id: Optional[str] = Query(default=None),
    status: Optional[CommandStatus] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    service: CommandService = Depends(get_command_service)
) -> List[CommandRecord]:
    return await service.list_commands(device_id=device_id, status=status, limit=limit)


@router.get(
    "/commands/{command_id}",
    response_model=CommandRecord,
    summary="Get status of specific command"
)
async def get_command(
    command_id: str,
    service: CommandService = Depends(get_command_service)
) -> CommandRecord:
    record = await service.get_command(command_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Command '{command_id}' not found."
        )
    return record


# --- Edge Controller Ingestion Endpoints (Agent 1 firmware contract) ---

@router.get(
    "/device/command/poll",
    response_model=Optional[Command],
    summary="Edge device command polling endpoint"
)
async def poll_device_command(
    device_id: str = Query(default="esp32-sentry-01", description="Device ID polling for commands"),
    service: CommandService = Depends(get_command_service)
) -> Optional[Command]:
    """Polled periodically by ESP32 edge controller matching COMMAND_POLL_ENDPOINT config."""
    return await service.poll_next_command(device_id)


@router.post(
    "/device/command/result",
    response_model=CommandRecord,
    status_code=status.HTTP_200_OK,
    summary="Edge device command execution feedback"
)
async def record_command_result(
    result: CommandResult,
    service: CommandService = Depends(get_command_service)
) -> CommandRecord:
    """Ingests execution confirmation matching docs/contracts/CommandResult.json."""
    return await service.record_result(result)


@router.post(
    "/device/command",
    response_model=CommandResult,
    status_code=status.HTTP_200_OK,
    summary="Dispatch direct actuator command adhering to Command.json -> CommandResult.json"
)
async def dispatch_device_command(cmd: Command) -> CommandResult:
    """Dispatches command to active actuator provider (simulated or live hardware)."""
    from app.core.providers import provider_manager
    return await provider_manager.actuator_provider.execute_command(cmd)
