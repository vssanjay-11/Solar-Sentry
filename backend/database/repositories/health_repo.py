"""
Solar Sentry - Health & Anomaly Repositories
Data access operations for subsystem diagnostic health evaluations and anomaly events.
"""

from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from backend.database.models.health import HealthRecord, AnomalyEvent
from backend.database.repositories.base import BaseRepository


class HealthRepository(BaseRepository[HealthRecord]):
    """Repository managing periodic hardware health evaluations."""

    def __init__(self, session: Session):
        super().__init__(HealthRecord, session)

    def record_health(
        self,
        health_id: str,
        device_id: str,
        overall_health_score: int,
        power_status: str = "NORMAL",
        thermal_status: str = "NORMAL",
        actuator_status: str = "OPERATIONAL",
        comms_status: str = "HEALTHY",
        sensor_health_json: Optional[dict] = None,
        degraded_reason: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ) -> HealthRecord:
        """Stores a hardware subsystem health record."""
        record = HealthRecord(
            health_id=health_id,
            device_id=device_id,
            timestamp=timestamp or datetime.now(timezone.utc),
            overall_health_score=overall_health_score,
            power_status=power_status,
            thermal_status=thermal_status,
            actuator_status=actuator_status,
            comms_status=comms_status,
            sensor_health_json=sensor_health_json,
            degraded_reason=degraded_reason,
            created_at=datetime.now(timezone.utc),
        )
        return self.create(record)

    def get_latest(self, device_id: str) -> Optional[HealthRecord]:
        """Returns the most recent health record for the device."""
        stmt = (
            select(HealthRecord)
            .where(HealthRecord.device_id == device_id)
            .order_by(HealthRecord.timestamp.desc())
            .limit(1)
        )
        return self.session.scalars(stmt).first()

    def list_history(self, device_id: str, limit: int = 50) -> List[HealthRecord]:
        """Returns historical health diagnostic records."""
        stmt = (
            select(HealthRecord)
            .where(HealthRecord.device_id == device_id)
            .order_by(HealthRecord.timestamp.desc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())


class AnomalyRepository(BaseRepository[AnomalyEvent]):
    """Repository managing sensor fusion and AI anomaly events (Agent 7)."""

    def __init__(self, session: Session):
        super().__init__(AnomalyEvent, session)

    def record_anomaly(
        self,
        anomaly_id: str,
        device_id: str,
        source_subsystem: str,
        anomaly_type: str,
        severity: str = "WARNING",
        score: float = 1.0,
        details_json: Optional[dict] = None,
        timestamp: Optional[datetime] = None,
    ) -> AnomalyEvent:
        """Records an anomaly event."""
        anomaly = AnomalyEvent(
            anomaly_id=anomaly_id,
            device_id=device_id,
            timestamp=timestamp or datetime.now(timezone.utc),
            source_subsystem=source_subsystem,
            anomaly_type=anomaly_type,
            severity=severity,
            score=score,
            details_json=details_json,
            is_resolved=False,
            created_at=datetime.now(timezone.utc),
        )
        return self.create(anomaly)

    def resolve_anomaly(
        self,
        anomaly_id: str,
        resolution_notes: Optional[str] = None,
        resolved_at: Optional[datetime] = None,
    ) -> Optional[AnomalyEvent]:
        """Marks an anomaly as resolved."""
        anomaly = self.get_by_id(anomaly_id)
        if anomaly:
            anomaly.is_resolved = True
            anomaly.resolved_at = resolved_at or datetime.now(timezone.utc)
            anomaly.resolution_notes = resolution_notes
            self.update(anomaly)
        return anomaly

    def list_unresolved(self, device_id: Optional[str] = None, limit: int = 50) -> List[AnomalyEvent]:
        """Returns unresolved anomalies, ordered by timestamp descending."""
        filters = [AnomalyEvent.is_resolved.is_(False)]
        if device_id:
            filters.append(AnomalyEvent.device_id == device_id)
        stmt = (
            select(AnomalyEvent)
            .where(and_(*filters))
            .order_by(AnomalyEvent.timestamp.desc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

    def list_by_severity(self, severity: str, limit: int = 50) -> List[AnomalyEvent]:
        """Returns anomalies filtered by severity level (INFO, WARNING, CRITICAL, EMERGENCY)."""
        stmt = (
            select(AnomalyEvent)
            .where(AnomalyEvent.severity == severity)
            .order_by(AnomalyEvent.timestamp.desc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())
