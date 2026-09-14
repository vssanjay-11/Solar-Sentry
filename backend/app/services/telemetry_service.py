from datetime import datetime, timezone
from typing import List, Optional

from app.schemas.telemetry import (
    SensorTelemetry,
    TelemetryIngestResponse,
    TelemetryQueryResponse,
)
from app.repositories.base import TelemetryRepository
from app.services.observatory_service import observatory_service
from app.core.event_bus import event_bus, TOPIC_TELEMETRY
from app.core.logging import logger


class TelemetryService:
    """Orchestrates telemetry ingestion, validation, and real-time distribution."""

    def __init__(self, repository: TelemetryRepository):
        self.repository = repository

    async def ingest_telemetry(self, telemetry: SensorTelemetry) -> TelemetryIngestResponse:
        alerts: List[str] = []

        # Validate environmental sanity boundaries
        if telemetry.rain_detected or telemetry.rain_raw < 2000:
            alerts.append("RAIN_DETECTED: Stowing actuators to safe orientation.")

        if telemetry.temperature > 55.0:
            alerts.append(f"HIGH_TEMPERATURE_WARNING: Controller ambient temperature is {telemetry.temperature:.1f}C.")
        elif telemetry.temperature < -10.0:
            alerts.append(f"LOW_TEMPERATURE_WARNING: Sub-zero ambient temperature {telemetry.temperature:.1f}C.")

        if telemetry.health < 70:
            alerts.append(f"DEGRADED_HEALTH_WARNING: Edge health score is {telemetry.health}/100.")

        # Save to repository
        await self.repository.record_telemetry(telemetry)

        # Update authoritative observatory cognitive state
        await observatory_service.update_from_telemetry(telemetry)

        # Broadcast via internal event bus to WebSockets and AI modules
        await event_bus.publish(TOPIC_TELEMETRY, telemetry.model_dump())

        return TelemetryIngestResponse(
            status="received",
            device_id=telemetry.device_id,
            timestamp=telemetry.timestamp,
            rain_detected=bool(telemetry.rain_detected),
            state=telemetry.state,
            health=telemetry.health,
            alerts=alerts
        )

    async def get_latest(self, device_id: Optional[str] = None) -> Optional[SensorTelemetry]:
        return await self.repository.get_latest(device_id)

    async def get_history(
        self,
        device_id: Optional[str] = None,
        limit: int = 100,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> TelemetryQueryResponse:
        items = await self.repository.get_history(
            device_id=device_id,
            limit=limit,
            start_time=start_time,
            end_time=end_time
        )
        total = await self.repository.count(device_id)
        return TelemetryQueryResponse(total=total, items=items)
