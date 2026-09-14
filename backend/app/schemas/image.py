from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class CameraType(str, Enum):
    ESP32_CAM = "ESP32_CAM"
    SIMULATOR = "SIMULATOR"
    CALIBRATION = "CALIBRATION"
    EXTERNAL = "EXTERNAL"


class ImageMetadata(BaseModel):
    image_id: str = Field(..., description="Unique image identifier")
    device_id: str = Field(..., description="Source camera or edge device ID")
    camera_type: CameraType = Field(default=CameraType.ESP32_CAM)
    timestamp: str = Field(..., description="Capture timestamp")
    pan: Optional[int] = Field(default=None, ge=0, le=180, description="Pan angle at capture")
    tilt: Optional[int] = Field(default=None, ge=0, le=180, description="Tilt angle at capture")
    lux: Optional[float] = Field(default=None, description="Ambient illuminance at capture")
    content_type: str = Field(default="image/jpeg", description="MIME content type")
    file_size_bytes: int = Field(default=0, ge=0)
    file_path: Optional[str] = Field(default=None, description="Internal storage path")
    analysis: Optional[Dict[str, Any]] = Field(default=None, description="AI vision analysis from Agent 5")


class ImageUploadResponse(BaseModel):
    image_id: str
    device_id: str
    status: str = "stored"
    timestamp: str
    file_size_bytes: int
    url: str
