"""
Solar Sentry — API v1 Master Router Aggregator
Combines all domain routers for telemetry, actuators, vision, intelligence, missions,
digital twin simulation, and camera calibration.
"""

from fastapi import APIRouter

from app.api.v1.endpoints.telemetry import router as telemetry_router
from app.api.v1.endpoints.commands import router as commands_router
from app.api.v1.endpoints.devices import router as devices_router
from app.api.v1.endpoints.images import router as images_router
from app.api.v1.endpoints.system import router as system_router
from app.api.v1.endpoints.camera import router as camera_router
from app.api.v1.endpoints.intelligence import router as intelligence_router
from app.api.v1.endpoints.missions import router as missions_router
from app.api.v1.endpoints.simulation import router as simulation_router
from app.api.v1.endpoints.alerts import router as alerts_router
from app.api.v1.endpoints.replay import router as replay_router
from app.api.v1.endpoints.vision import router as vision_router


api_v1_router = APIRouter()

api_v1_router.include_router(system_router)
api_v1_router.include_router(telemetry_router)
api_v1_router.include_router(commands_router)
api_v1_router.include_router(devices_router)
api_v1_router.include_router(images_router)
api_v1_router.include_router(camera_router)
api_v1_router.include_router(intelligence_router)
api_v1_router.include_router(missions_router)
api_v1_router.include_router(simulation_router)
api_v1_router.include_router(alerts_router)
api_v1_router.include_router(replay_router)
api_v1_router.include_router(vision_router)
