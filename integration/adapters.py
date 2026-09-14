"""
Solar Sentry — Multi-Agent Subsystem Integration Adapters
Agent 10: Digital Twin + Mission Memory + Learning + Simulation + Integration

Standardizes communication and contract translation between all 10 subsystem boundaries:
- Agent 1: ESP32 Edge Device / Mock Simulator
- Agent 2: Backend Ingestion & Communication
- Agent 3: Database & Data Persistence
- Agent 5: Computer Vision Pipeline
- Agent 6: Environment Prediction
- Agent 7: Sensor Fusion & Health Anomaly Detection
- Agent 8: Cognitive Decision Engine
- Agent 9: Mission Planner & Active Perception
- Agent 10: Digital Twin, Memory, Simulation, Learning
"""

from __future__ import annotations

import datetime
import math
import uuid
from typing import Any, Dict, List, Optional, Tuple

from firmware.mock_edge.edge_simulator import SolarSentryEdgeDevice
from ai.decision.engine import CognitiveDecisionEngine
from ai.decision.types import (
    CognitiveInput,
    EdgeTelemetryState,
    EnvironmentPrediction,
    HealthFusionEvaluation,
    VisionEvaluation,
)
from ai.environment.predictor import EnvironmentPredictor
from ai.environment.schemas import TelemetryInput, VisionHints
from ai.vision.preprocessor import generate_synthetic_solar_image
from ai.vision.quality import analyze_solar_image
from ai.vision.models import ImageSourceType


