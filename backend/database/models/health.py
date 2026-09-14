"""
Solar Sentry - Health Records & Anomaly Events Models
Subsystem health diagnostics and AI sensor fusion anomaly detection events.
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Integer, Float, Boolean, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.core import Base, UTCDateTime, PortableJSON


class HealthRecord(Base):
    """Authoritative periodic diagnostic health evaluation of edge hardware subsystems."""
    __tablename__ = "health_records"

    health_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    device_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("devices.device_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, index=True)
    overall_health_score: Mapped[int] = mapped_column(Integer, nullable=False, default=100)  # 0 - 100
    power_status: Mapped[str] = mapped_column(String(32), nullable=False, default="NORMAL")
    thermal_status: Mapped[str] = mapped_column(String(32), nullable=False, default="NORMAL")
    actuator_status: Mapped[str] = mapped_column(String(32), nullable=False, default="OPERATIONAL")
    comms_status: Mapped[str] = mapped_column(String(32), nullable=False, default="HEALTHY")
    sensor_health_json: Mapped[Optional[dict]] = mapped_column(PortableJSON, nullable=True)
    degraded_reason: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    device: Mapped["Device"] = relationship("Device", back_populates="health_records")

    __table_args__ = (
        Index("ix_health_device_timestamp", "device_id", "timestamp"),
        Index("ix_health_score", "overall_health_score"),
    )


class AnomalyEvent(Base):
    """Authoritative anomaly detection event triggered by statistical or AI models (Agent 7)."""
    __tablename__ = "anomaly_events"

    anomaly_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    device_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("devices.device_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, index=True)
    source_subsystem: Mapped[str] = mapped_column(String(32), nullable=False)  # SENSOR, ACTUATOR, OPTICAL, COMMS, ENVIRONMENT
    anomaly_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # SENSOR_SPIKE, VALUE_DISAGREEMENT, etc.
    severity: Mapped[str] = mapped_column(String(32), nullable=False, default="WARNING")  # INFO, WARNING, CRITICAL, EMERGENCY
    score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)  # Isolation Forest anomaly score
    details_json: Mapped[Optional[dict]] = mapped_column(PortableJSON, nullable=True)
    is_resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, nullable=True)
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    device: Mapped["Device"] = relationship("Device", back_populates="anomaly_events")

    __table_args__ = (
        Index("ix_anomaly_device_timestamp", "device_id", "timestamp"),
        Index("ix_anomaly_severity_score", "severity", "score"),
    )
