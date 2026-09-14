"""Solar Sentry — Safe Recovery & Emergency Interlock Manager.

Agent 9 Ownership.
Enforces the core rule: Safety strictly overrides mission optimization.
Handles emergency aborts, safe stowing, state entry (SUSPEND / SAFE),
and verified recovery sequencing once hazardous conditions clear.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Tuple, List, Optional
from datetime import datetime, timezone
import uuid

from .types import (
    Command,
    CommandResult,
    ActionVerb,
    FailureReason,
)
from .dispatcher import CommandDispatcherInterface

logger = logging.getLogger("SafeRecoveryManager")


class SafeRecoveryManager:
    """
    Manages emergency stowing, safety aborts, and cautious system recovery.
    """

    PAN_SAFE_DEG = 90
    TILT_SAFE_DEG = 0
    MAX_RECOVERY_TEMP_C = 55.0
    MIN_RECOVERY_LUX = 1000.0

    def __init__(self, dispatcher: CommandDispatcherInterface):
        self.dispatcher = dispatcher
        self.last_safety_trip_reason: Optional[str] = None
        self.last_safety_trip_time: Optional[str] = None

    def execute_emergency_suspension(
        self,
        reason: str = "Unspecified safety condition",
        trip_type: FailureReason = FailureReason.SAFETY_INTERLOCK,
    ) -> CommandResult:
        """
        Immediately aborts any active mission and commands the edge controller
        to park in the protected safe position (Pan=90°, Tilt=0°).
        """
        self.last_safety_trip_reason = reason
        self.last_safety_trip_time = datetime.now(timezone.utc).isoformat()

        logger.critical(f"[EMERGENCY OVERRIDE] Safety trip triggered: {reason}. Commanding safe stow.")

        emergency_cmd = Command(
            command_id=f"cmd-emergency-{uuid.uuid4().hex[:6]}",
            command=ActionVerb.EMERGENCY_STOP,
            pan=self.PAN_SAFE_DEG,
            tilt=self.TILT_SAFE_DEG,
            speed=100,
            target_state="SUSPEND" if trip_type == FailureReason.RAIN_OVERRIDE else "SAFE",
        )

        res = self.dispatcher.dispatch(emergency_cmd, timeout_sec=2.0)
        return res

    def check_recovery_readiness(
        self,
        telemetry: Dict[str, Any],
    ) -> Tuple[bool, List[str]]:
        """
        Verifies the multi-point pre-flight checklist before recovery can occur:
        1. Rain sensor dry
        2. Thermal conditions normal
        3. Comms online
        4. Hardware sensors plausible
        """
        blockers: List[str] = []

        # 1. Rain check
        if telemetry.get("rain_detected", False):
            blockers.append("Precipitation moisture still present on rain sensor")

        # 2. Temperature check
        temp = telemetry.get("temperature", 25.0)
        if temp > self.MAX_RECOVERY_TEMP_C:
            blockers.append(f"Temperature ({temp:.1f}°C) exceeds recovery safety ceiling ({self.MAX_RECOVERY_TEMP_C}°C)")

        # 3. Comms check
        if not self.dispatcher.is_connected():
            blockers.append("Dispatcher communications channel to edge device is offline")

        # 4. Sensor status
        sensor_status = telemetry.get("sensor_status", {})
        if not sensor_status.get("rain", True):
            blockers.append("Rain sensor hardware reported faulty")
        if not sensor_status.get("bh1750", True):
            blockers.append("Photometric illuminance sensor (BH1750) reported offline")

        is_ready = len(blockers) == 0
        return is_ready, blockers

    def execute_recovery(
        self,
        telemetry: Dict[str, Any],
    ) -> Tuple[bool, str]:
        """
        Attempts clean recovery from SUSPEND / SAFE into STANDBY state
        if all safety preconditions are verified satisfied.
        """
        ready, blockers = self.check_recovery_readiness(telemetry)
        if not ready:
            msg = f"Recovery rejected by safety gate: {'; '.join(blockers)}"
            logger.warning(msg)
            return False, msg

        logger.info("[RECOVERY] All safety conditions clear. Transitioning system to STANDBY.")
        recovery_cmd = Command(
            command_id=f"cmd-recover-{uuid.uuid4().hex[:6]}",
            command=ActionVerb.SET_STATE,
            target_state="STANDBY",
            pan=self.PAN_SAFE_DEG,
            tilt=self.TILT_SAFE_DEG,
        )

        res = self.dispatcher.dispatch(recovery_cmd, timeout_sec=3.0)
        if res.status == "SUCCESS":
            self.last_safety_trip_reason = None
            return True, "Observed conditions clear. Recovery to STANDBY completed successfully."
        else:
            return False, f"Recovery command rejected by controller: {res.message}"
