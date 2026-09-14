"""Solar Sentry — Edge Hardware & Firmware Emulator (Agent 1)

Simulates the physical ESP32 edge device, sensor acquisition (DHT22, BH1750, BMP280, Rain),
pan/tilt servo mechanics, 3-LED status signaling, and local safety state machine.

Adheres strictly to docs/contracts/SensorTelemetry.json and docs/contracts/Command.json.
Used for offline testing, CI/CD, and multi-agent development without requiring physical hardware.
"""

import time
import math
import json
import logging
from typing import Dict, Any, Tuple, Optional
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(asctime)s - %(message)s")
logger = logging.getLogger("EdgeSimulator")

# Hardware Contract Constants
PAN_SAFE_DEG = 90
TILT_SAFE_DEG = 0
RAIN_THRESHOLD_ADC = 2000
OVERHEAT_TEMP_C = 65.0
COMMS_TIMEOUT_SEC = 30.0

STATE_BOOT = "BOOT"
STATE_SELF_CHECK = "SELF_CHECK"
STATE_STANDBY = "STANDBY"
STATE_OBSERVE = "OBSERVE"
STATE_WAIT = "WAIT"
STATE_SCAN = "SCAN"
STATE_SUSPEND = "SUSPEND"
STATE_FAULT = "FAULT"
STATE_SAFE = "SAFE"
STATE_DEGRADED = "DEGRADED"


class MockSensorSubsystem:
    def __init__(self):
        self.temp_base = 26.5
        self.humid_base = 45.0
        self.pressure_base = 1013.25
        self.lux_base = 45000.0
        self.rain_raw = 3850  # Dry by default (12-bit ADC: >2000 is dry)
        self.rain_detected = False

        # Fault injection flags
        self.dht_fault = False
        self.bmp_fault = False
        self.bh1750_fault = False
        self.rain_sensor_fault = False

    def sample(self, uptime_sec: float) -> Dict[str, Any]:
        """Simulates realistic sensor readings with slight diurnal drift."""
        if self.dht_fault:
            temp = -999.0
            humid = -999.0
            dht_valid = False
        else:
            temp = round(self.temp_base + 2.0 * math.sin(uptime_sec / 120.0), 2)
            humid = round(max(10.0, min(95.0, self.humid_base + 5.0 * math.cos(uptime_sec / 120.0))), 1)
            dht_valid = True

        if self.bmp_fault:
            pressure = -999.0
            bmp_valid = False
        else:
            pressure = round(self.pressure_base + 1.5 * math.sin(uptime_sec / 300.0), 2)
            bmp_valid = True
            if not dht_valid:
                temp = 25.0  # Fallback to BMP280 temperature

        if self.bh1750_fault:
            lux = -999.0
            bh1750_valid = False
        else:
            lux = round(max(0.0, self.lux_base + 10000.0 * math.sin(uptime_sec / 60.0)), 1)
            bh1750_valid = True

        self.rain_detected = (self.rain_raw < RAIN_THRESHOLD_ADC) and not self.rain_sensor_fault
        rain_valid = not self.rain_sensor_fault

        return {
            "temperature": temp,
            "humidity": humid,
            "pressure": pressure,
            "lux": lux,
            "rain_raw": self.rain_raw,
            "rain_detected": self.rain_detected,
            "sensor_status": {
                "dht22": dht_valid,
                "bh1750": bh1750_valid,
                "bmp280": bmp_valid,
                "rain": rain_valid
            }
        }


