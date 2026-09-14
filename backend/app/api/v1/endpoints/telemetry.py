from typing import Optional
from fastapi import APIRouter, Depends, Query, status

from app.schemas.telemetry import (
    SensorTelemetry,
    TelemetryIngestResponse,
    TelemetryQueryResponse,
)
from app.services.telemetry_service import TelemetryService
from app.api.deps import get_telemetry_service
from app.core.exceptions import SolarSentryException

router = APIRouter(prefix="/telemetry", tags=["Sensor Telemetry"])


@router.post(
    "",
    response_model=TelemetryIngestResponse,
    status_code=status.HTTP_200_OK,
    summary="Ingest edge sensor telemetry frame"
)
async def ingest_telemetry(
    telemetry: SensorTelemetry,
    service: TelemetryService = Depends(get_telemetry_service)
) -> TelemetryIngestResponse:
    """Ingests multi-modal sensor telemetry payload matching docs/contracts/SensorTelemetry.json.
    
    Triggers safety evaluation, cognitive state update, and real-time WebSocket distribution.
    """
    return await service.ingest_telemetry(telemetry)


@router.get(
    "/latest",
    response_model=Optional[SensorTelemetry],
    summary="Get latest received telemetry reading"
)
async def get_latest_telemetry(
    device_id: Optional[str] = Query(default=None, description="Optional target device filter"),
    service: TelemetryService = Depends(get_telemetry_service)
) -> Optional[SensorTelemetry]:
    """Retrieve the most recent environmental and actuator state reading."""
    result = await service.get_latest(device_id)
    if not result:
        from app.core.providers import provider_manager
        return await provider_manager.sensor_provider.get_telemetry()
    return result


@router.get(
    "/live",
    response_model=SensorTelemetry,
    summary="Get real-time live telemetry snapshot from active provider"
)
async def get_live_telemetry() -> SensorTelemetry:
    """Returns live telemetry adhering strictly to SensorTelemetry.json from active provider."""
    from app.core.providers import provider_manager
    return await provider_manager.sensor_provider.get_telemetry()


@router.get(
    "/history",
    response_model=TelemetryQueryResponse,
    summary="Query historical telemetry frames"
)
async def get_telemetry_history(
    device_id: Optional[str] = Query(default=None, description="Optional device filter"),
    limit: int = Query(default=100, ge=1, le=1000, description="Max frames to return"),
    start_time: Optional[str] = Query(default=None, description="ISO-8601 start window filter"),
    end_time: Optional[str] = Query(default=None, description="ISO-8601 end window filter"),
    service: TelemetryService = Depends(get_telemetry_service)
) -> TelemetryQueryResponse:
    """Retrieve historical rolling telemetry records."""
    return await service.get_history(
        device_id=device_id,
        limit=limit,
        start_time=start_time,
        end_time=end_time
    )
