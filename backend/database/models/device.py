"""
Solar Sentry - Device & Sensor Models
Authoritative records for edge controllers, camera nodes, and physical sensors.
"""

from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import String, Boolean, Float, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.core import Base, UTCDateTime, PortableJSON


class Device(Base):
    """Authoritative physical or simulated edge device record."""
    __tablename__ = "devices"

    device_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    device_type: Mapped[str] = mapped_column(String(32), nullable=False, default="CONTROLLER_ESP32")
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    hardware_version: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    firmware_version: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    mac_address: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ONLINE")
    registered_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(
        UTCDateTime,
        nullable=True,
        index=True,
    )
    config_json: Mapped[Optional[dict]] = mapped_column(PortableJSON, nullable=True)

    # Relationships
    sensors: Mapped[List["Sensor"]] = relationship("Sensor", back_populates="device", cascade="all, delete-orphan")
    telemetry_records: Mapped[List["TelemetryRecord"]] = relationship(
        "TelemetryRecord", back_populates="device", cascade="all, delete-orphan"
    )
    images: Mapped[List["ImageMetadata"]] = relationship("ImageMetadata", back_populates="device")
    observations: Mapped[List["Observation"]] = relationship("Observation", back_populates="device")
    health_records: Mapped[List["HealthRecord"]] = relationship("HealthRecord", back_populates="device")
    anomaly_events: Mapped[List["AnomalyEvent"]] = relationship("AnomalyEvent", back_populates="device")
    decisions: Mapped[List["DecisionRecord"]] = relationship("DecisionRecord", back_populates="device")
    predictions: Mapped[List["EnvironmentPrediction"]] = relationship("EnvironmentPrediction", back_populates="device")
    commands: Mapped[List["CommandRecord"]] = relationship("CommandRecord", back_populates="device")

    __table_args__ = (
        Index("ix_devices_status", "status"),
        Index("ix_devices_type", "device_type"),
    )


class Sensor(Base):
    """Authoritative physical or virtual sensor attached to an edge device."""
    __tablename__ = "sensors"

    sensor_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    device_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("devices.device_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sensor_type: Mapped[str] = mapped_column(String(32), nullable=False)  # DHT22, BMP280, BH1750, RAIN, CAM
    model: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    bus_type: Mapped[str] = mapped_column(String(32), nullable=False, default="I2C")  # I2C, GPIO, ADC, NETWORK
    address_or_pin: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    calibration_offset: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    health_status: Mapped[str] = mapped_column(String(32), nullable=False, default="HEALTHY")
    metadata_json: Mapped[Optional[dict]] = mapped_column(PortableJSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    device: Mapped["Device"] = relationship("Device", back_populates="sensors")

    __table_args__ = (
        Index("ix_sensors_device_type", "device_id", "sensor_type"),
    )
