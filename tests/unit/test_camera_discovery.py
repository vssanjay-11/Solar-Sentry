"""
Unit tests for ESP32-CAM dynamic discovery, camera registry, and dynamic IP recovery.
Module: Solar Sentry Agent 1 / Agent 2 HAL
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

try:
    from app.services.camera_discovery import CameraRegistry
except ImportError:
    from backend.app.services.camera_discovery import CameraRegistry


@pytest.fixture
def registry():
    return CameraRegistry()


def test_camera_registry_initial_state(registry):
    info = registry.get_info()
    assert info["device_id"] == "SOLAR-SENTRY-CAM-01"
    assert info["hostname"] == "solar-sentry-cam.local"
    assert info["status"] == "DISCOVERING"
    assert info["stream_url"] == "/api/v1/camera/stream"
    assert info["is_verified"] is False


def test_camera_registry_verify_success(registry):
    async def run():
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            verified = await registry.verify_camera("192.168.1.50")
            assert verified is True
            assert registry.status == "ONLINE"
            assert registry.current_ip == "192.168.1.50"
            assert registry.consecutive_failures == 0
            assert registry.last_seen is not None

    asyncio.run(run())


def test_camera_registry_verify_failure(registry):
    async def run():
        with patch("httpx.AsyncClient.get", side_effect=Exception("Connection refused")):
            verified = await registry.verify_camera("192.168.1.99")
            assert verified is False
            assert registry.consecutive_failures == 1
            assert registry.last_error is not None

    asyncio.run(run())


def test_camera_discovery_mdns_success(registry):
    async def run():
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("socket.gethostbyname", return_value="192.168.1.120"), \
             patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):

            info = await registry.discover()
            assert info["status"] == "ONLINE"
            assert info["ip"] == "192.168.1.120"
            assert info["discovery_method"] == "mdns"
            assert info["is_verified"] is True

    asyncio.run(run())


def test_camera_dynamic_ip_change_recovery(registry):
    """
    Simulate camera rebooting and DHCP reassigning IP from 192.168.1.50 to 192.168.1.73.
    System should dynamically recover without code changes.
    """
    async def run():
        mock_response = MagicMock()
        mock_response.status_code = 200

        # Step 1: Camera initial discovery at IP 192.168.1.50
        with patch("socket.gethostbyname", return_value="192.168.1.50"), \
             patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
            info1 = await registry.discover()
            assert info1["ip"] == "192.168.1.50"
            assert info1["status"] == "ONLINE"

        # Step 2: Camera reboots, DHCP assigns 192.168.1.73, mDNS resolves new IP
        with patch("socket.gethostbyname", return_value="192.168.1.73"), \
             patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
            info2 = await registry.discover()
            assert info2["ip"] == "192.168.1.73"
            assert info2["status"] == "ONLINE"
            assert info2["hostname"] == "solar-sentry-cam.local"

    asyncio.run(run())


def test_camera_discovery_fallback_ip(registry):
    """If mDNS fails, verify fallback IP succeeds."""
    async def run():
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("socket.gethostbyname", side_effect=Exception("mDNS timeout")), \
             patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):

            info = await registry.discover(fallback_ip="192.168.1.150")
            assert info["status"] == "ONLINE"
            assert info["ip"] == "192.168.1.150"
            assert info["discovery_method"] == "manual_fallback"

    asyncio.run(run())


def test_camera_repeated_failures_trigger_offline(registry):
    async def run():
        with patch("socket.gethostbyname", side_effect=Exception("Unresolved")), \
             patch("httpx.AsyncClient.get", side_effect=Exception("Timeout")):

            for _ in range(4):
                await registry.discover()

            info = registry.get_info()
            assert info["status"] == "OFFLINE"
            assert info["is_verified"] is False

    asyncio.run(run())
