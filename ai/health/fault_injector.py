"""Simulated failure injection testbed for Solar Sentry.

Agent 7 Ownership.
Allows simulation of edge failures, hardware degradation, sensor conflicts,
and communication stalls for testing, validation, and digital twin simulation.
"""

from __future__ import annotations

import copy
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta


class FaultInjector:
    """Injects synthetic faults and degradation into telemetry payloads."""

    @staticmethod
    def inject_dht22_disconnected(telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """Simulates physical disconnection of the DHT22 sensor (GPIO4)."""
        t = copy.deepcopy(telemetry)
        t["temperature"] = -999.0
        t["humidity"] = -999.0
        if "sensor_status" in t:
            t["sensor_status"]["dht22"] = False
        return t

    @staticmethod
    def inject_bmp280_stale(
        telemetry: Dict[str, Any],
        frozen_pressure: float = 1013.25
    ) -> Dict[str, Any]:
        """Simulates BMP280 I2C lockup where pressure is frozen bit-for-bit invariant."""
        t = copy.deepcopy(telemetry)
        t["pressure"] = frozen_pressure
        return t

    @staticmethod
    def inject_rain_sensor_stuck(
        telemetry: Dict[str, Any],
        stuck_wet: bool = True
    ) -> Dict[str, Any]:
        """Simulates rain sensor stuck condition (e.g. bird dropping short or corrosion)."""
        t = copy.deepcopy(telemetry)
        if stuck_wet:
            t["rain_raw"] = 450
            t["rain_detected"] = True
            # Keep humidity low to create physical cross-sensor conflict
            t["humidity"] = 18.5
            t["lux"] = 72000.0
        else:
            t["rain_raw"] = 3900
            t["rain_detected"] = False
        return t

    @staticmethod
    def inject_communication_interruption(
        telemetry: Dict[str, Any],
        delay_seconds: float = 35.0
    ) -> Dict[str, Any]:
        """Simulates communication latency or heartbeat interruption."""
        t = copy.deepcopy(telemetry)
        stale_time = datetime.now(timezone.utc) - timedelta(seconds=delay_seconds)
        t["timestamp"] = stale_time.isoformat()
        t["wifi_rssi"] = -94
        return t

    @staticmethod
    def inject_inconsistent_temperatures(
        telemetry: Dict[str, Any],
        dht_temp: float = 42.0,
        bmp_temp: float = 23.0
    ) -> Tuple[Dict[str, Any], float]:
        """Simulates divergent temperature readings between DHT22 and BMP280."""
        t = copy.deepcopy(telemetry)
        t["temperature"] = dht_temp
        return t, bmp_temp

    @staticmethod
    def inject_humidity_drift(
        telemetry: Dict[str, Any],
        drift_offset_pct: float = 22.0
    ) -> Dict[str, Any]:
        """Simulates progressive sensor calibration decay (upward humidity drift)."""
        t = copy.deepcopy(telemetry)
        base_h = float(t.get("humidity", 45.0))
        t["humidity"] = round(min(100.0, base_h + drift_offset_pct), 1)
        return t

    @staticmethod
    def inject_actuator_stall(
        telemetry: Dict[str, Any],
        frozen_pan: int = 45
    ) -> Dict[str, Any]:
        """Simulates mechanical gear jam on pan servo."""
        t = copy.deepcopy(telemetry)
        t["pan"] = frozen_pan
        return t
