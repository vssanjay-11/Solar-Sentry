from abc import ABC, abstractmethod
from typing import List, Optional, Tuple, Dict, Any

from app.schemas.telemetry import SensorTelemetry
from app.schemas.device import DeviceInfo, DeviceRegisterRequest
from app.schemas.command import Command, CommandRecord, CommandResult, CommandStatus
from app.schemas.image import ImageMetadata
from app.schemas.mission import Mission, MissionCreate


class DeviceRepository(ABC):
    """Abstract storage interface for Device management (Agent 3 hand-off contract)."""

    @abstractmethod
    async def get_by_id(self, device_id: str) -> Optional[DeviceInfo]:
        pass

    @abstractmethod
    async def list_all(self, limit: int = 100, offset: int = 0) -> List[DeviceInfo]:
        pass

    @abstractmethod
    async def register_or_update(self, request: DeviceRegisterRequest) -> DeviceInfo:
        pass

    @abstractmethod
    async def update_heartbeat(
        self,
        device_id: str,
        uptime: int,
        rssi: Optional[int],
        health: int,
        current_state: Optional[str] = None
    ) -> Optional[DeviceInfo]:
        pass


class TelemetryRepository(ABC):
    """Abstract storage interface for Sensor Telemetry (Agent 3 hand-off contract)."""

    @abstractmethod
    async def record_telemetry(self, telemetry: SensorTelemetry) -> None:
        pass

    @abstractmethod
    async def get_latest(self, device_id: Optional[str] = None) -> Optional[SensorTelemetry]:
        pass

    @abstractmethod
    async def get_history(
        self,
        device_id: Optional[str] = None,
        limit: int = 100,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> List[SensorTelemetry]:
        pass

    @abstractmethod
    async def count(self, device_id: Optional[str] = None) -> int:
        pass


class CommandRepository(ABC):
    """Abstract storage interface for Edge Commands (Agent 3 hand-off contract)."""

    @abstractmethod
    async def create_command(self, command: Command) -> CommandRecord:
        pass

    @abstractmethod
    async def get_by_id(self, command_id: str) -> Optional[CommandRecord]:
        pass

    @abstractmethod
    async def list_commands(
        self,
        device_id: Optional[str] = None,
        status: Optional[CommandStatus] = None,
        limit: int = 50
    ) -> List[CommandRecord]:
        pass

    @abstractmethod
    async def get_next_pending(self, device_id: str) -> Optional[CommandRecord]:
        pass

    @abstractmethod
    async def update_result(self, result: CommandResult) -> Optional[CommandRecord]:
        pass


class ImageRepository(ABC):
    """Abstract storage interface for Image Metadata & Binary storage."""

    @abstractmethod
    async def save_image(self, metadata: ImageMetadata, data: bytes) -> ImageMetadata:
        pass

    @abstractmethod
    async def get_metadata(self, image_id: str) -> Optional[ImageMetadata]:
        pass

    @abstractmethod
    async def get_data(self, image_id: str) -> Optional[Tuple[ImageMetadata, bytes]]:
        pass

    @abstractmethod
    async def list_images(self, device_id: Optional[str] = None, limit: int = 50) -> List[ImageMetadata]:
        pass

    @abstractmethod
    async def update_analysis(self, image_id: str, analysis: Dict[str, Any]) -> Optional[ImageMetadata]:
        pass


class MissionRepository(ABC):
    """Abstract storage interface for Autonomous Missions (Agent 9 integration)."""

    @abstractmethod
    async def create_mission(self, request: MissionCreate) -> Mission:
        pass

    @abstractmethod
    async def get_by_id(self, mission_id: str) -> Optional[Mission]:
        pass

    @abstractmethod
    async def list_missions(self, limit: int = 50) -> List[Mission]:
        pass

    @abstractmethod
    async def update_status(
        self,
        mission_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None
    ) -> Optional[Mission]:
        pass