class MockActuatorSubsystem:
    def __init__(self):
        self.current_pan = PAN_SAFE_DEG
        self.current_tilt = TILT_SAFE_DEG
        self.target_pan = PAN_SAFE_DEG
        self.target_tilt = TILT_SAFE_DEG
        self.moving = False
        self.speed_deg_per_sec = 45.0

    def set_target(self, pan: int, tilt: int, speed_percent: int = 100) -> bool:
        if not (0 <= pan <= 180 and 0 <= tilt <= 180):
            return False
        self.target_pan = pan
        self.target_tilt = tilt
        self.moving = (self.current_pan != self.target_pan or self.current_tilt != self.target_tilt)
        return True

    def park_safe(self):
        self.set_target(PAN_SAFE_DEG, TILT_SAFE_DEG, 100)

    def step(self, dt: float):
        step_delta = (self.speed_deg_per_sec * dt)
        if abs(self.current_pan - self.target_pan) > 0.5:
            if self.current_pan < self.target_pan:
                self.current_pan = min(self.target_pan, self.current_pan + step_delta)
            else:
                self.current_pan = max(self.target_pan, self.current_pan - step_delta)
        else:
            self.current_pan = float(self.target_pan)

        if abs(self.current_tilt - self.target_tilt) > 0.5:
            if self.current_tilt < self.target_tilt:
                self.current_tilt = min(self.target_tilt, self.current_tilt + step_delta)
            else:
                self.current_tilt = max(self.target_tilt, self.current_tilt - step_delta)
        else:
            self.current_tilt = float(self.target_tilt)

        self.moving = (self.current_pan != self.target_pan or self.current_tilt != self.target_tilt)


