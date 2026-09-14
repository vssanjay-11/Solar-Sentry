"""
Solar Sentry — Hardware Abstraction Layer & Providers
Implements unified SensorProvider, CameraProvider, and ActuatorProvider hierarchy.
Supports dynamic, non-destructive switching between DEMO (Simulation) and LIVE HARDWARE modes.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
import io
import time
from typing import Any, Dict, List, Optional, Tuple

import cv2
import httpx
import numpy as np

from ai.vision.pipeline import generate_synthetic_solar_image
from app.config import settings
from app.core.logging import logger
from app.schemas.command import Command, CommandResult, CommandStatus
from app.schemas.telemetry import DeviceState, SensorTelemetry
from simulation.engine import ObservatorySimulator
from simulation.scenarios import ScenarioType, get_scenario


class SystemMode(str, Enum):
    DEMO = "DEMO"
    HARDWARE = "HARDWARE"


# =============================================================================
# SENSOR PROVIDERS
# =============================================================================

class SensorProvider(ABC):
    """Abstract interface for observatory telemetry and environment sensing."""

    @abstractmethod
    async def get_telemetry(self) -> SensorTelemetry:
        """Fetch latest telemetry snapshot."""
        pass

    @abstractmethod
    async def is_connected(self) -> bool:
        """Check if telemetry source is online and healthy."""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Provider descriptive identification."""
        pass


class DemoSensorProvider(SensorProvider):
    """Simulation-backed sensor provider running 10 autonomous weather and seeing scenarios."""

    def __init__(self):
        self.simulator = ObservatorySimulator()
        self._last_telemetry: Optional[SensorTelemetry] = None
        self._step_lock = asyncio.Lock()

    async def get_telemetry(self) -> SensorTelemetry:
        async with self._step_lock:
            # Advance simulation step
            telem_dict, _ = self.simulator.step()
            telem = SensorTelemetry(
                device_id="esp32-sentry-sim",
                timestamp=datetime.now(timezone.utc).isoformat(),
                uptime_seconds=int(self.simulator.elapsed_time_sec),
                temperature=float(telem_dict.get("temperature", 25.0)),
                humidity=float(telem_dict.get("humidity", 40.0)),
                pressure=float(telem_dict.get("pressure", 1013.25)),
                lux=float(telem_dict.get("lux", 52000.0)),
                rain_raw=int(telem_dict.get("rain_raw", 3850)),
                rain_detected=bool(telem_dict.get("rain_detected", False)),
                pan=int(telem_dict.get("pan", 90)),
                tilt=int(telem_dict.get("tilt", 45)),
                state=DeviceState(telem_dict.get("state", "OBSERVE")),
                health=int(telem_dict.get("health", 100)),
                wifi_rssi=int(telem_dict.get("wifi_rssi", -55)),
                camera_online=bool(telem_dict.get("camera_online", True)),
                camera_ip="192.168.1.120",
                sensor_status=telem_dict.get("sensor_status", {
                    "dht22": True,
                    "bh1750": True,
                    "bmp280": True,
                    "rain": True
                }),
                firmware_version="1.0.0-sim"
            )
            self._last_telemetry = telem
            return telem

    async def is_connected(self) -> bool:
        return True

    def get_provider_name(self) -> str:
        return "Demo / Simulation Sensor Provider"

    def switch_scenario(self, scenario_name: str) -> None:
        """Switch the running simulation scenario."""
        try:
            self.simulator.set_scenario(scenario_name)
            logger.info(f"Switched Demo sensor scenario to: {scenario_name}")
        except Exception as e:
            logger.warning(f"Failed to switch simulation scenario '{scenario_name}': {e}")


class ESP32SensorProvider(SensorProvider):
    """Hardware sensor provider communicating with physical ESP32 devkit."""

    def __init__(self, timeout_sec: float = 30.0):
        self.timeout_sec = timeout_sec
        self.last_received_time: float = 0.0
        self.last_telemetry: Optional[SensorTelemetry] = None
        self._lock = asyncio.Lock()

    def record_incoming_telemetry(self, telemetry: SensorTelemetry) -> None:
        """Invoked when physical ESP32 posts telemetry to /api/v1/telemetry."""
        self.last_telemetry = telemetry
        self.last_received_time = time.time()

    async def is_connected(self) -> bool:
        if self.last_telemetry is None:
            return False
        return (time.time() - self.last_received_time) < self.timeout_sec

    async def get_telemetry(self) -> SensorTelemetry:
        async with self._lock:
            connected = await self.is_connected()
            if not connected:
                # Return explicit OFFLINE state — NEVER fake live data in HARDWARE mode
                return SensorTelemetry(
                    device_id=settings.DEFAULT_DEVICE_ID,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    uptime_seconds=0,
                    temperature=0.0,
                    humidity=0.0,
                    pressure=0.0,
                    lux=0.0,
                    rain_raw=4095,
                    rain_detected=False,
                    pan=90,
                    tilt=0,
                    state=DeviceState.OFFLINE,
                    health=0,
                    wifi_rssi=-100,
                    camera_online=False,
                    camera_ip="DISCONNECTED",
                    sensor_status={
                        "dht22": False,
                        "bh1750": False,
                        "bmp280": False,
                        "rain": False
                    },
                    firmware_version="DISCONNECTED"
                )
            assert self.last_telemetry is not None
            return self.last_telemetry

    def get_provider_name(self) -> str:
        return "Live ESP32 Hardware Sensor Provider"


