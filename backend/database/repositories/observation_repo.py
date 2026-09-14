"""
Solar Sentry - Observation & Image Repositories
Data access operations for scientific observation sessions and optical image metadata.
"""

from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import select, and_
from sqlalchemy.orm import Session, selectinload

from backend.database.models.observation import Observation
from backend.database.models.image import ImageMetadata
from backend.database.repositories.base import BaseRepository


class ObservationRepository(BaseRepository[Observation]):
    """Repository managing observation session records."""

    def __init__(self, session: Session):
        super().__init__(Observation, session)

    def create_observation(
        self,
        observation_id: str,
        device_id: str,
        start_time: datetime,
        timestamp: Optional[datetime] = None,
        mission_id: Optional[str] = None,
        image_id: Optional[str] = None,
        end_time: Optional[datetime] = None,
        pan_angle: int = 90,
        tilt_angle: int = 45,
        solar_elevation: Optional[float] = None,
        solar_azimuth: Optional[float] = None,
        ambient_lux: Optional[float] = None,
        cloud_cover_pct: Optional[float] = None,
        status: str = "IN_PROGRESS",
        quality_score: Optional[float] = None,
        notes: Optional[str] = None,
        metadata_json: Optional[dict] = None,
    ) -> Observation:
        """Creates a new observation record."""
        obs = Observation(
            observation_id=observation_id,
            device_id=device_id,
            mission_id=mission_id,
            image_id=image_id,
            timestamp=timestamp or start_time,
            start_time=start_time,
            end_time=end_time,
            pan_angle=pan_angle,
            tilt_angle=tilt_angle,
            solar_elevation=solar_elevation,
            solar_azimuth=solar_azimuth,
            ambient_lux=ambient_lux,
            cloud_cover_pct=cloud_cover_pct,
            status=status,
            quality_score=quality_score,
            notes=notes,
            metadata_json=metadata_json,
            created_at=datetime.now(timezone.utc),
        )
        return self.create(obs)

    def complete_observation(
        self,
        observation_id: str,
        end_time: Optional[datetime] = None,
        quality_score: Optional[float] = None,
        status: str = "COMPLETED",
        notes: Optional[str] = None,
    ) -> Optional[Observation]:
        """Marks an observation session as completed with final metrics."""
        obs = self.get_by_id(observation_id)
        if obs:
            obs.end_time = end_time or datetime.now(timezone.utc)
            if quality_score is not None:
                obs.quality_score = quality_score
            obs.status = status
            if notes:
                obs.notes = notes
            self.update(obs)
        return obs

    def list_by_mission(self, mission_id: str) -> List[Observation]:
        """Returns all observation sessions linked to a specific mission."""
        stmt = (
            select(Observation)
            .where(Observation.mission_id == mission_id)
            .order_by(Observation.timestamp.asc())
        )
        return list(self.session.scalars(stmt).all())

    def list_recent(self, limit: int = 50) -> List[Observation]:
        """Returns the most recent observation sessions."""
        stmt = select(Observation).order_by(Observation.timestamp.desc()).limit(limit)
        return list(self.session.scalars(stmt).all())

    def get_with_analyses(self, observation_id: str) -> Optional[Observation]:
        """Fetches an observation with related vision analyses eagerly loaded."""
        stmt = (
            select(Observation)
            .where(Observation.observation_id == observation_id)
            .options(selectinload(Observation.vision_analyses))
        )
        return self.session.scalars(stmt).first()


class ImageRepository(BaseRepository[ImageMetadata]):
    """Repository managing captured image frames and optical metadata."""

    def __init__(self, session: Session):
        super().__init__(ImageMetadata, session)

    def record_image(
        self,
        image_id: str,
        device_id: str,
        timestamp: datetime,
        file_path: str,
        storage_uri: Optional[str] = None,
        format: str = "JPEG",
        width: int = 640,
        height: int = 480,
        file_size_bytes: int = 0,
        exposure_time_ms: Optional[float] = None,
        gain: Optional[float] = None,
        pan_angle: Optional[int] = None,
        tilt_angle: Optional[int] = None,
        checksum_sha256: Optional[str] = None,
        metadata_json: Optional[dict] = None,
    ) -> ImageMetadata:
        """Stores optical image metadata."""
        img = ImageMetadata(
            image_id=image_id,
            device_id=device_id,
            timestamp=timestamp,
            file_path=file_path,
            storage_uri=storage_uri,
            format=format,
            width=width,
            height=height,
            file_size_bytes=file_size_bytes,
            exposure_time_ms=exposure_time_ms,
            gain=gain,
            pan_angle=pan_angle,
            tilt_angle=tilt_angle,
            checksum_sha256=checksum_sha256,
            metadata_json=metadata_json,
            created_at=datetime.now(timezone.utc),
        )
        return self.create(img)

    def get_latest(self, device_id: str) -> Optional[ImageMetadata]:
        """Returns the most recent image captured by the device."""
        stmt = (
            select(ImageMetadata)
            .where(ImageMetadata.device_id == device_id)
            .order_by(ImageMetadata.timestamp.desc())
            .limit(1)
        )
        return self.session.scalars(stmt).first()

    def list_range(
        self,
        device_id: str,
        start_time: datetime,
        end_time: datetime,
        limit: int = 100,
    ) -> List[ImageMetadata]:
        """Returns images captured within [start_time, end_time]."""
        stmt = (
            select(ImageMetadata)
            .where(
                and_(
                    ImageMetadata.device_id == device_id,
                    ImageMetadata.timestamp >= start_time,
                    ImageMetadata.timestamp <= end_time,
                )
            )
            .order_by(ImageMetadata.timestamp.desc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())
