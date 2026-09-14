"""Unit tests for Solar Sentry Edge Device + ESP32 Integration (Agent 1).

Validates:
- Telemetry generation adhering to contracts/SensorTelemetry.json
- Command parsing and execution adhering to contracts/Command.json & contracts/CommandResult.json
- Local rain emergency override safety interlocks
- Actuator bound enforcement (0 - 180 degrees)
- Communication timeout fail-safe behavior
"""

import os
import sys
import json
import pytest

# Add firmware directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../firmware/mock_edge")))
from edge_simulator import (
    SolarSentryEdgeDevice,
    STATE_STANDBY,
    STATE_OBSERVE,
    STATE_SUSPEND,
    STATE_SAFE,
    PAN_SAFE_DEG,
    TILT_SAFE_DEG,
    RAIN_THRESHOLD_ADC,
)


@pytest.fixture
def edge_device():
    return SolarSentryEdgeDevice(device_id="esp32-test-01")


def test_initial_boot_state(edge_device):
    """Verifies that the edge controller boots into STANDBY with actuators parked safely."""
    assert edge_device.state == STATE_STANDBY
    assert edge_device.actuators.current_pan == PAN_SAFE_DEG
    assert edge_device.actuators.current_tilt == TILT_SAFE_DEG
    assert edge_device.health_score == 100


def test_telemetry_schema_compliance(edge_device):
    """Verifies that generated telemetry matches all required keys and types in SensorTelemetry.json."""
    edge_device.update(0.1)
    telemetry = edge_device.generate_telemetry()

    required_keys = [
        "device_id", "timestamp", "uptime_seconds", "temperature", "humidity",
        "pressure", "lux", "rain_raw", "rain_detected", "pan", "tilt",
        "state", "health", "firmware_version", "sensor_status"
    ]

    for key in required_keys:
        assert key in telemetry, f"Missing required telemetry key: {key}"

    assert telemetry["device_id"] == "esp32-test-01"
    assert isinstance(telemetry["uptime_seconds"], int)
    assert isinstance(telemetry["temperature"], (int, float))
    assert 0 <= telemetry["humidity"] <= 100
    assert telemetry["pressure"] > 800
    assert 0 <= telemetry["pan"] <= 180
    assert 0 <= telemetry["tilt"] <= 180
    assert 0 <= telemetry["health"] <= 100
    assert isinstance(telemetry["rain_detected"], bool)


def test_observe_command_execution(edge_device):
    """Verifies valid OBSERVE command slews servos and updates state."""
    cmd = {
        "command_id": "test-cmd-001",
        "command": "OBSERVE",
        "pan": 120,
        "tilt": 65,
        "speed": 100
    }
    result = edge_device.execute_command(cmd)

    assert result["status"] == "SUCCESS"
    assert result["command_id"] == "test-cmd-001"
    assert edge_device.state == STATE_OBSERVE
    assert edge_device.actuators.target_pan == 120
    assert edge_device.actuators.target_tilt == 65


def test_park_command_execution(edge_device):
    """Verifies PARK command returns actuators to safe position (90°, 0°)."""
    # Move somewhere else first
    edge_device.execute_command({"command_id": "c1", "command": "OBSERVE", "pan": 45, "tilt": 80})

    # Now park
    result = edge_device.execute_command({"command_id": "c2", "command": "PARK"})
    assert result["status"] == "SUCCESS"
    assert edge_device.actuators.target_pan == PAN_SAFE_DEG
    assert edge_device.actuators.target_tilt == TILT_SAFE_DEG


def test_invalid_servo_parameters_rejected(edge_device):
    """Verifies out-of-bounds angles (< 0 or > 180) are rejected."""
    bad_cmd = {
        "command_id": "test-bad-001",
        "command": "SET_SERVO",
        "pan": -15,
        "tilt": 200
    }
    result = edge_device.execute_command(bad_cmd)
    assert result["status"] == "INVALID_PARAMS"


def test_rain_emergency_override(edge_device):
    """CRITICAL SAFETY TEST:
    Simulates rain sensor reading moisture.
    System must immediately enter SUSPEND state, park servos, and reject observation commands.
    """
    # System is observing sun
    edge_device.execute_command({"command_id": "c1", "command": "OBSERVE", "pan": 90, "tilt": 85})
    assert edge_device.state == STATE_OBSERVE

    # Simulate rain arrival (ADC drops below RAIN_THRESHOLD_ADC)
    edge_device.sensors.rain_raw = 500  # wet
    edge_device.update(0.1)

    # Edge must automatically transition to SUSPEND
    assert edge_device.state == STATE_SUSPEND
    assert edge_device.actuators.target_pan == PAN_SAFE_DEG
    assert edge_device.actuators.target_tilt == TILT_SAFE_DEG

    # Attempt to command OBSERVE during rain must be rejected by safety interlock
    attempt = edge_device.execute_command({"command_id": "c2", "command": "OBSERVE", "pan": 90, "tilt": 45})
    assert attempt["status"] == "REJECTED_SAFETY"
    assert edge_device.state == STATE_SUSPEND

    # When rain clears, system recovers
    edge_device.sensors.rain_raw = 3800  # dry
    edge_device.update(0.1)
    assert edge_device.state == STATE_STANDBY


def test_comms_timeout_failsafe(edge_device):
    """Verifies that loss of backend communication while in OBSERVE triggers SAFE state and parking."""
    edge_device.execute_command({"command_id": "c1", "command": "OBSERVE", "pan": 90, "tilt": 60})
    assert edge_device.state == STATE_OBSERVE

    # Fast-forward simulated last backend contact
    edge_device.last_backend_contact = edge_device.last_backend_contact - 35.0  # 35 seconds ago
    edge_device.update(0.1)

    assert edge_device.state == STATE_SAFE
    assert edge_device.actuators.target_pan == PAN_SAFE_DEG
    assert edge_device.actuators.target_tilt == TILT_SAFE_DEG


def test_sensor_fault_health_impact(edge_device):
    """Verifies that sensor hardware fault reduces the device health score."""
    edge_device.sensors.dht_fault = True
    edge_device.update(0.1)

    telemetry = edge_device.generate_telemetry()
    assert telemetry["sensor_status"]["dht22"] is False
    assert telemetry["health"] < 100
