"""
Solar Sentry - Repositories Package
Exports all authoritative repository interfaces for persistence and data access.
"""

from backend.database.repositories.base import BaseRepository
from backend.database.repositories.device_repo import DeviceRepository, SensorRepository
from backend.database.repositories.telemetry_repo import TelemetryRepository
from backend.database.repositories.observation_repo import ObservationRepository, ImageRepository
from backend.database.repositories.vision_repo import VisionAnalysisRepository
from backend.database.repositories.prediction_repo import EnvironmentPredictionRepository
from backend.database.repositories.health_repo import HealthRepository, AnomalyRepository
from backend.database.repositories.decision_repo import DecisionRepository
from backend.database.repositories.mission_repo import (
    MissionRepository,
    MissionActionRepository,
    MissionMemoryRepository,
)
from backend.database.repositories.command_repo import CommandRepository
from backend.database.repositories.verification_repo import VerificationRepository
from backend.database.repositories.model_repo import ModelVersionRepository

__all__ = [
    "BaseRepository",
    "DeviceRepository",
    "SensorRepository",
    "TelemetryRepository",
    "ObservationRepository",
    "ImageRepository",
    "VisionAnalysisRepository",
    "EnvironmentPredictionRepository",
    "HealthRepository",
    "AnomalyRepository",
    "DecisionRepository",
    "MissionRepository",
    "MissionActionRepository",
    "MissionMemoryRepository",
    "CommandRepository",
    "VerificationRepository",
    "ModelVersionRepository",
]
