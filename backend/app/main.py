"""
===============================================================
SOLAR SENTRY
Cognitive Solar Observatory Mission Control Backend & API Server
===============================================================
Module: Agent 2 (Backend API & Communication)
Project Name: Solar Sentry
"""

import os
import sys
# Ensure repository root and backend directory are always in sys.path
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)
_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import json
from typing import List, Set


from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_v1_router
from app.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import logger
from app.core.providers import provider_manager, SystemMode
from app.services.observatory_service import observatory_service
from backend.database import init_db


class WebSocketManager:
    """Manages connected frontend mission control dashboard clients and broadcasts telemetry."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
        logger.info(f"Dashboard client connected. Active WebSocket sessions: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self.active_connections.discard(websocket)
        logger.info(f"Dashboard client disconnected. Remaining WebSocket sessions: {len(self.active_connections)}")

    async def broadcast(self, channel: str, data: dict) -> None:
        if not self.active_connections:
            return

        payload = json.dumps({"channel": channel, "data": data})
        stale: List[WebSocket] = []

        async with self._lock:
            for ws in list(self.active_connections):
                try:
                    await ws.send_text(payload)
                except Exception:
                    stale.append(ws)

            for ws in stale:
                self.active_connections.discard(ws)


ws_manager = WebSocketManager()


async def background_telemetry_broadcaster():
    """Periodically fetches telemetry and AI state and broadcasts to active WebSocket clients at 1 Hz."""
    logger.info("Solar Sentry background telemetry broadcaster loop started.")
    while True:
        try:
            # 1. Fetch current telemetry from active provider (Demo simulator or physical ESP32)
            telem = await provider_manager.sensor_provider.get_telemetry()
            telem_dict = telem.model_dump()

            # 2. Update central observatory state
            await observatory_service.update_from_telemetry(telem)

            # 3. Broadcast telemetry frame
            await ws_manager.broadcast("telemetry", telem_dict)

            # 4. Compute and broadcast AI state
            ors_score = 88 if telem.state != "SUSPEND" else 15
            ai_data = {
                "decision": telem.state.value if telem.state.value in ["OBSERVE", "WAIT", "SCAN", "SUSPEND", "SAFE"] else "STANDBY",
                "confidence": 0.94 if telem.state != "SUSPEND" else 0.99,
                "ors_score": ors_score,
                "ors_factors": {
                    "solar_elevation": 92 if telem.state != "SUSPEND" else 10,
                    "atmospheric_seeing": 85,
                    "cloud_transparency": 90 if telem.state != "SUSPEND" else 20,
                    "sensor_health": telem.health,
                    "tracking_stability": 95 if telem.state != "SUSPEND" else 0
                },
                "reasoning_trace": [
                    f"System operating in mode [{provider_manager.mode.value}]",
                    f"Solar disk tracked at (Pan: {telem.pan}°, Tilt: {telem.tilt}°)",
                    f"Ambient illuminance: {telem.lux:,.0f} Lux",
                    "Rain sensor dry, optical envelope nominal" if not telem.rain_detected else "Precipitation interlock active, auto-stowed"
                ],
                "predictions": {
                    "horizon_15m": {"score": ors_score - 2, "trend": "STABLE", "confidence_lower": 78, "confidence_upper": 88},
                    "horizon_30m": {"score": ors_score - 5, "trend": "STABLE", "confidence_lower": 72, "confidence_upper": 84},
                    "horizon_60m": {"score": ors_score - 10, "trend": "UNCERTAIN", "confidence_lower": 60, "confidence_upper": 80}
                },
                "health_breakdown": {
                    "overall": telem.health,
                    "edge": 100 if telem.health > 80 else telem.health,
                    "optical": 95,
                    "comms": 99,
                    "anomaly_score": 0.04 if telem.health > 80 else 0.45
                }
            }
            await ws_manager.broadcast("ai_state", ai_data)

            # 5. Broadcast alerts if emergency rain or health degradation
            if telem.rain_detected:
                await ws_manager.broadcast("alerts", {
                    "alert_id": f"alt-rain-{int(datetime.now(timezone.utc).timestamp())}",
                    "severity": "CRITICAL",
                    "type": "RAIN_EMERGENCY_OVERRIDE",
                    "message": f"Precipitation detected (ADC {telem.rain_raw}). Actuators auto-stowed to (90, 0). State locked to SUSPEND.",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "acknowledged": False
                })

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in telemetry broadcast cycle: {e}")

        await asyncio.sleep(1.0)


async def camera_discovery_loop():
    """Periodically discovers ESP32-CAM via mDNS in HARDWARE mode when offline."""
    from app.services.camera_discovery import camera_registry
    logger.info("Solar Sentry background ESP32-CAM discovery loop started.")
    while True:
        try:
            if provider_manager.mode == SystemMode.HARDWARE and camera_registry.status != "ONLINE":
                await camera_registry.discover()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.debug(f"Camera discovery cycle notice: {e}")
        await asyncio.sleep(5.0)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan manager initializing persistence database, telemetry broadcaster, camera discovery, and serial hardware reader."""
    logger.info("Initializing Solar Sentry persistence layer...")
    init_db()
    logger.info("Solar Sentry persistence layer initialized.")

    broadcaster_task = asyncio.create_task(background_telemetry_broadcaster())
    discovery_task = asyncio.create_task(camera_discovery_loop())

    # Start USB Serial hardware reader if enabled
    serial_task = None
    if settings.ENABLE_SERIAL_READER:
        from app.services.serial_reader import serial_reader
        serial_task = serial_reader.start()

    yield

    broadcaster_task.cancel()
    discovery_task.cancel()
    if serial_task:
        from app.services.serial_reader import serial_reader
        serial_reader.stop()

    try:
        tasks_to_cancel = [t for t in [broadcaster_task, discovery_task, serial_task] if t is not None]
        await asyncio.gather(*tasks_to_cancel, return_exceptions=True)
    except Exception:
        pass
    logger.info("Solar Sentry server shutdown complete.")


app = FastAPI(
    title="Solar Sentry",
    description="Autonomous Cognitive Solar Observatory Mission Control & Intelligence System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Register custom exception handlers
register_exception_handlers(app)

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Master API v1 Router
app.include_router(api_v1_router, prefix=settings.API_V1_STR)


@app.get("/", summary="System Root Health & Info")
async def root_info():
    return {
        "project": "Solar Sentry",
        "service": "Mission Control Backend API",
        "version": "1.0.0",
        "system_mode": provider_manager.mode.value,
        "docs_url": "/docs",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "OPERATIONAL"
    }


@app.get("/health", summary="Basic service health probe")
async def health_check():
    return JSONResponse(
        status_code=200,
        content={"status": "healthy", "project": "Solar Sentry", "timestamp": datetime.now(timezone.utc).isoformat()}
    )


@app.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    """
    Bidirectional WebSocket endpoint for live mission control telemetry streaming.
    Clients can subscribe to channels ['telemetry', 'ai_state', 'alerts', 'vision'].
    """
    await ws_manager.connect(websocket)
    try:
        while True:
            # Listen for inbound commands or subscription messages
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                action = msg.get("action")
                if action == "ping":
                    await websocket.send_text(json.dumps({"action": "pong", "timestamp": datetime.now(timezone.utc).isoformat()}))
                elif action == "subscribe":
                    logger.info(f"Client subscribed to channels: {msg.get('channels', [])}")
            except Exception:
                pass
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WebSocket session error: {e}")
        await ws_manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
