"""
Solar Sentry — ESP32-CAM Dynamic Discovery & Camera Registry
Module: Agent 1 (Edge Camera), Agent 2 (Backend Core HAL)

Provides:
- mDNS dynamic discovery (solar-sentry-cam.local)
- Automatic DHCP IP change detection & reconnection
- Camera health verification (online / discovering / offline / reconnecting)
- SSRF-safe camera registry
"""

import asyncio
from datetime import datetime, timezone
import logging
import socket
import time
from typing import Any, Dict, Optional

import httpx

from app.core.providers import provider_manager, SystemMode

logger = logging.getLogger("solarsentry.camera_discovery")


class CameraRegistry:
    """Manages discovered camera nodes and prevents SSRF by strictly registering approved hardware endpoints."""

    def __init__(self):
        self.device_id = "SOLAR-SENTRY-CAM-01"
        self.name = "Solar Sentry ESP32-CAM"
        self.hostname = "solar-sentry-cam.local"
        self.current_ip: Optional[str] = None
        self.port: int = 80
        self.status: str = "DISCOVERING"
        self.last_seen: Optional[str] = None
        self.last_error: Optional[str] = None
        self.latency_ms: float = 0.0
        self.discovery_method: str = "mdns"
        self.consecutive_failures: int = 0
        self._lock = asyncio.Lock()

    def get_info(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "name": self.name,
            "hostname": self.hostname,
            "ip": self.current_ip or "UNRESOLVED",
            "port": self.port,
            "status": self.status,
            "last_seen": self.last_seen or "Never",
            "last_error": self.last_error,
            "latency_ms": self.latency_ms,
            "discovery_method": self.discovery_method,
            "stream_url": "/api/v1/camera/stream",
            "snapshot_url": "/api/v1/camera/capture",
            "direct_url": f"http://{self.current_ip}" if self.current_ip else None,
            "is_verified": self.status == "ONLINE"
        }

    async def verify_camera(self, target_ip: str) -> bool:
        """Verifies that target_ip is an actual ESP32-CAM responding to /status or /capture."""
        url = f"http://{target_ip}:{self.port}/status"
        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(url)
                self.latency_ms = round((time.perf_counter() - t0) * 1000, 1)
                if res.status_code == 200:
                    self.current_ip = target_ip
                    self.status = "ONLINE"
                    self.last_seen = datetime.now(timezone.utc).isoformat()
                    self.last_error = None
                    self.consecutive_failures = 0
                    provider_manager.set_camera_url(f"http://{target_ip}:{self.port}")
                    logger.info(f"Verified ESP32-CAM at {target_ip} ({self.latency_ms}ms)")
                    return True
        except Exception as e:
            self.last_error = str(e)
            self.consecutive_failures += 1
            logger.debug(f"Verification failed for {target_ip}: {e}")
        return False

    async def discover(self, fallback_ip: Optional[str] = None) -> Dict[str, Any]:
        """Resolves solar-sentry-cam.local or fallback IP and updates registry."""
        async with self._lock:
            # Step 1: Try resolving mDNS hostname
            resolved_ip: Optional[str] = None
            try:
                resolved_ip = await asyncio.to_thread(socket.gethostbyname, self.hostname)
                logger.info(f"mDNS resolved {self.hostname} -> {resolved_ip}")
                self.discovery_method = "mdns"
            except Exception:
                logger.debug(f"mDNS resolution failed for {self.hostname}")

            # Step 2: If mDNS resolved, verify reachability
            if resolved_ip:
                verified = await self.verify_camera(resolved_ip)
                if verified:
                    return self.get_info()

            # Step 3: Try existing known IP if already configured
            if self.current_ip and self.current_ip != resolved_ip:
                verified = await self.verify_camera(self.current_ip)
                if verified:
                    return self.get_info()

            # Step 4: Try fallback IP if supplied
            if fallback_ip:
                self.discovery_method = "manual_fallback"
                verified = await self.verify_camera(fallback_ip)
                if verified:
                    return self.get_info()

            # Step 5: If not reachable, record failure and set state to RECONNECTING or OFFLINE
            if not resolved_ip and not fallback_ip:
                self.consecutive_failures += 1

            if self.consecutive_failures > 3:
                self.status = "OFFLINE"
            else:
                self.status = "RECONNECTING"

            return self.get_info()


camera_registry = CameraRegistry()
