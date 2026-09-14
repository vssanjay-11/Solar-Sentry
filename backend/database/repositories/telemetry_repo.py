"""
Solar Sentry - Telemetry Repository
High-throughput time-series storage and historical querying.
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from backend.database.models.telemetry import TelemetryRecord
from backend.database.repositories.base import BaseRepository


class TelemetryRepository(BaseRepository[TelemetryRecord]):
    """Repository managing time-series sensor telemetry readings."""

    def __init__(self, session: Session):
        super().__init__(TelemetryRecord, session)

    def record_telemetry(
        self,
        device_id: str,
        timestamp: datetime | str,
        temperature: float,
        humidity: float,
        pressure: float,
        lux: float,
        rain_raw: int,
        pan: int,
        tilt: int,
        state: str,
        health: int = 100,
        uptime_seconds: int = 0,
        rain_detected: bool = False,
        wifi_rssi: Optional[int] = None,
        camera_online: bool = False,
        camera_ip: Optional[str] = None,
        sensor_status_json: Optional[dict] = None,
        firmware_version: Optional[str] = None,
    ) -> TelemetryRecord:
        """Stores a single telemetry record adhering to the SensorTelemetry contract."""
        if isinstance(timestamp, str):
            # Parse ISO-8601 string
            parsed_dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        else:
            parsed_dt = timestamp

        record = TelemetryRecord(
            device_id=device_id,
            timestamp=parsed_dt,
            uptime_seconds=uptime_seconds,
            temperature=float(temperature),
            humidity=float(humidity),
            pressure=float(pressure),
            lux=float(lux),
            rain_raw=int(rain_raw),
            rain_detected=rain_detected,
            pan=int(pan),
            tilt=int(tilt),
            state=state,
            health=int(health),
            wifi_rssi=wifi_rssi,
            camera_online=camera_online,
            camera_ip=camera_ip,
            sensor_status_json=sensor_status_json,
            firmware_version=firmware_version,
            ingested_at=datetime.now(timezone.utc),
        )
        return self.create(record)

    def record_batch(self, records: List[Dict[str, Any]]) -> int:
        """Efficiently inserts multiple telemetry records in a single batch operation."""
        instances = []
        now = datetime.now(timezone.utc)
        for r in records:
            ts = r["timestamp"]
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            instances.append(
                TelemetryRecord(
                    device_id=r["device_id"],
                    timestamp=ts,
                    uptime_seconds=r.get("uptime_seconds", 0),
                    temperature=float(r["temperature"]),
                    humidity=float(r["humidity"]),
                    pressure=float(r["pressure"]),
                    lux=float(r["lux"]),
                    rain_raw=int(r["rain_raw"]),
                    rain_detected=r.get("rain_detected", False),
                    pan=int(r["pan"]),
                    tilt=int(r["tilt"]),
                    state=r["state"],
                    health=int(r.get("health", 100)),
                    wifi_rssi=r.get("wifi_rssi"),
                    camera_online=r.get("camera_online", False),
                    camera_ip=r.get("camera_ip"),
                    sensor_status_json=r.get("sensor_status_json"),
                    firmware_version=r.get("firmware_version"),
                    ingested_at=now,
                )
            )
        self.session.add_all(instances)
        self.session.flush()
        return len(instances)

    def get_latest(self, device_id: str) -> Optional[TelemetryRecord]:
        """Returns the most recent telemetry record for the specified device."""
        stmt = (
            select(TelemetryRecord)
            .where(TelemetryRecord.device_id == device_id)
            .order_by(TelemetryRecord.timestamp.desc())
            .limit(1)
        )
        return self.session.scalars(stmt).first()

    def get_range(
        self,
        device_id: str,
        start_time: datetime,
        end_time: datetime,
        limit: int = 1000,
        order_asc: bool = True,
    ) -> List[TelemetryRecord]:
        """Returns time-series telemetry records within [start_time, end_time]."""
        order_clause = (
            TelemetryRecord.timestamp.asc() if order_asc else TelemetryRecord.timestamp.desc()
        )
        stmt = (
            select(TelemetryRecord)
            .where(
                and_(
                    TelemetryRecord.device_id == device_id,
                    TelemetryRecord.timestamp >= start_time,
                    TelemetryRecord.timestamp <= end_time,
                )
            )
            .order_by(order_clause)
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

    def get_by_state(self, device_id: str, state: str, limit: int = 100) -> List[TelemetryRecord]:
        """Returns telemetry records matching an edge state (e.g. OBSERVE, SUSPEND, SAFE)."""
        stmt = (
            select(TelemetryRecord)
            .where(
                and_(
                    TelemetryRecord.device_id == device_id,
                    TelemetryRecord.state == state,
                )
            )
            .order_by(TelemetryRecord.timestamp.desc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

    def get_rain_events(self, device_id: str, limit: int = 50) -> List[TelemetryRecord]:
        """Returns telemetry entries where rain was detected."""
        stmt = (
            select(TelemetryRecord)
            .where(
                and_(
                    TelemetryRecord.device_id == device_id,
                    TelemetryRecord.rain_detected.is_(True),
                )
            )
            .order_by(TelemetryRecord.timestamp.desc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

    def get_aggregate_summary(
        self,
        device_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> Dict[str, Any]:
        """Calculates min, max, and avg values over a time-series window."""
        stmt = select(
            func.count(TelemetryRecord.id).label("sample_count"),
            func.avg(TelemetryRecord.temperature).label("avg_temp"),
            func.min(TelemetryRecord.temperature).label("min_temp"),
            func.max(TelemetryRecord.temperature).label("max_temp"),
            func.avg(TelemetryRecord.humidity).label("avg_humidity"),
            func.min(TelemetryRecord.humidity).label("min_humidity"),
            func.max(TelemetryRecord.humidity).label("max_humidity"),
            func.avg(TelemetryRecord.pressure).label("avg_pressure"),
            func.avg(TelemetryRecord.lux).label("avg_lux"),
            func.max(TelemetryRecord.lux).label("max_lux"),
        ).where(
            and_(
                TelemetryRecord.device_id == device_id,
                TelemetryRecord.timestamp >= start_time,
                TelemetryRecord.timestamp <= end_time,
            )
        )
        row = self.session.execute(stmt).first()
        if not row or row.sample_count == 0:
            return {"sample_count": 0}
        return {
            "sample_count": row.sample_count,
            "avg_temp": round(row.avg_temp, 2) if row.avg_temp else None,
            "min_temp": row.min_temp,
            "max_temp": row.max_temp,
            "avg_humidity": round(row.avg_humidity, 2) if row.avg_humidity else None,
            "min_humidity": row.min_humidity,
            "max_humidity": row.max_humidity,
            "avg_pressure": round(row.avg_pressure, 2) if row.avg_pressure else None,
            "avg_lux": round(row.avg_lux, 2) if row.avg_lux else None,
            "max_lux": row.max_lux,
        }