class EdgeAdapter:
    """Adapter for Agent 1 ESP32 Edge Controller or Simulator."""

    def __init__(self, edge_device: Optional[SolarSentryEdgeDevice] = None):
        self.device = edge_device or SolarSentryEdgeDevice(device_id="esp32-sentry-01")

    def get_telemetry(self) -> Dict[str, Any]:
        """Polls edge controller for telemetry payload adhering to SensorTelemetry.json."""
        return self.device.generate_telemetry()

    def send_command(self, cmd_verb: str, pan: int = -1, tilt: int = -1, speed: int = 100, target_state: str = "") -> Dict[str, Any]:
        """Dispatches structured command adhering to Command.json."""
        cmd_payload = {
            "command_id": f"cmd-{uuid.uuid4().hex[:8]}",
            "command": cmd_verb,
            "pan": pan,
            "tilt": tilt,
            "speed": speed,
            "target_state": target_state,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        return self.device.execute_command(cmd_payload)

    def step(self, dt: float = 0.5) -> None:
        self.device.update(dt)


class DatabaseAdapter:
    """Mock database repository representing Agent 3 storage layer."""

    def __init__(self):
        self.telemetry_table: List[Dict[str, Any]] = []
        self.observations_table: List[Dict[str, Any]] = []
        self.events_table: List[Dict[str, Any]] = []

    def store_telemetry(self, telemetry: Dict[str, Any]) -> None:
        self.telemetry_table.append(dict(telemetry))

    def store_observation(self, observation: Dict[str, Any]) -> None:
        self.observations_table.append(dict(observation))

    def log_event(self, event_type: str, details: Dict[str, Any]) -> None:
        self.events_table.append({
            "event_type": event_type,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "details": details
        })


class HealthAnomalyAdapter:
    """Adapter representing Agent 7: Sensor Fusion & Health Anomaly AI."""

    @staticmethod
    def evaluate_health(telemetry: Dict[str, Any]) -> HealthFusionEvaluation:
        st = telemetry.get("sensor_status", {})
        sensor_health = {
            "dht22": bool(st.get("dht22", True)),
            "bh1750": bool(st.get("bh1750", True)),
            "bmp280": bool(st.get("bmp280", True)),
            "rain": bool(st.get("rain", True)),
        }
        failed = [k for k, ok in sensor_health.items() if not ok]
        all_ok = len(failed) == 0

        # Sensor disagreement checks
        conflict = False
        conflict_details = []
        # If lux is super high (> 50k) but temp is unrealistically low (< -100) or DHT22 failed
        if telemetry.get("lux", 0) > 40000 and not sensor_health["dht22"]:
            conflict = True
            conflict_details.append("High illuminance observed with offline temperature sensor")

        anomaly_score = 0.0 if all_ok else 0.45
        if not sensor_health["rain"]:
            anomaly_score = 0.85

        health_score = 1.0 if all_ok else (0.5 if "rain" not in failed else 0.1)

        return HealthFusionEvaluation(
            overall_health_score=health_score,
            is_healthy=all_ok,
            sensor_health=sensor_health,
            failed_sensors=failed,
            anomaly_score=anomaly_score,
            anomaly_detected=(not all_ok or conflict),
            sensor_conflict=conflict,
            sensor_conflict_details=conflict_details
        )


class VisionAdapter:
    """Adapter for Agent 5: Computer Vision Pipeline."""

    @staticmethod
    def analyze_frame(preset: str = "quiet_sun", width: int = 320, height: int = 240) -> Dict[str, Any]:
        """Generates synthetic solar image and executes Agent 5 analysis."""
        img_bytes = generate_synthetic_solar_image(width=width, height=height, preset=preset)
        res = analyze_solar_image(img_bytes, source_type=ImageSourceType.SIMULATION)
        return res.to_dict()


class EnvironmentAdapter:
    """Adapter for Agent 6: Environment Assessment & Prediction."""

    def __init__(self):
        self.predictor = EnvironmentPredictor()

    def predict(self, telemetry: Dict[str, Any], vision: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        t_input = TelemetryInput(
            temperature=telemetry.get("temperature", 25.0),
            humidity=telemetry.get("humidity", 40.0),
            pressure=telemetry.get("pressure", 1013.25),
            lux=telemetry.get("lux", 50000.0),
            rain_raw=telemetry.get("rain_raw", 3850),
            rain_detected=telemetry.get("rain_detected", False),
            pan=telemetry.get("pan", 90),
            tilt=telemetry.get("tilt", 45),
            state=telemetry.get("state", "STANDBY"),
            sensor_status=telemetry.get("sensor_status", {"dht22": True, "bh1750": True, "bmp280": True, "rain": True})
        )
        v_hints = None
        if vision:
            v_hints = VisionHints(
                vision_quality=vision.get("quality_score", 0.8),
                cloud_cover=vision.get("obstruction_score", 0.1),
                solar_disk_detected=vision.get("solar_disk_detected", True)
            )
        return self.predictor.predict(telemetry=t_input, vision_hints=v_hints)


class MissionPlannerAdapter:
    """Adapter representing Agent 9: Mission Planner & Active Perception."""

    def __init__(self, edge_adapter: EdgeAdapter):
        self.edge = edge_adapter
        self.active_mission_id: Optional[str] = None
        self.candidate_scan_regions: List[Tuple[int, int]] = [
            (80, 40),
            (90, 45),
            (100, 50),
            (90, 55),
        ]

    def plan_and_execute(
        self,
        decision: str,
        target_pan: int = 90,
        target_tilt: int = 45,
        scan_mode: bool = False
    ) -> Tuple[Dict[str, Any], Optional[Tuple[int, int]]]:
        """
        Translates cognitive decision into edge commands and returns (command_result, best_region).
        """
        best_region = None
        if decision == "OBSERVE":
            res = self.edge.send_command("OBSERVE", pan=target_pan, tilt=target_tilt)
            return res, (target_pan, target_tilt)

        elif decision == "SCAN" or scan_mode:
            # Sweep scan regions to find peak illuminance/contrast
            best_region = self._sweep_scan()
            res = self.edge.send_command("OBSERVE", pan=best_region[0], tilt=best_region[1])
            return res, best_region

        elif decision == "WAIT":
            res = self.edge.send_command("SET_STATE", target_state="WAIT")
            return res, None

        elif decision in ["SUSPEND", "SAFE"]:
            res = self.edge.send_command("PARK", pan=90, tilt=0)
            return res, None

        else:
            res = self.edge.send_command("SET_STATE", target_state="STANDBY")
            return res, None

    def _sweep_scan(self) -> Tuple[int, int]:
        """Simulates sweeping candidate sky coordinates and selecting region with maximum solar signal."""
        # Standard optimal solar region is typically centered at (90, 45)
        best_score = -1.0
        best_coord = (90, 45)
        for pan, tilt in self.candidate_scan_regions:
            # Score region based on proximity to solar noon angle
            dist = math.sqrt((pan - 90)**2 + (tilt - 45)**2)
            score = 1.0 / (1.0 + 0.1 * dist)
            if score > best_score:
                best_score = score
                best_coord = (pan, tilt)
        return best_coord
