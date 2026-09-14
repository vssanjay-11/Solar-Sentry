import asyncio
import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any
from collections import deque

from app.schemas.telemetry import SensorTelemetry
from app.schemas.device import DeviceInfo, DeviceRegisterRequest, DeviceStatus, DeviceType
from app.schemas.command import Command, CommandRecord, CommandResult, CommandStatus
from app.schemas.image import ImageMetadata
from app.schemas.mission import Mission, MissionCreate, MissionStatus
from app.repositories.base import (
    DeviceRepository,
    TelemetryRepository,
    CommandRepository,
    ImageRepository,
    MissionRepository,
)


class InMemoryDeviceRepository(DeviceRepository):
    """Thread-safe in-memory device registry."""

    def __init__(self):
        self._devices: Dict[str, DeviceInfo] = {}
        self._lock = asyncio.Lock()

    async def get_by_id(self, device_id: str) -> Optional[DeviceInfo]:
        async with self._lock:
            return self._devices.get(device_id)

    async def list_all(self, limit: int = 100, offset: int = 0) -> List[DeviceInfo]:
        async with self._lock:
            devices = list(self._devices.values())
            return devices[offset : offset + limit]

    async def register_or_update(self, request: DeviceRegisterRequest) -> DeviceInfo:
        async with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            existing = self._devices.get(request.device_id)

            if existing:
                updated = existing.model_copy(update={
                    "firmware_version": request.firmware_version,
                    "hardware_revision": request.hardware_revision or existing.hardware_revision,
                    "ip_address": request.ip_address or existing.ip_address,
                    "mac_address": request.mac_address or existing.mac_address,
                    "capabilities": request.capabilities,
                    "status": DeviceStatus.ONLINE,
                    "last_seen_at": now,
                    "metadata": {**existing.metadata, **request.metadata}
                })
                self._devices[request.device_id] = updated
                return updated

            new_device = DeviceInfo(
                device_id=request.device_id,
                device_type=request.device_type,
                status=DeviceStatus.ONLINE,
                firmware_version=request.firmware_version,
                hardware_revision=request.hardware_revision,
                ip_address=request.ip_address,
                mac_address=request.mac_address,
                capabilities=request.capabilities,
                registered_at=now,
                last_seen_at=now,
                last_heartbeat_at=now,
                uptime_seconds=0,
                wifi_rssi=None,
                health_score=100,
                metadata=request.metadata
            )
            self._devices[request.device_id] = new_device
            return new_device

    async def update_heartbeat(
        self,
        device_id: str,
        uptime: int,
        rssi: Optional[int],
        health: int,
        current_state: Optional[str] = None
    ) -> Optional[DeviceInfo]:
        async with self._lock:
            device = self._devices.get(device_id)
            if not device:
                return None
            now = datetime.now(timezone.utc).isoformat()
            updated = device.model_copy(update={
                "uptime_seconds": uptime,
                "wifi_rssi": rssi if rssi is not None else device.wifi_rssi,
                "health_score": health,
                "last_seen_at": now,
                "last_heartbeat_at": now,
                "status": DeviceStatus.ONLINE
            })
            self._devices[device_id] = updated
            return updated