# =============================================================================
# CAMERA PROVIDERS & CALIBRATION
# =============================================================================

class CameraProvider(ABC):
    """Abstract interface for solar optical capture and camera management."""

    @abstractmethod
    async def capture_raw_frame(self) -> bytes:
        """Acquire single raw optical image frame as JPEG bytes."""
        pass

    @abstractmethod
    async def get_status(self) -> Dict[str, Any]:
        """Query camera hardware health, resolution, and connection status."""
        pass

    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """Perform ping/handshake test to camera interface."""
        pass


class DemoCameraProvider(CameraProvider):
    """Simulation optical camera generating synthetic solar disks with solar limb darkening."""

    def __init__(self):
        self.current_preset = "clear_with_sunspots"
        self.frame_counter = 0

    def set_preset(self, preset: str) -> None:
        self.current_preset = preset

    async def capture_raw_frame(self) -> bytes:
        self.frame_counter += 1
        # Generate clean synthetic frame
        bgr = generate_synthetic_solar_image(
            width=640,
            height=480,
            preset=self.current_preset,
            sunspot_count=3,
            seed=self.frame_counter % 100
        )
        ok, buf = cv2.imencode(".jpg", bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
        if not ok:
            raise RuntimeError("Failed to encode synthetic JPEG frame.")
        return buf.tobytes()

    async def get_status(self) -> Dict[str, Any]:
        return {
            "online": True,
            "provider": "Demo Simulation Camera",
            "url": "simulation://internal-generator",
            "resolution": "VGA_640x480",
            "fps_target": 1.0,
            "latency_ms": 1.5,
            "lens_type": "Virtual 1/4\" CMOS F/2.0 Solar Telephoto",
            "device_status": "ONLINE_SIMULATED"
        }

    async def test_connection(self) -> Dict[str, Any]:
        return {
            "status": "SUCCESS",
            "message": "Demo Camera generator reachable and nominal.",
            "latency_ms": 1.2
        }


class ESP32CamProvider(CameraProvider):
    """Physical ESP32-CAM companion node communicating over HTTP."""

    def __init__(self, base_url: str = "http://192.168.1.120", timeout_sec: float = 3.5):
        self.base_url = base_url.rstrip("/")
        self.timeout_sec = timeout_sec

    def update_url(self, url: str) -> None:
        self.base_url = url.rstrip("/")
        logger.info(f"ESP32-CAM target URL updated to: {self.base_url}")

    async def get_status(self) -> Dict[str, Any]:
        target = f"{self.base_url}/status"
        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
                resp = await client.get(target)
                dt_ms = round((time.perf_counter() - t0) * 1000, 1)
                if resp.status_code == 200:
                    data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                    return {
                        "online": True,
                        "provider": "Physical ESP32-CAM Node",
                        "url": self.base_url,
                        "resolution": data.get("resolution", "SVGA_800x600"),
                        "captures_served": data.get("captures_served", 0),
                        "uptime_seconds": data.get("uptime_seconds", 0),
                        "wifi_rssi": data.get("wifi_rssi", -60),
                        "latency_ms": dt_ms,
                        "device_status": "ONLINE"
                    }
                else:
                    return {
                        "online": False,
                        "provider": "Physical ESP32-CAM Node",
                        "url": self.base_url,
                        "error": f"HTTP {resp.status_code}",
                        "latency_ms": dt_ms,
                        "device_status": "ERROR_RESPONSE"
                    }
        except Exception as e:
            return {
                "online": False,
                "provider": "Physical ESP32-CAM Node",
                "url": self.base_url,
                "error": str(e),
                "device_status": "OFFLINE"
            }

    async def test_connection(self) -> Dict[str, Any]:
        target = f"{self.base_url}/status"
        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
                resp = await client.get(target)
                dt_ms = round((time.perf_counter() - t0) * 1000, 1)
                if resp.status_code == 200:
                    return {
                        "status": "SUCCESS",
                        "message": f"Successfully connected to ESP32-CAM at {self.base_url}",
                        "latency_ms": dt_ms
                    }
                return {
                    "status": "FAILED",
                    "message": f"Camera returned HTTP {resp.status_code}",
                    "latency_ms": dt_ms
                }
        except Exception as e:
            return {
                "status": "FAILED",
                "message": f"Could not reach ESP32-CAM at {self.base_url}: {e}",
                "latency_ms": -1
            }

    async def capture_raw_frame(self) -> bytes:
        target = f"{self.base_url}/capture"
        try:
            async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
                resp = await client.get(target)
                if resp.status_code == 200 and len(resp.content) > 100:
                    return resp.content
                raise RuntimeError(f"ESP32-CAM capture returned status {resp.status_code}")
        except Exception as e:
            logger.warning(f"ESP32-CAM capture failed ({self.base_url}): {e}")
            raise


# =============================================================================
# ACTUATOR PROVIDERS
# =============================================================================

class ActuatorProvider(ABC):
    """Abstract interface for dual-axis tracking gimbal actuation."""

    @abstractmethod
    async def execute_command(self, command: Command) -> CommandResult:
        """Dispatch control verb to actuator hardware."""
        pass


class DemoActuatorProvider(ActuatorProvider):
    """Simulated dual-axis gimbal controller with software limits and slew dynamics."""

    def __init__(self):
        self.pan = 90
        self.tilt = 45
        self.state = DeviceState.STANDBY

    async def execute_command(self, command: Command) -> CommandResult:
        # Software limits check
        if command.pan is not None and command.pan >= 0:
            self.pan = max(0, min(180, command.pan))
        if command.tilt is not None and command.tilt >= 0:
            self.tilt = max(0, min(180, command.tilt))

        if command.command == "PARK":
            self.pan = 90
            self.tilt = 0
            self.state = DeviceState.SAFE
        elif command.command == "OBSERVE":
            self.state = DeviceState.OBSERVE
        elif command.command == "SET_STATE" and command.target_state:
            try:
                self.state = DeviceState(command.target_state)
            except ValueError:
                pass

        return CommandResult(
            command_id=command.command_id,
            status=CommandStatus.SUCCESS,
            message=f"Simulated slew completed to (Pan: {self.pan}°, Tilt: {self.tilt}°). State: {self.state.value}",
            current_pan=self.pan,
            current_tilt=self.tilt,
            current_state=self.state,
            timestamp=datetime.now(timezone.utc).isoformat()
        )


class ESP32ActuatorProvider(ActuatorProvider):
    """Physical ESP32 servo command dispatcher."""

    def __init__(self, esp32_host: str = "192.168.1.100", esp32_port: int = 80):
        self.esp32_host = esp32_host
        self.esp32_port = esp32_port
        self._command_queue: List[Command] = []

    def queue_for_poll(self, command: Command) -> None:
        self._command_queue.append(command)

    def pop_queued_command(self) -> Optional[Command]:
        if self._command_queue:
            return self._command_queue.pop(0)
        return None

    async def execute_command(self, command: Command) -> CommandResult:
        # If ESP32 is polling commands via HTTP, enqueue it
        self.queue_for_poll(command)
        return CommandResult(
            command_id=command.command_id,
            status=CommandStatus.EXECUTING,
            message="Command queued for physical ESP32 edge polling dispatch.",
            current_pan=command.pan if command.pan is not None else 90,
            current_tilt=command.tilt if command.tilt is not None else 0,
            current_state=DeviceState.OBSERVE if command.command == "OBSERVE" else DeviceState.STANDBY,
            timestamp=datetime.now(timezone.utc).isoformat()
        )


# =============================================================================
# PROVIDER MANAGER (SYSTEM MODE TOGGLE COORDINATOR)
# =============================================================================

class ProviderManager:
    """Coordinates active subsystem providers and manages non-destructive DEMO <-> HARDWARE toggling."""

    def __init__(self):
        self._mode: SystemMode = SystemMode.DEMO
        self._camera_url: str = "http://192.168.1.120"
        self._lock = asyncio.Lock()

        # Providers
        self.demo_sensor = DemoSensorProvider()
        self.esp32_sensor = ESP32SensorProvider()

        self.demo_camera = DemoCameraProvider()
        self.esp32_camera = ESP32CamProvider(base_url=self._camera_url)

        self.demo_actuator = DemoActuatorProvider()
        self.esp32_actuator = ESP32ActuatorProvider()

    @property
    def mode(self) -> SystemMode:
        return self._mode

    def set_mode(self, new_mode: SystemMode | str) -> SystemMode:
        if isinstance(new_mode, str):
            new_mode = SystemMode(new_mode.upper())
        self._mode = new_mode
        logger.info(f"Solar Sentry System Mode changed to: [ {self._mode.value} ]")
        return self._mode

    @property
    def camera_url(self) -> str:
        return self._camera_url

    def set_camera_url(self, url: str) -> str:
        clean = url.strip().rstrip("/")
        if not clean.startswith("http://") and not clean.startswith("https://"):
            clean = f"http://{clean}"
        self._camera_url = clean
        self.esp32_camera.update_url(clean)
        return self._camera_url

    @property
    def sensor_provider(self) -> SensorProvider:
        if self._mode == SystemMode.HARDWARE:
            return self.esp32_sensor
        return self.demo_sensor

    @property
    def camera_provider(self) -> CameraProvider:
        if self._mode == SystemMode.HARDWARE:
            return self.esp32_camera
        return self.demo_camera

    @property
    def actuator_provider(self) -> ActuatorProvider:
        if self._mode == SystemMode.HARDWARE:
            return self.esp32_actuator
        return self.demo_actuator


# Global Singleton Instance
provider_manager = ProviderManager()
