"""
Solar Sentry - Telemetry Storage Model
High-throughput time-series sensor and edge state readings.
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import BigInteger, String, Integer, Float, Boolean, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.core import Base, UTCDateTime, PortableJSON


class TelemetryRecord(Base):
    """Authoritative time-series telemetry reading emitted by Solar Sentry edge nodes."""
    __tablename__ = "telemetry_records"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("devices.device_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, index=True)
    uptime_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    temperature: Mapped[float] = mapped_column(Float, nullable=False)
    humidity: Mapped[float] = mapped_column(Float, nullable=False)
    pressure: Mapped[float] = mapped_column(Float, nullable=False)
    lux: Mapped[float] = mapped_column(Float, nullable=False)
    rain_raw: Mapped[int] = mapped_column(Integer, nullable=False)
    rain_detected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pan: Mapped[int] = mapped_column(Integer, nullable=False)
    tilt: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    health: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    wifi_rssi: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    camera_online: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    camera_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    sensor_status_json: Mapped[Optional[dict]] = mapped_column(PortableJSON, nullable=True)
    firmware_version: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    device: Mapped["Device"] = relationship("Device", back_populates="telemetry_records")

    __table_args__ = (
        Index("ix_telemetry_device_timestamp", "device_id", "timestamp"),
        Index("ix_telemetry_timestamp_state", "timestamp", "state"),
        Index("ix_telemetry_rain_detected", "rain_detected"),
    )
