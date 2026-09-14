"""
Solar Sentry — Anomaly & Safety Alerts API Endpoints
Module: Agent 7 (Sensor Fusion & Health Anomaly AI)
"""

from datetime import datetime, timezone
from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, status


router = APIRouter(prefix="/alerts", tags=["Anomaly & Safety Alerts"])

# In-memory active alerts
_active_alerts: List[Dict[str, Any]] = [
    {
        "alert_id": "alt-init-001",
        "severity": "INFO",
        "type": "SYSTEM_BOOT",
        "message": "Solar Sentry Observatory initialized in nominal standby state.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "acknowledged": False
    }
]


@router.get("", summary="List active anomaly and safety alerts")
async def list_alerts() -> List[Dict[str, Any]]:
    return _active_alerts


@router.post("/{alert_id}/ack", summary="Acknowledge and dismiss an anomaly alert")
async def acknowledge_alert(alert_id: str) -> Dict[str, Any]:
    global _active_alerts
    found = False
    for a in _active_alerts:
        if a["alert_id"] == alert_id:
            a["acknowledged"] = True
            found = True
            break

    # Also prune acknowledged
    _active_alerts = [a for a in _active_alerts if not a["acknowledged"]]

    return {"status": "ACKNOWLEDGED", "alert_id": alert_id}
