"""
Solar Sentry — Mission Session Replay API Endpoints
Module: Agent 10 (Digital Twin, Mission Memory & Replay)
"""

from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/replay", tags=["Mission Session Replay"])

REPLAY_SESSIONS = [
    {
        "session_id": "ses-20260913-001",
        "title": "Clear Sky Optimal Solar Flare Tracking",
        "date": "2026-09-13",
        "duration_seconds": 180,
        "frame_count": 60,
        "primary_scenario": "CLEAR_DAY",
        "outcome": "SUCCESS"
    },
    {
        "session_id": "ses-20260913-002",
        "title": "Cloud Transit & Active Gimbal Recovery",
        "date": "2026-09-13",
        "duration_seconds": 120,
        "frame_count": 40,
        "primary_scenario": "CLOUD_TRANSIT",
        "outcome": "SUCCESS"
    },
    {
        "session_id": "ses-20260913-003",
        "title": "Precipitation Emergency Interlock Slew",
        "date": "2026-09-13",
        "duration_seconds": 90,
        "frame_count": 30,
        "primary_scenario": "RAIN_APPROACHING",
        "outcome": "EMERGENCY_PARK"
    }
]


@router.get("/sessions", summary="List historical mission sessions available for replay")
async def list_replay_sessions() -> List[Dict[str, Any]]:
    return REPLAY_SESSIONS


@router.get("/{session_id}", summary="Get full recorded telemetry and decision frame sequence")
async def get_replay_session_frames(session_id: str) -> Dict[str, Any]:
    matched = next((s for s in REPLAY_SESSIONS if s["session_id"] == session_id), None)
    if not matched:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Replay session '{session_id}' not found."
        )

    # Generate synthetic frames
    frames = []
    for i in range(matched["frame_count"]):
        pan = 90 + int(i * 0.5)
        tilt = 45 + int(i * 0.2)
        frames.append({
            "frame_index": i,
            "timestamp": f"2026-09-13T11:{i // 60:02d}:{i % 60:02d}Z",
            "telemetry": {
                "temperature": 26.5 + 0.1 * i,
                "humidity": 38.0 + 0.2 * i,
                "pressure": 1013.25,
                "lux": 52000.0 - 100 * i,
                "pan": pan,
                "tilt": tilt,
                "state": "OBSERVE"
            },
            "decision": "OBSERVE",
            "decision_confidence": 0.94,
            "ors_score": max(50, 92 - i // 2),
            "vision": {
                "solar_disk_detected": True,
                "center_x": 320,
                "center_y": 240,
                "radius_px": 142
            }
        })

    return {
        "session": matched,
        "frames": frames
    }
