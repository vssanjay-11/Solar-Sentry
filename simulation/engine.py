"""
Solar Sentry — Autonomous Observatory Simulation Engine
Agent 10: Digital Twin + Mission Memory + Learning + Simulation + Integration

Executes multi-modal simulation scenarios completely in software without hardware.
Drives virtual edge telemetry, pan/tilt mechanics, optical camera frames, and network delays.
"""

from __future__ import annotations

import datetime
import math
import time
from typing import Any, Dict, List, Optional, Tuple

from firmware.mock_edge.edge_simulator import SolarSentryEdgeDevice
from simulation.scenarios import ScenarioType, SimulationScenario, SimulatedStepData, get_scenario
from ai.vision.preprocessor import generate_synthetic_solar_image


class ObservatorySimulator:
    """
    Simulation driver running scenarios in real-time or fast-forward modes.
    Integrates virtual edge electronics, weather profiles, and optical simulation.
    """

    def __init__(self, scenario: Optional[SimulationScenario] = None, device_id: str = "esp32-sentry-sim"):
        self.device_id = device_id
        self.edge_device = SolarSentryEdgeDevice(device_id=device_id)
        self.scenario = scenario or get_scenario(ScenarioType.CLEAR_DAY)
        self.current_step_idx = 0
        self.elapsed_time_sec = 0.0
        self.is_running = False
        self.step_history: List[Dict[str, Any]] = []

    def set_scenario(self, scenario: SimulationScenario | str) -> None:
        """Sets or resets the active simulation scenario."""
        if isinstance(scenario, str):
            scenario = get_scenario(scenario)
        self.scenario = scenario
        self.current_step_idx = 0
        self.elapsed_time_sec = 0.0
        self.step_history.clear()

    def step(self, dt: Optional[float] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Advances the simulation by dt seconds.
        Returns:
            Tuple[Dict[str, Any], Dict[str, Any]]: (telemetry_dict, vision_dict)
        """
        step_dt = dt if dt is not None else self.scenario.step_seconds
        step_data: SimulatedStepData = self.scenario.generate_step(
            step_idx=self.current_step_idx,
            elapsed_sec=self.elapsed_time_sec
        )

        # Inject simulated scenario values into virtual edge sensor subsystem
        self.edge_device.sensors.temp_base = step_data.temperature
        self.edge_device.sensors.humid_base = step_data.humidity
        self.edge_device.sensors.pressure_base = step_data.pressure
        self.edge_device.sensors.lux_base = step_data.lux
        self.edge_device.sensors.rain_raw = step_data.rain_raw
        self.edge_device.sensors.rain_detected = step_data.rain_detected

        # Fault injection
        self.edge_device.sensors.dht_fault = not step_data.sensor_status.get("dht22", True)
        self.edge_device.sensors.bh1750_fault = not step_data.sensor_status.get("bh1750", True)
        self.edge_device.sensors.bmp_fault = not step_data.sensor_status.get("bmp280", True)
        self.edge_device.sensors.rain_sensor_fault = not step_data.sensor_status.get("rain", True)

        # Comms dropout injection
        if step_data.comms_loss:
            self.edge_device.last_backend_contact = time.time() - (step_data.comms_delay_sec + 35.0)
        else:
            self.edge_device.last_backend_contact = time.time()

        # Step edge hardware loop
        self.edge_device.update(dt=step_dt)

        if step_data.edge_state_override:
            self.edge_device.state = step_data.edge_state_override

        # Generate telemetry adhering strictly to docs/contracts/SensorTelemetry.json
        telemetry = self.edge_device.generate_telemetry()
        # Ensure exact injected values for high-fidelity scenario compliance
        telemetry["temperature"] = step_data.temperature
        telemetry["humidity"] = step_data.humidity
        telemetry["pressure"] = step_data.pressure
        telemetry["lux"] = step_data.lux
        telemetry["rain_raw"] = step_data.rain_raw
        telemetry["rain_detected"] = step_data.rain_detected
        telemetry["sensor_status"] = dict(step_data.sensor_status)

        # Generate simulated Vision result adhering to docs/contracts/VisionResult.json
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        vision_result: Dict[str, Any] = {
            "image_id": f"sim-img-{self.current_step_idx:05d}",
            "timestamp": now_str,
            "source_type": "SIMULATION",
            "image_width": 320,
            "image_height": 240,
            "quality_score": step_data.image_quality,
            "solar_disk_detected": step_data.solar_disk_detected,
            "sunspot_count": step_data.sunspot_count,
            "features": ["quiet_photosphere"] if step_data.solar_disk_detected else [],
            "obstruction_score": step_data.obstruction_score,
            "change_score": 0.02,
            "confidence": 0.92,
            "quality_metrics": {
                "blur_score": step_data.image_quality * 100.0,
                "tenengrad_score": step_data.image_quality * 50.0,
                "exposure_score": 0.90 if step_data.image_quality > 0.5 else 0.3,
                "clipped_black_fraction": 0.01,
                "clipped_white_fraction": 0.02,
                "rms_contrast": 0.45,
                "noise_estimate": 0.03,
                "composite_quality": step_data.image_quality,
                "rating": "EXCELLENT" if step_data.image_quality > 0.8 else ("USABLE" if step_data.image_quality > 0.5 else "DEGRADED")
            },
            "obstruction_metrics": {
                "obstruction_score": step_data.obstruction_score,
                "cloud_fraction": step_data.obstruction_score,
                "glare_fraction": 0.0,
                "limb_integrity": 0.95 if step_data.solar_disk_detected else 0.2,
                "obstruction_type": "CLEAR" if step_data.obstruction_score < 0.2 else "HEAVY_CLOUD"
            },
            "metadata": {
                "scenario": self.scenario.scenario_type.value,
                "vision_preset": step_data.vision_preset,
                "step_index": self.current_step_idx
            }
        }

        # Step record
        step_record = {
            "step_index": self.current_step_idx,
            "elapsed_seconds": self.elapsed_time_sec,
            "telemetry": telemetry,
            "vision": vision_result,
        }
        self.step_history.append(step_record)

        self.current_step_idx += 1
        self.elapsed_time_sec += step_dt

        return telemetry, vision_result

    def execute_command(self, cmd: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches control command to simulated edge device."""
        return self.edge_device.execute_command(cmd)

    def run_all_steps(self) -> List[Dict[str, Any]]:
        """Runs the complete scenario to termination and returns step history."""
        total_steps = int(self.scenario.duration_seconds / self.scenario.step_seconds)
        results = []
        for _ in range(total_steps):
            t, v = self.step()
            results.append({"telemetry": t, "vision": v})
        return results
