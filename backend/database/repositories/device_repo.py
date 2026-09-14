"""
Solar Sentry - Device & Sensor Repositories
Data access operations for edge controllers and physical sensor telemetry nodes.
"""

from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.database.models.device import Device, Sensor
from backend.database.repositories.base import BaseRepository


class DeviceRepository(BaseRepository[Device]):
    """Repository managing physical and simulated edge device records."""

    def __init__(self, session: Session):
        super().__init__(Device, session)

    def register_or_update(
        self,
        device_id: str,
        name: str,
        device_type: str = "CONTROLLER_ESP32",
        hardware_version: Optional[str] = None,
        firmware_version: Optional[str] = None,
        ip_address: Optional[str] = None,
        mac_address: Optional[str] = None,
        config_json: Optional[dict] = None,
        status: str = "ONLINE",
    ) -> Device:
        """Registers a new edge device or updates an existing device record."""
        device = self.get_by_id(device_id)
        now = datetime.now(timezone.utc)
        if device is None:
            device = Device(
                device_id=device_id,
                name=name,
                device_type=device_type,
                hardware_version=hardware_version,
                firmware_version=firmware_version,
                ip_address=ip_address,
                mac_address=mac_address,
                config_json=config_json,
                status=status,
                registered_at=now,
                last_seen_at=now,
            )
            self.create(device)
        else:
            device.name = name
            device.device_type = device_type
            if hardware_version:
                device.hardware_version = hardware_version
            if firmware_version:
                device.firmware_version = firmware_version
            if ip_address:
                device.ip_address = ip_address
            if mac_address:
                device.mac_address = mac_address
            if config_json:
                device.config_json = config_json
            device.status = status
            device.last_seen_at = now
            self.update(device)
        return device

    def update_last_seen(self, device_id: str, timestamp: Optional[datetime] = None) -> Optional[Device]:
        """Updates the last_seen_at timestamp for heartbeat and connection tracking."""
        device = self.get_by_id(device_id)
        if device:
            device.last_seen_at = timestamp or datetime.now(timezone.utc)
            self.update(device)
        return device

    def update_status(self, device_id: str, status: str) -> Optional[Device]:
        """Updates the operating status (e.g. ONLINE, OFFLINE, DEGRADED, FAULT)."""
        device = self.get_by_id(device_id)
        if device:
            device.status = status
            self.update(device)
        return device

    def get_with_sensors(self, device_id: str) -> Optional[Device]:
        """Fetches a device with its associated sensor records loaded."""
        stmt = (
            select(Device)
            .where(Device.device_id == device_id)
            .options(selectinload(Device.sensors))
        )
        return self.session.scalars(stmt).first()

    def list_by_status(self, status: str = "ONLINE") -> List[Device]:
        """Returns all devices matching a given status."""
        stmt = select(Device).where(Device.status == status).order_by(Device.registered_at.desc())
        return list(self.session.scalars(stmt).all())


class SensorRepository(BaseRepository[Sensor]):
    """Repository managing sensor attachments and calibration records."""

    def __init__(self, session: Session):
        super().__init__(Sensor, session)

    def register_or_update(
        self,
        sensor_id: str,
        device_id: str,
        sensor_type: str,
        model: Optional[str] = None,
        bus_type: str = "I2C",
        address_or_pin: Optional[str] = None,
        calibration_offset: float = 0.0,
        health_status: str = "HEALTHY",
        metadata_json: Optional[dict] = None,
    ) -> Sensor:
        """Registers or updates a sensor attachment."""
        sensor = self.get_by_id(sensor_id)
        if sensor is None:
            sensor = Sensor(
                sensor_id=sensor_id,
                device_id=device_id,
                sensor_type=sensor_type,
                model=model,
                bus_type=bus_type,
                address_or_pin=address_or_pin,
                calibration_offset=calibration_offset,
                health_status=health_status,
                metadata_json=metadata_json,
                is_active=True,
            )
            self.create(sensor)
        else:
            sensor.sensor_type = sensor_type
            sensor.model = model
            sensor.bus_type = bus_type
            sensor.address_or_pin = address_or_pin
            sensor.calibration_offset = calibration_offset
            sensor.health_status = health_status
            if metadata_json:
                sensor.metadata_json = metadata_json
            self.update(sensor)
        return sensor

    def list_by_device(self, device_id: str) -> List[Sensor]:
        """Returns all sensors registered to a given device."""
        stmt = select(Sensor).where(Sensor.device_id == device_id).order_by(Sensor.sensor_type)
        return list(self.session.scalars(stmt).all())