class SolarSentryEdgeDevice:
    def __init__(self, device_id: str = "esp32-sentry-01"):
        self.device_id = device_id
        self.firmware_version = "1.0.0"
        self.start_time = time.time()
        self.last_backend_contact = time.time()

        self.sensors = MockSensorSubsystem()
        self.actuators = MockActuatorSubsystem()

        self.state = STATE_BOOT
        self.health_score = 100
        self.wifi_rssi = -64
        self.camera_online = True
        self.camera_ip = "192.168.1.120"

        self._boot_sequence()

    def _boot_sequence(self):
        self.state = STATE_SELF_CHECK
        self.actuators.park_safe()
        self.state = STATE_STANDBY
        logger.info(f"Edge device {self.device_id} boot completed. State: {self.state}")

    def update(self, dt: float = 0.1):
        """Simulates one cycle of the cooperative FreeRTOS loop."""
        uptime = time.time() - self.start_time
        sensor_data = self.sensors.sample(uptime)
        self.actuators.step(dt)

        # 1. Rain Safety Interlock (Highest priority)
        if sensor_data["rain_detected"]:
            if self.state != STATE_SUSPEND and self.state != STATE_FAULT:
                logger.warning("[SAFETY OVERRIDE] Rain detected! Immediate transition to SUSPEND.")
                self.state = STATE_SUSPEND
                self.actuators.park_safe()
        elif self.state == STATE_SUSPEND and not sensor_data["rain_detected"]:
            logger.info("[SAFETY RECOVERY] Rain stopped. Transitioning to STANDBY.")
            self.state = STATE_STANDBY

        # 2. Thermal Protection
        if sensor_data["temperature"] > OVERHEAT_TEMP_C and self.state != STATE_SAFE:
            logger.error(f"[THERMAL FAULT] Temperature {sensor_data['temperature']}C > {OVERHEAT_TEMP_C}C.")
            self.state = STATE_SAFE
            self.actuators.park_safe()

        # 3. Comms Timeout
        if (time.time() - self.last_backend_contact > COMMS_TIMEOUT_SEC) and self.state in [STATE_OBSERVE, STATE_SCAN]:
            logger.warning("[COMMS TIMEOUT] Central backend unreachable > 30s. Entering SAFE state.")
            self.state = STATE_SAFE
            self.actuators.park_safe()

        # 4. Compute Health Score (0 - 100)
        score = 0
        st = sensor_data["sensor_status"]
        if st["dht22"]: score += 10
        if st["bh1750"]: score += 10
        if st["bmp280"]: score += 10
        if st["rain"]: score += 10
        score += 30  # Actuators intact
        score += 20  # Wi-Fi healthy
        if not sensor_data["rain_detected"]: score += 10
        self.health_score = score

    def generate_telemetry(self) -> Dict[str, Any]:
        """Generates JSON telemetry payload adhering strictly to docs/contracts/SensorTelemetry.json"""
        uptime = time.time() - self.start_time
        s = self.sensors.sample(uptime)

        return {
            "device_id": self.device_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": int(uptime),
            "temperature": s["temperature"],
            "humidity": s["humidity"],
            "pressure": s["pressure"],
            "lux": s["lux"],
            "rain_raw": s["rain_raw"],
            "rain_detected": s["rain_detected"],
            "pan": int(round(self.actuators.current_pan)),
            "tilt": int(round(self.actuators.current_tilt)),
            "state": self.state,
            "health": self.health_score,
            "wifi_rssi": self.wifi_rssi,
            "camera_online": self.camera_online,
            "camera_ip": self.camera_ip,
            "sensor_status": s["sensor_status"],
            "firmware_version": self.firmware_version
        }

    def execute_command(self, cmd_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Parses and executes a command adhering strictly to docs/contracts/Command.json"""
        self.last_backend_contact = time.time()
        cid = cmd_dict.get("command_id", "unknown-cmd")
        verb = cmd_dict.get("command", "")
        pan = cmd_dict.get("pan", -1)
        tilt = cmd_dict.get("tilt", -1)
        speed = cmd_dict.get("speed", 100)
        target_state = cmd_dict.get("target_state", "")

        # Safety Check: Rain active prevents OBSERVE / SCAN
        if (self.sensors.rain_detected or self.state == STATE_SUSPEND) and verb in ["OBSERVE", "SCAN"]:
            return {
                "command_id": cid,
                "status": "REJECTED_SAFETY",
                "message": "Observation command rejected: Local rain safety interlock active",
                "current_pan": int(round(self.actuators.current_pan)),
                "current_tilt": int(round(self.actuators.current_tilt)),
                "current_state": self.state,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        status = "SUCCESS"
        msg = ""

        if verb == "OBSERVE":
            self.state = STATE_OBSERVE
            if pan >= 0 and tilt >= 0:
                self.actuators.set_target(pan, tilt, speed)
            msg = "Entered OBSERVE mode"
        elif verb in ["PARK", "SAFE"]:
            self.state = STATE_STANDBY
            self.actuators.park_safe()
            msg = "Parked in safe position"
        elif verb == "SCAN":
            self.state = STATE_SCAN
            if pan >= 0 and tilt >= 0:
                self.actuators.set_target(pan, tilt, speed)
            msg = "Executing scan sweep"
        elif verb == "SET_SERVO":
            if 0 <= pan <= 180 and 0 <= tilt <= 180:
                self.actuators.set_target(pan, tilt, speed)
                msg = f"Servo targeted to Pan={pan}, Tilt={tilt}"
            else:
                status = "INVALID_PARAMS"
                msg = "Angles outside [0, 180] degree range"
        elif verb == "SET_STATE":
            if target_state in [STATE_STANDBY, STATE_OBSERVE, STATE_WAIT, STATE_SCAN, STATE_SUSPEND, STATE_SAFE]:
                self.state = target_state
                msg = f"State transitioned to {target_state}"
            else:
                status = "INVALID_PARAMS"
                msg = f"Unknown target state: {target_state}"
        elif verb == "EMERGENCY_STOP":
            self.state = STATE_SAFE
            self.actuators.park_safe()
            msg = "Emergency stop executed"
        else:
            status = "INVALID_PARAMS"
            msg = f"Unrecognized command verb: {verb}"

        return {
            "command_id": cid,
            "status": status,
            "message": msg,
            "current_pan": int(round(self.actuators.current_pan)),
            "current_tilt": int(round(self.actuators.current_tilt)),
            "current_state": self.state,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


if __name__ == "__main__":
    device = SolarSentryEdgeDevice()
    print("Running Edge Simulator demo loop (5 seconds)...")
    for _ in range(10):
        device.update(0.5)
        telemetry = device.generate_telemetry()
        print(f"[{telemetry['timestamp']}] State: {telemetry['state']} | Lux: {telemetry['lux']} | Pan/Tilt: ({telemetry['pan']}°, {telemetry['tilt']}°)")
        time.sleep(0.5)
