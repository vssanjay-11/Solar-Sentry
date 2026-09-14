"""Solar Sentry — Command Dispatcher Interface.

Agent 9 Ownership.
Provides clean command dispatch abstraction isolating the mission planner
from direct physical hardware drivers, adhering strictly to Agent 1's command contract.
Supports both physical HTTP dispatch and high-fidelity simulated execution.
"""

from __future__ import annotations

import time
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from .types import (
    Command,
    CommandResult,
    ActionVerb,
)

logger = logging.getLogger("CommandDispatcher")


class CommandDispatcherInterface(ABC):
    """Abstract interface for dispatching commands to the edge device controller."""

    @abstractmethod
    def dispatch(self, command: Command, timeout_sec: float = 5.0) -> CommandResult:
        """Dispatches a command and returns the execution confirmation."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Returns True if comms channel to edge controller is healthy."""
        pass


class SimulatedCommandDispatcher(CommandDispatcherInterface):
    """
    Simulation dispatcher wrapping Agent 1's SolarSentryEdgeDevice emulator.
    Allows offline testing, fault injection, timeout simulation, and hardware-in-the-loop tests.
    """

    def __init__(self, edge_device: Optional[Any] = None):
        if edge_device is None:
            try:
                from firmware.mock_edge.edge_simulator import SolarSentryEdgeDevice
                self.device = SolarSentryEdgeDevice(device_id="esp32-sim-agent9")
            except ImportError:
                # Fallback minimal mock if path resolution differs
                self.device = None
        else:
            self.device = edge_device

        self._connected = True
        self.injected_timeout: bool = False
        self.injected_failure: Optional[str] = None
        self.injected_latency_sec: float = 0.0

    def is_connected(self) -> bool:
        return self._connected

    def set_connected(self, connected: bool) -> None:
        self._connected = connected

    def inject_timeout(self, enable: bool = True) -> None:
        """Forces next command(s) to simulate a response timeout."""
        self.injected_timeout = enable

    def inject_failure(self, error_type: Optional[str] = "EXECUTION_ERROR") -> None:
        """Forces next command to return an execution or safety failure."""
        self.injected_failure = error_type

    def dispatch(self, command: Command, timeout_sec: float = 5.0) -> CommandResult:
        """Dispatches command to simulated edge device with timeout enforcement."""
        if not self._connected:
            return CommandResult(
                command_id=command.command_id,
                status="EXECUTION_ERROR",
                message="Dispatcher comms channel offline (Edge device unreachable)",
                current_pan=90,
                current_tilt=0,
                current_state="SAFE",
            )

        if self.injected_timeout:
            logger.warning(f"Simulated timeout on command {command.command_id}")
            time.sleep(min(0.05, timeout_sec))  # Fast mock sleep for tests
            return CommandResult(
                command_id=command.command_id,
                status="EXECUTION_ERROR",
                message=f"Command execution timed out after {timeout_sec:.1f}s",
                current_pan=90,
                current_tilt=0,
                current_state="DEGRADED",
            )

        if self.injected_failure:
            status = self.injected_failure
            msg = f"Injected mock fault: {status}"
            self.injected_failure = None
            return CommandResult(
                command_id=command.command_id,
                status=status,
                message=msg,
                current_pan=90,
                current_tilt=0,
                current_state="FAULT",
            )

        if self.device is not None:
            cmd_dict = command.to_dict()
            # Fast-forward simulator physical steps so servo reaches destination
            raw_res = self.device.execute_command(cmd_dict)
            for _ in range(5):
                self.device.update(dt=0.5)
            # Re-fetch post-move telemetry state
            telem = self.device.generate_telemetry()
            return CommandResult(
                command_id=raw_res.get("command_id", command.command_id),
                status=raw_res.get("status", "SUCCESS"),
                message=raw_res.get("message", ""),
                current_pan=telem.get("pan", raw_res.get("current_pan", 90)),
                current_tilt=telem.get("tilt", raw_res.get("current_tilt", 0)),
                current_state=telem.get("state", raw_res.get("current_state", "STANDBY")),
            )

        # Fallback pure software mock
        pan = command.pan if command.pan is not None else 90
        tilt = command.tilt if command.tilt is not None else 80
        return CommandResult(
            command_id=command.command_id,
            status="SUCCESS",
            message="Mock simulated command success",
            current_pan=pan,
            current_tilt=tilt,
            current_state="OBSERVE" if command.command == ActionVerb.OBSERVE else "STANDBY",
        )


class HttpCommandDispatcher(CommandDispatcherInterface):
    """Production HTTP REST client dispatching commands to the physical ESP32."""

    def __init__(self, endpoint_url: str = "http://192.168.1.100/command"):
        self.endpoint_url = endpoint_url
        self._connected = True

    def is_connected(self) -> bool:
        return self._connected

    def dispatch(self, command: Command, timeout_sec: float = 5.0) -> CommandResult:
        import urllib.request
        import urllib.error

        payload = json.dumps(command.to_dict()).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return CommandResult.from_dict(data)
        except urllib.error.HTTPError as e:
            return CommandResult(
                command_id=command.command_id,
                status="EXECUTION_ERROR",
                message=f"HTTP Error {e.code}: {e.reason}",
            )
        except urllib.error.URLError as e:
            self._connected = False
            return CommandResult(
                command_id=command.command_id,
                status="EXECUTION_ERROR",
                message=f"Network comms error: {e.reason}",
            )
        except Exception as e:
            return CommandResult(
                command_id=command.command_id,
                status="EXECUTION_ERROR",
                message=f"Unexpected dispatch error: {str(e)}",
            )
