"""
Solar Sentry — Serial Telemetry & Actuator Hardware Service
Continuously interfaces with physical ESP32 DevKit over USB Serial (e.g. COM3 at 115200 baud).
Parses diagnostic telemetry reports, auto-reconnects on disconnection, and updates the active
sensor provider and central observatory state in real time.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import re
import sys
import time
from typing import Any, Dict, Optional

import serial
import serial.tools.list_ports

from app.config import settings
from app.core.logging import logger
from app.schemas.telemetry import DeviceState, SensorStatus, SensorTelemetry


class SerialTelemetryReader:
    """Manages serial connection to the physical ESP32 edge controller."""

    def __init__(
        self,
        port: Optional[str] = None,
        baudrate: int = 115200,
        reconnect_interval_sec: float = 3.0
    ):
        self.configured_port = port or settings.SERIAL_PORT
        self.baudrate = baudrate or settings.SERIAL_BAUDRATE
        self.reconnect_interval_sec = reconnect_interval_sec

        self.ser: Optional[serial.Serial] = None
        self._running: bool = False
        self._is_connected: bool = False
        self._current_port: Optional[str] = None
        self._task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

        self._latest_telemetry: Optional[SensorTelemetry] = None
        self._current_report_data: Dict[str, Any] = {}
        self._last_received_time: float = 0.0

    @property
    def is_connected(self) -> bool:
        return self._is_connected and (time.time() - self._last_received_time) < 15.0

    @property
    def current_port(self) -> Optional[str]:
        return self._current_port

    @property
    def latest_telemetry(self) -> Optional[SensorTelemetry]:
        return self._latest_telemetry

    def find_available_port(self) -> Optional[str]:
        """Detect configured port or scan for available ESP32 / USB-Serial devices."""
        ports = list(serial.tools.list_ports.comports())
        if not ports:
            return None

        # Check configured port first
        for p in ports:
            if p.device.upper() == self.configured_port.upper():
                return p.device

        # Fallback to ports with CP210x, CH340, USB, or FTDI descriptions
        for p in ports:
            desc = (p.description or "").lower()
            if any(k in desc for k in ["cp210", "ch340", "usb", "serial", "uart", "esp32"]):
                return p.device

        # Default to first available COM port
        return ports[0].device

    def open_port(self) -> bool:
        """Attempt to open the serial port."""
        target_port = self.find_available_port() or self.configured_port
        try:
            ser = serial.Serial()
            ser.port = target_port
            ser.baudrate = self.baudrate
            ser.timeout = 1.0
            # Prevent unexpected DTR/RTS resets when connecting to running ESP32
            ser.dtr = False
            ser.rts = False
            ser.open()

            self.ser = ser
            self._current_port = target_port
            self._is_connected = True
            logger.info(f"[SerialReader] Successfully connected to ESP32 on {target_port} @ {self.baudrate} baud.")
            return True

        except PermissionError:
            logger.warning(
                f"[SerialReader] Access denied opening {target_port}. "
                f"Ensure Arduino IDE Serial Monitor or other serial terminals are closed."
            )
            self._is_connected = False
            return False
        except Exception as e:
            logger.debug(f"[SerialReader] Unable to open {target_port}: {e}")
            self._is_connected = False
            return False

    def close_port(self) -> None:
        """Safely close serial port."""
        if self.ser:
            try:
                self.ser.close()
            except Exception:
                pass
            self.ser = None
        self._is_connected = False

    async def send_command(self, cmd: str) -> bool:
        """Transmit an actuator or mode command string over serial to the physical ESP32."""
        if not self.ser or not self._is_connected:
            return False

        async with self._lock:
            try:
                line = f"{cmd.strip()}\n".encode("utf-8")
                await asyncio.to_thread(self.ser.write, line)
                await asyncio.to_thread(self.ser.flush)
                logger.info(f"[SerialReader] Dispatched command over serial to ESP32: '{cmd.strip()}'")
                return True
            except Exception as e:
                logger.warning(f"[SerialReader] Failed to send serial command '{cmd}': {e}")
                return False

    def _parse_line(self, line: str) -> None:
        """Parse lines emitted by ESP32 printSystemReport() and createTelemetryJSON()."""
        # 1. Delimiter check
        if "================================================" in line:
            if len(self._current_report_data) >= 5:
                self._build_and_publish_telemetry(self._current_report_data)
                self._current_report_data = {}
            return

        # 2. Check for single-line JSON payload if sent by ESP32
        line_clean = line.strip()
        if line_clean.startswith("{") and line_clean.endswith("}"):
            try:
                parsed_json = json.loads(line_clean)
                self._build_from_json(parsed_json)
                return
            except Exception:
                pass

        # 3. Check for Key: Value format
        if ":" in line:
            parts = line.split(":", 1)
            key = parts[0].strip().lower()
            val_str = parts[1].strip()

            if key == "temperature":
                try:
                    self._current_report_data["temperature"] = float(re.findall(r"[-+]?\d*\.?\d+", val_str)[0])
                except Exception:
                    pass
            elif key == "humidity":
                try:
                    self._current_report_data["humidity"] = float(re.findall(r"[-+]?\d*\.?\d+", val_str)[0])
                except Exception:
                    pass
            elif key == "pressure":
                try:
                    self._current_report_data["pressure"] = float(re.findall(r"[-+]?\d*\.?\d+", val_str)[0])
                except Exception:
                    pass
            elif key == "light":
                try:
                    self._current_report_data["lux"] = float(re.findall(r"[-+]?\d*\.?\d+", val_str)[0])
                except Exception:
                    pass
            elif "rain adc" in key:
                try:
                    self._current_report_data["rain_raw"] = int(re.findall(r"\d+", val_str)[0])
                except Exception:
                    pass
            elif key == "dht22":
                try:
                    self._current_report_data["dht22_confidence"] = float(re.findall(r"[-+]?\d*\.?\d+", val_str)[0])
                except Exception:
                    pass
            elif key == "bmp280":
                try:
                    self._current_report_data["bmp280_confidence"] = float(re.findall(r"[-+]?\d*\.?\d+", val_str)[0])
                except Exception:
                    pass
            elif key == "bh1750":
                try:
                    self._current_report_data["bh1750_confidence"] = float(re.findall(r"[-+]?\d*\.?\d+", val_str)[0])
                except Exception:
                    pass
            elif "rain sensor" in key:
                try:
                    self._current_report_data["rain_confidence"] = float(re.findall(r"[-+]?\d*\.?\d+", val_str)[0])
                except Exception:
                    pass
            elif "overall health" in key:
                try:
                    self._current_report_data["overall_health"] = float(re.findall(r"[-+]?\d*\.?\d+", val_str)[0])
                except Exception:
                    pass
            elif "environment score" in key:
                try:
                    self._current_report_data["environment_score"] = float(re.findall(r"[-+]?\d*\.?\d+", val_str)[0])
                except Exception:
                    pass
            elif "local readiness" in key:
                try:
                    self._current_report_data["local_readiness"] = float(re.findall(r"[-+]?\d*\.?\d+", val_str)[0])
                except Exception:
                    pass
            elif "vision score" in key:
                try:
                    self._current_report_data["vision_score"] = float(re.findall(r"[-+]?\d*\.?\d+", val_str)[0])
                except Exception:
                    pass
            elif "solar data score" in key:
                try:
                    self._current_report_data["solar_data_score"] = float(re.findall(r"[-+]?\d*\.?\d+", val_str)[0])
                except Exception:
                    pass
            elif "confidence" in key and "observation" not in key:
                try:
                    self._current_report_data["confidence"] = float(re.findall(r"[-+]?\d*\.?\d+", val_str)[0])
                except Exception:
                    pass
            elif "ai decision" in key:
                self._current_report_data["ai_decision"] = val_str
            elif "current state" in key:
                self._current_report_data["current_state"] = val_str
            elif key == "pan":
                try:
                    self._current_report_data["pan"] = int(re.findall(r"\d+", val_str)[0])
                except Exception:
                    pass
            elif key == "tilt":
                try:
                    self._current_report_data["tilt"] = int(re.findall(r"\d+", val_str)[0])
                except Exception:
                    pass
            elif key == "wi-fi":
                self._current_report_data["wifi"] = val_str
            elif "device id" in key:
                self._current_report_data["device_id"] = val_str
            elif "uptime" in key:
                try:
                    self._current_report_data["uptime_seconds"] = int(re.findall(r"\d+", val_str)[0])
                except Exception:
                    pass

    def _build_and_publish_telemetry(self, data: Dict[str, Any]) -> None:
        """Construct validated SensorTelemetry model and inject into provider manager and WebSocket."""
        try:
            state_raw = str(data.get("current_state", "OBSERVE")).upper().strip()
            # Map state safely
            try:
                dev_state = DeviceState(state_raw)
            except ValueError:
                dev_state = DeviceState.OBSERVE

            rain_raw_val = int(data.get("rain_raw", 4095))
            rain_detected = rain_raw_val < 1500

            health_val = int(round(float(data.get("overall_health", 100))))
            health_val = max(0, min(100, health_val))

            status_dht = float(data.get("dht22_confidence", 100.0)) > 0
            status_bmp = float(data.get("bmp280_confidence", 100.0)) > 0
            status_bh1750 = float(data.get("bh1750_confidence", 100.0)) > 0
            status_rain = float(data.get("rain_confidence", 100.0)) > 0

            telemetry = SensorTelemetry(
                device_id=str(data.get("device_id", settings.DEFAULT_DEVICE_ID)),
                timestamp=datetime.now(timezone.utc).isoformat(),
                uptime_seconds=int(data.get("uptime_seconds", 0)),
                temperature=float(data.get("temperature", 22.0)),
                humidity=float(max(0.0, min(100.0, data.get("humidity", 50.0)))),
                pressure=float(data.get("pressure", 1013.25)),
                lux=float(max(0.0, min(65535.0, data.get("lux", 500.0)))),
                rain_raw=max(0, min(4095, rain_raw_val)),
                rain_detected=rain_detected,
                pan=int(max(0, min(180, data.get("pan", 90)))),
                tilt=int(max(0, min(180, data.get("tilt", 90)))),
                state=dev_state,
                health=health_val,
                wifi_rssi=-50 if data.get("wifi") == "CONNECTED" else -90,
                camera_online=True,
                camera_ip="solar-sentry-cam.local",
                sensor_status=SensorStatus(
                    dht22=status_dht,
                    bh1750=status_bh1750,
                    bmp280=status_bmp,
                    rain=status_rain
                ),
                firmware_version="1.0.0-edge"
            )

            self._latest_telemetry = telemetry
            self._last_received_time = time.time()
            self._is_connected = True

            # Ingest into active provider
            from app.core.providers import provider_manager
            provider_manager.esp32_sensor.record_incoming_telemetry(telemetry)

            logger.info(
                f"[SerialReader] Live Hardware Ingest: Temp={telemetry.temperature}°C, "
                f"Hum={telemetry.humidity}%, Lux={telemetry.lux}, Rain={telemetry.rain_raw}, "
                f"Health={telemetry.health}%, State={telemetry.state.value}"
            )

        except Exception as e:
            logger.error(f"[SerialReader] Error constructing telemetry from data: {e}")

    def _build_from_json(self, data: Dict[str, Any]) -> None:
        """Handle JSON telemetry frame if emitted by createTelemetryJSON()."""
        try:
            state_raw = str(data.get("state", "OBSERVE")).upper().strip()
            try:
                dev_state = DeviceState(state_raw)
            except ValueError:
                dev_state = DeviceState.OBSERVE

            rain_raw_val = int(data.get("rain_raw", 4095))
            health_val = int(round(float(data.get("sensor_health", 100))))

            telemetry = SensorTelemetry(
                device_id=str(data.get("device_id", settings.DEFAULT_DEVICE_ID)),
                timestamp=datetime.now(timezone.utc).isoformat(),
                uptime_seconds=int(data.get("uptime_ms", 0)) // 1000,
                temperature=float(data.get("temperature", 22.0)),
                humidity=float(max(0.0, min(100.0, data.get("humidity", 50.0)))),
                pressure=float(data.get("pressure", 1013.25)),
                lux=float(max(0.0, min(65535.0, data.get("lux", 500.0)))),
                rain_raw=rain_raw_val,
                rain_detected=rain_raw_val < 1500,
                pan=int(max(0, min(180, data.get("pan", 90)))),
                tilt=int(max(0, min(180, data.get("tilt", 90)))),
                state=dev_state,
                health=health_val,
                wifi_rssi=int(data.get("wifi_rssi", -50)),
                camera_online=True,
                sensor_status=SensorStatus(
                    dht22=bool(data.get("dht_ok", True)),
                    bh1750=bool(data.get("bh1750_ok", True)),
                    bmp280=bool(data.get("bmp_ok", True)),
                    rain=bool(data.get("rain_ok", True))
                ),
                firmware_version="1.0.0-edge"
            )

            self._latest_telemetry = telemetry
            self._last_received_time = time.time()
            self._is_connected = True

            from app.core.providers import provider_manager
            provider_manager.esp32_sensor.record_incoming_telemetry(telemetry)

        except Exception as e:
            logger.error(f"[SerialReader] Error parsing JSON telemetry: {e}")

    async def _read_loop(self) -> None:
        """Main asynchronous background reading loop."""
        logger.info("[SerialReader] Background serial worker loop started.")
        while self._running:
            try:
                # 1. Ensure port is open
                if not self.ser or not self.ser.is_open:
                    opened = await asyncio.to_thread(self.open_port)
                    if not opened:
                        await asyncio.sleep(self.reconnect_interval_sec)
                        continue

                # 2. Read lines
                raw = await asyncio.to_thread(self.ser.readline)
                if not raw:
                    await asyncio.sleep(0.05)
                    continue

                line = raw.decode("utf-8", errors="replace").strip()
                if line:
                    self._parse_line(line)

            except serial.SerialException as se:
                logger.warning(f"[SerialReader] Serial port error / disconnected: {se}")
                self.close_port()
                await asyncio.sleep(self.reconnect_interval_sec)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[SerialReader] Unexpected error in read loop: {e}")
                await asyncio.sleep(1.0)

        self.close_port()
        logger.info("[SerialReader] Background serial worker loop terminated.")

    def start(self) -> asyncio.Task:
        """Launch serial reader in background task."""
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._read_loop())
        return self._task

    def stop(self) -> None:
        """Stop background task and close port."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
        self.close_port()


# Global Singleton Instance
serial_reader = SerialTelemetryReader()
