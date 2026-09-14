from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Optional, Any
from pydantic import BaseModel, Field, field_validator


class DeviceState(str, Enum):
    BOOT = "BOOT"
    SELF_CHECK = "SELF_CHECK"
    STANDBY = "STANDBY"
    OBSERVE = "OBSERVE"
    WAIT = "WAIT"
    SCAN = "SCAN"
    SUSPEND = "SUSPEND"
    FAULT = "FAULT"
    SAFE = "SAFE"
    DEGRADED = "DEGRADED"


class SensorStatus(BaseModel):
    dht22: bool = True
    bh1750: bool = True
    bmp280: bool = True
    rain: bool = True


class SensorTelemetry(BaseModel):
    """Telemetry payload matching docs/contracts/SensorTelemetry.json."""

    device_id: str = Field(..., description="Unique identifier of the edge controller", example="esp32-sentry-01")
    timestamp: str = Field(..., description="ISO-8601 UTC timestamp or epoch timestamp string", example="2026-09-13T11:20:00Z")
    uptime_seconds: Optional[int] = Field(default=0, ge=0, description="Uptime of the ESP32 in seconds")
    temperature: float = Field(..., description="Ambient temperature in Celsius")
    humidity: float = Field(..., ge=0.0, le=100.0, description="Relative humidity percentage")
    pressure: float = Field(..., description="Barometric atmospheric pressure in hPa")
    lux: float = Field(..., ge=0.0, le=65535.0, description="Ambient illuminance in Lux")
    rain_raw: int = Field(..., ge=0, le=4095, description="Raw 12-bit ADC reading from Rain sensor")
    rain_detected: Optional[bool] = Field(default=False, description="Flag indicating if rain threshold is exceeded")
    pan: int = Field(..., ge=0, le=180, description="Current pan servo angle in degrees")
    tilt: int = Field(..., ge=0, le=180, description="Current tilt servo angle in degrees")
    state: DeviceState = Field(..., description="Current system state of the edge controller")
    health: int = Field(..., ge=0, le=100, description="Device health score (0-100)")
    wifi_rssi: Optional[int] = Field(default=None, description="Wi-Fi signal strength in dBm")
    camera_online: Optional[bool] = Field(default=None, description="Status of the companion camera node")
    camera_ip: Optional[str] = Field(default=None, description="IP address of the companion camera node")
    sensor_status: Optional[SensorStatus] = Field(default=None, description="Individual sensor health flags")
    firmware_version: str = Field(..., description="Firmware version string", example="1.0.0")

    @field_validator("timestamp", mode="before")
    @classmethod
    def validate_timestamp(cls, v: Any) -> str:
        if isinstance(v, datetime):
            return v.astimezone(timezone.utc).isoformat()
        if isinstance(v, (int, float)):
            return datetime.fromtimestamp(v, tz=timezone.utc).isoformat()
        if isinstance(v, str):
            return v
        return datetime.now(timezone.utc).isoformat()


class TelemetryIngestResponse(BaseModel):
    status: str = "received"
    device_id: str
    timestamp: str
    rain_detected: bool
    state: DeviceState
    health: int
    alerts: list[str] = []


class TelemetryQueryResponse(BaseModel):
    total: int
    items: list[SensorTelemetry]
