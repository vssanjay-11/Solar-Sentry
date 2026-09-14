import sys
import os
import pytest
from fastapi.testclient import TestClient

# Ensure backend and root are in python path
sys.path.insert(0, os.path.abspath("backend"))
sys.path.insert(0, os.path.abspath("."))

from app.main import app
from app.core.providers import provider_manager


@pytest.fixture
def client():
    # Force DEMO mode for reliable testing
    provider_manager.set_mode("DEMO")
    with TestClient(app) as test_client:
        yield test_client


def test_system_status(client):
    response = client.get("/api/v1/system/status")
    assert response.status_code == 200
    data = response.json()
    assert data["project"] == "Solar Sentry"
    assert data["mode"] == "DEMO"
    assert "status" in data


def test_system_mode_toggle(client):
    # Set to HARDWARE mode
    response = client.post("/api/v1/system/mode", json={"mode": "HARDWARE"})
    assert response.status_code == 200
    assert response.json()["mode"] == "HARDWARE"

    # Status in HARDWARE mode when physical device is offline
    status_resp = client.get("/api/v1/system/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["mode"] == "HARDWARE"

    # Revert to DEMO mode
    response = client.post("/api/v1/system/mode", json={"mode": "DEMO"})
    assert response.status_code == 200
    assert response.json()["mode"] == "DEMO"


def test_telemetry_live(client):
    response = client.get("/api/v1/telemetry/live")
    assert response.status_code == 200
    data = response.json()
    assert "metrics" in data or "temperature" in data


def test_camera_capture(client):
    response = client.post("/api/v1/camera/capture?condition=clear")
    assert response.status_code == 200
    data = response.json()
    assert "image_base64" in data
    assert "quality_score" in data
    assert "metadata" in data
    assert data["metadata"]["condition"] == "clear"


def test_camera_calibrate(client):
    # First capture an image to populate last frame
    client.post("/api/v1/camera/capture?condition=clear")

    calib_params = {
        "brightness": 10,
        "contrast": 1.2,
        "gamma": 1.0,
        "clahe_enabled": True,
        "clahe_clip_limit": 2.5,
        "unsharp_mask": True,
        "unsharp_strength": 1.0
    }
    response = client.post("/api/v1/camera/calibrate", json=calib_params)
    assert response.status_code == 200
    data = response.json()
    assert "processed_base64" in data
    assert "raw_base64" in data
    assert "scorecard" in data
    assert data["scorecard"]["composite_score"] >= 0


def test_device_command(client):
    cmd = {
        "command": "SET_SERVO",
        "pan": 180,
        "tilt": 45
    }
    response = client.post("/api/v1/device/command", json=cmd)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("QUEUED", "DISPATCHED", "SUCCESS")
