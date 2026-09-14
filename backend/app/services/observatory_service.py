import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List

from app.schemas.observatory import (
    ObservatoryState,
    ObservatoryHealthResponse,
    ObservatoryPose,
    EnvironmentalSummary,
    SafetyStatus,
    SubsystemHealthStatus,
)
from app.schemas.telemetry import DeviceState, SensorTelemetry
from app.core.event_bus import event_bus, TOPIC_STATE_CHANGED, TOPIC_SAFETY_ALERT
from app.core.logging import logger


class ObservatoryService:
    """Maintains and coordinates the authoritative cognitive state of the Solar Sentry observatory."""

    def __init__(self):
        self._state = ObservatoryState(
            state=DeviceState.STANDBY,
            state_description="System initialized. Ready for observation directives.",
            timestamp=datetime.now(timezone.utc).isoformat(),
            pose=ObservatoryPose(pan=90, tilt=0),
            environment=EnvironmentalSummary(),
            safety=SafetyStatus(),
            active_device_id="esp32-sentry-01",
            device_online=False,
            camera_online=False,
            health_score=100,
            ai_status={}
        )
        self._lock = asyncio.Lock()

    async def get_state(self) -> ObservatoryState:
        async with self._lock:
            return self._state.model_copy()

    async def update_from_telemetry(self, telemetry: SensorTelemetry) -> ObservatoryState:
        async with self._lock:
            prev_state = self._state.state
            now = datetime.now(timezone.utc).isoformat()

            # Update Environmental summary
            env = EnvironmentalSummary(
                temperature_c=telemetry.temperature,
                humidity_pct=telemetry.humidity,
                pressure_hpa=telemetry.pressure,
                lux=telemetry.lux,
                rain_detected=bool(telemetry.rain_detected),
                rain_raw=telemetry.rain_raw
            )

            # Update Pose
            pose = ObservatoryPose(
                pan=telemetry.pan,
                tilt=telemetry.tilt,
                moving=False
            )

            # Evaluate Safety and Interlocks
            interlocks = []
            rain_emergency = bool(telemetry.rain_detected)
            if rain_emergency:
                interlocks.append("RAIN_DETECTED_LOCAL_OVERRIDE")

            overheat = telemetry.temperature > 65.0
            if overheat:
                interlocks.append("EDGE_OVERHEAT_WARNING")

            safety = SafetyStatus(
                rain_emergency=rain_emergency,
                comms_timeout=False,
                edge_overheat=overheat,
                interlocks_triggered=interlocks,
                failsafe_active=rain_emergency or (telemetry.state in [DeviceState.SUSPEND, DeviceState.SAFE, DeviceState.FAULT])
            )

            # Determine authoritative state
            effective_state = telemetry.state
            if rain_emergency and effective_state != DeviceState.SUSPEND:
                effective_state = DeviceState.SUSPEND

            state_desc = self._describe_state(effective_state)

            self._state = self._state.model_copy(update={
                "state": effective_state,
                "state_description": state_desc,
                "timestamp": now,
                "pose": pose,
                "environment": env,
                "safety": safety,
                "active_device_id": telemetry.device_id,
                "device_online": True,
                "camera_online": telemetry.camera_online if telemetry.camera_online is not None else self._state.camera_online,
                "health_score": telemetry.health
            })

            # Publish event if state changed
            if effective_state != prev_state:
                logger.info(f"Observatory state transition: {prev_state} -> {effective_state}")
                await event_bus.publish(TOPIC_STATE_CHANGED, {
                    "previous_state": prev_state,
                    "current_state": effective_state,
                    "timestamp": now,
                    "trigger": "telemetry_update"
                })

            if rain_emergency:
                await event_bus.publish(TOPIC_SAFETY_ALERT, {
                    "alert": "RAIN_EMERGENCY",
                    "rain_raw": telemetry.rain_raw,
                    "timestamp": now,
                    "action": "EMERGENCY_STOW"
                })

            return self._state.model_copy()

    async def update_ai_status(self, module_name: str, payload: Dict[str, Any]) -> None:
        async with self._lock:
            current_ai = dict(self._state.ai_status)
            current_ai[module_name] = {
                "last_update": datetime.now(timezone.utc).isoformat(),
                "summary": payload
            }
            self._state = self._state.model_copy(update={"ai_status": current_ai})

    async def get_health(self) -> ObservatoryHealthResponse:
        async with self._lock:
            state = self._state
            subsystems: List[SubsystemHealthStatus] = []

            # Edge device health
            edge_status = "OK" if state.device_online else "ERROR"
            subsystems.append(SubsystemHealthStatus(
                name="Edge Controller (ESP32)",
                status=edge_status,
                score=state.health_score if state.device_online else 0,
                details={"device_id": state.active_device_id, "online": state.device_online}
            ))

            # Environmental sensors
            env_status = "OK"
            if state.environment.rain_detected:
                env_status = "WARNING"
            subsystems.append(SubsystemHealthStatus(
                name="Environmental Sensors",
                status=env_status,
                score=85 if state.environment.rain_detected else 100,
                details={"temperature": state.environment.temperature_c, "rain": state.environment.rain_detected}
            ))

            # Camera subsystem
            cam_status = "OK" if state.camera_online else "WARNING"
            subsystems.append(SubsystemHealthStatus(
                name="Vision Node (ESP32-CAM)",
                status=cam_status,
                score=100 if state.camera_online else 60,
                details={"online": state.camera_online}
            ))

            overall_status = "HEALTHY"
            if not state.device_online or state.state == DeviceState.FAULT:
                overall_status = "CRITICAL"
            elif state.state in [DeviceState.SUSPEND, DeviceState.DEGRADED] or state.safety.failsafe_active:
                overall_status = "DEGRADED"

            return ObservatoryHealthResponse(
                overall_status=overall_status,
                health_score=state.health_score if state.device_online else 0,
                timestamp=datetime.now(timezone.utc).isoformat(),
                subsystems=subsystems,
                active_alarms=state.safety.interlocks_triggered
            )

    def _describe_state(self, state: DeviceState) -> str:
        descriptions = {
            DeviceState.BOOT: "Edge controller booting up and initializing hardware buses.",
            DeviceState.SELF_CHECK: "Diagnostic sweep and sensor sanity validation.",
            DeviceState.STANDBY: "Ready, idle, awaiting observation directives or schedule.",
            DeviceState.OBSERVE: "Active solar tracking and continuous radiometric acquisition.",
            DeviceState.WAIT: "Conditions marginal or cloud occlusion; holding observation pose.",
            DeviceState.SCAN: "Autonomous spatial raster sweep to locate solar disk center.",
            DeviceState.SUSPEND: "Adverse conditions (rain / high risk); servos stowed in safe pose.",
            DeviceState.FAULT: "Hardware subsystem fault encountered; parked safely.",
            DeviceState.SAFE: "Comms timeout fail-safe engaged; parked at neutral pose.",
            DeviceState.DEGRADED: "Non-critical sensor fault; operational with reduced redundancy."
        }
        return descriptions.get(state, "Unknown state.")


# Global singleton instance
observatory_service = ObservatoryService()
