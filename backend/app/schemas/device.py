from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class DeviceType(str, Enum):
    ESP32_CONTROLLER = "ESP32_CONTROLLER"
    ESP32_CAM = "ESP32_CAM"
    SIMULATOR = "SIMULATOR"
    VIRTUAL_NODE = "VIRTUAL_NODE"


class DeviceStatus(str, Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    DEGRADED = "DEGRADED"
    UNREGISTERED = "UNREGISTERED"


class DeviceRegisterRequest(BaseModel):
    device_id: str = Field(..., description="Unique device identifier", example="esp32-sentry-01")
    device_type: DeviceType = Field(default=DeviceType.ESP32_CONTROLLER, description="Hardware class")
    firmware_version: str = Field(..., description="Firmware version string", example="1.0.0")
    hardware_revision: Optional[str] = Field(default="rev1", description="Hardware board revision")
    ip_address: Optional[str] = Field(default=None, description="Local or assigned IP address")
    mac_address: Optional[str] = Field(default=None, description="Device MAC address")
    capabilities: List[str] = Field(
        default=["sensors", "servos", "leds"],
        description="Supported subsystem capabilities"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional custom metadata")


class DeviceHeartbeatRequest(BaseModel):
    uptime_seconds: int = Field(default=0, ge=0)
    wifi_rssi: Optional[int] = Field(default=None)
    ip_address: Optional[str] = Field(default=None)
    health: Optional[int] = Field(default=100, ge=0, le=100)
    current_state: Optional[str] = Field(default=None)


class DeviceHeartbeatResponse(BaseModel):
    status: str = "acknowledged"
    device_id: str
    server_time: str
    pending_commands_count: int = 0


class DeviceInfo(BaseModel):
    device_id: str
    device_type: DeviceType
    status: DeviceStatus
    firmware_version: str
    hardware_revision: Optional[str] = None
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None
    capabilities: List[str] = []
    registered_at: str
    last_seen_at: Optional[str] = None
    last_heartbeat_at: Optional[str] = None
    uptime_seconds: int = 0
    wifi_rssi: Optional[int] = None
    health_score: int = 100
    metadata: Dict[str, Any] = {}