class InMemoryTelemetryRepository(TelemetryRepository):
    """In-memory rolling buffer repository for sensor telemetry."""

    def __init__(self, maxlen: int = 5000):
        self._history: deque[SensorTelemetry] = deque(maxlen=maxlen)
        self._by_device: Dict[str, deque[SensorTelemetry]] = {}
        self._latest_by_device: Dict[str, SensorTelemetry] = {}
        self._maxlen = maxlen
        self._lock = asyncio.Lock()

    async def record_telemetry(self, telemetry: SensorTelemetry) -> None:
        async with self._lock:
            self._history.appendleft(telemetry)
            dev_id = telemetry.device_id
            if dev_id not in self._by_device:
                self._by_device[dev_id] = deque(maxlen=self._maxlen)
            self._by_device[dev_id].appendleft(telemetry)
            self._latest_by_device[dev_id] = telemetry

    async def get_latest(self, device_id: Optional[str] = None) -> Optional[SensorTelemetry]:
        async with self._lock:
            if device_id:
                return self._latest_by_device.get(device_id)
            if self._history:
                return self._history[0]
            return None

    async def get_history(
        self,
        device_id: Optional[str] = None,
        limit: int = 100,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> List[SensorTelemetry]:
        async with self._lock:
            source = self._by_device.get(device_id, deque()) if device_id else self._history
            items = list(source)
            if start_time:
                items = [t for t in items if t.timestamp >= start_time]
            if end_time:
                items = [t for t in items if t.timestamp <= end_time]
            return items[:limit]

    async def count(self, device_id: Optional[str] = None) -> int:
        async with self._lock:
            if device_id:
                return len(self._by_device.get(device_id, []))
            return len(self._history)


class InMemoryCommandRepository(CommandRepository):
    """In-memory queue and tracker for commands."""

    def __init__(self):
        self._commands: Dict[str, CommandRecord] = {}
        self._pending_queues: Dict[str, deque[str]] = {}  # device_id -> deque of command_ids
        self._lock = asyncio.Lock()

    async def create_command(self, command: Command) -> CommandRecord:
        async with self._lock:
            dev_id = command.device_id or "esp32-sentry-01"
            record = CommandRecord(
                command=command,
                status=CommandStatus.PENDING,
                dispatched_at=datetime.now(timezone.utc).isoformat()
            )
            self._commands[command.command_id] = record

            if dev_id not in self._pending_queues:
                self._pending_queues[dev_id] = deque()
            self._pending_queues[dev_id].append(command.command_id)
            return record

    async def get_by_id(self, command_id: str) -> Optional[CommandRecord]:
        async with self._lock:
            return self._commands.get(command_id)

    async def list_commands(
        self,
        device_id: Optional[str] = None,
        status: Optional[CommandStatus] = None,
        limit: int = 50
    ) -> List[CommandRecord]:
        async with self._lock:
            records = list(self._commands.values())
            if device_id:
                records = [r for r in records if r.command.device_id == device_id]
            if status:
                records = [r for r in records if r.status == status]
            records.sort(key=lambda r: r.dispatched_at or "", reverse=True)
            return records[:limit]

    async def get_next_pending(self, device_id: str) -> Optional[CommandRecord]:
        async with self._lock:
            queue = self._pending_queues.get(device_id)
            if not queue:
                return None
            command_id = queue.popleft()
            record = self._commands.get(command_id)
            if record:
                record.status = CommandStatus.DISPATCHED
            return record

    async def update_result(self, result: CommandResult) -> Optional[CommandRecord]:
        async with self._lock:
            record = self._commands.get(result.command_id)
            if not record:
                return None
            record.status = result.status
            record.completed_at = result.timestamp or datetime.now(timezone.utc).isoformat()
            record.result = result
            return record


class InMemoryImageRepository(ImageRepository):
    """In-memory metadata repository with byte storage."""

    def __init__(self, storage_dir: str = "data/images"):
        self._images_meta: Dict[str, ImageMetadata] = {}
        self._images_data: Dict[str, bytes] = {}
        self._storage_dir = storage_dir
        self._lock = asyncio.Lock()
        os.makedirs(storage_dir, exist_ok=True)

    async def save_image(self, metadata: ImageMetadata, data: bytes) -> ImageMetadata:
        async with self._lock:
            # Also optionally write to disk if path is configured
            filename = f"{metadata.image_id}.jpg"
            disk_path = os.path.join(self._storage_dir, filename)
            try:
                with open(disk_path, "wb") as f:
                    f.write(data)
                metadata.file_path = disk_path
            except Exception:
                metadata.file_path = None

            self._images_meta[metadata.image_id] = metadata
            self._images_data[metadata.image_id] = data
            return metadata

    async def get_metadata(self, image_id: str) -> Optional[ImageMetadata]:
        async with self._lock:
            return self._images_meta.get(image_id)

    async def get_data(self, image_id: str) -> Optional[Tuple[ImageMetadata, bytes]]:
        async with self._lock:
            meta = self._images_meta.get(image_id)
            if not meta:
                return None
            data = self._images_data.get(image_id)
            if data is None and meta.file_path and os.path.exists(meta.file_path):
                with open(meta.file_path, "rb") as f:
                    data = f.read()
            if data is None:
                return None
            return meta, data

    async def list_images(self, device_id: Optional[str] = None, limit: int = 50) -> List[ImageMetadata]:
        async with self._lock:
            images = list(self._images_meta.values())
            if device_id:
                images = [img for img in images if img.device_id == device_id]
            images.sort(key=lambda x: x.timestamp, reverse=True)
            return images[:limit]

    async def update_analysis(self, image_id: str, analysis: Dict[str, Any]) -> Optional[ImageMetadata]:
        async with self._lock:
            meta = self._images_meta.get(image_id)
            if not meta:
                return None
            meta.analysis = analysis
            return meta


class InMemoryMissionRepository(MissionRepository):
    """In-memory mission repository."""

    def __init__(self):
        self._missions: Dict[str, Mission] = {}
        self._lock = asyncio.Lock()

    async def create_mission(self, request: MissionCreate) -> Mission:
        async with self._lock:
            mission_id = f"msn-{uuid.uuid4().hex[:8]}"
            now = datetime.now(timezone.utc).isoformat()
            mission = Mission(
                mission_id=mission_id,
                title=request.title,
                mission_type=request.mission_type,
                status=MissionStatus.PENDING,
                priority=request.priority,
                target_pan=request.target_pan,
                target_tilt=request.target_tilt,
                duration_seconds=request.duration_seconds,
                parameters=request.parameters,
                created_at=now
            )
            self._missions[mission_id] = mission
            return mission

    async def get_by_id(self, mission_id: str) -> Optional[Mission]:
        async with self._lock:
            return self._missions.get(mission_id)

    async def list_missions(self, limit: int = 50) -> List[Mission]:
        async with self._lock:
            missions = list(self._missions.values())
            missions.sort(key=lambda m: m.created_at, reverse=True)
            return missions[:limit]

    async def update_status(
        self,
        mission_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None
    ) -> Optional[Mission]:
        async with self._lock:
            mission = self._missions.get(mission_id)
            if not mission:
                return None
            now = datetime.now(timezone.utc).isoformat()
            updates: Dict[str, Any] = {"status": status}
            if status == MissionStatus.ACTIVE and not mission.started_at:
                updates["started_at"] = now
            elif status in [MissionStatus.COMPLETED, MissionStatus.ABORTED, MissionStatus.FAILED]:
                updates["completed_at"] = now
            if result is not None:
                updates["result"] = result
            updated = mission.model_copy(update=updates)
            self._missions[mission_id] = updated
            return updated
