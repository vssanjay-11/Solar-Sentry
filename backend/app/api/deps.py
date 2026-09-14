from typing import Generator
from fastapi import Depends

from app.repositories.base import (
    DeviceRepository,
    TelemetryRepository,
    CommandRepository,
    ImageRepository,
    MissionRepository,
)
from app.repositories.memory import (
    InMemoryDeviceRepository,
    InMemoryTelemetryRepository,
    InMemoryCommandRepository,
    InMemoryImageRepository,
    InMemoryMissionRepository,
)
from app.services.device_service import DeviceService
from app.services.telemetry_service import TelemetryService
from app.services.command_service import CommandService
from app.services.image_service import ImageService
from app.services.ai_integration import AIIntegrationService
from app.services.observatory_service import observatory_service, ObservatoryService
from app.config import settings

# Global repository singletons (In-memory references ready for Agent 3 DB replacement)
_device_repo = InMemoryDeviceRepository()
_telemetry_repo = InMemoryTelemetryRepository()
_command_repo = InMemoryCommandRepository()
_image_repo = InMemoryImageRepository(storage_dir=settings.IMAGE_STORAGE_PATH)
_mission_repo = InMemoryMissionRepository()

# Service singletons
_device_service = DeviceService(_device_repo, _command_repo)
_telemetry_service = TelemetryService(_telemetry_repo)
_command_service = CommandService(_command_repo)
_image_service = ImageService(_image_repo)
_ai_integration_service = AIIntegrationService(_image_repo)


def get_device_repository() -> DeviceRepository:
    return _device_repo


def get_telemetry_repository() -> TelemetryRepository:
    return _telemetry_repo


def get_command_repository() -> CommandRepository:
    return _command_repo


def get_image_repository() -> ImageRepository:
    return _image_repo


def get_mission_repository() -> MissionRepository:
    return _mission_repo


def get_device_service() -> DeviceService:
    return _device_service


def get_telemetry_service() -> TelemetryService:
    return _telemetry_service


def get_command_service() -> CommandService:
    return _command_service


def get_image_service() -> ImageService:
    return _image_service


def get_ai_service() -> AIIntegrationService:
    return _ai_integration_service


def get_observatory_service() -> ObservatoryService:
    return observatory_service
