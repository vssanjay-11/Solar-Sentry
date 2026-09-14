"""
Solar Sentry - Vision Analysis Repository
Data access operations for solar disk detection, sunspot count, limb darkening, and cloud obstruction inferences.
"""

from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.models.vision import VisionAnalysis
from backend.database.repositories.base import BaseRepository


class VisionAnalysisRepository(BaseRepository[VisionAnalysis]):
    """Repository managing computer vision inference results."""

    def __init__(self, session: Session):
        super().__init__(VisionAnalysis, session)

    def record_analysis(
        self,
        analysis_id: str,
        image_id: str,
        model_version: str,
        analyzed_at: Optional[datetime] = None,
        observation_id: Optional[str] = None,
        solar_disk_detected: bool = False,
        disk_center_x: Optional[float] = None,
        disk_center_y: Optional[float] = None,
        disk_radius_px: Optional[float] = None,
        sunspot_count: int = 0,
        limb_darkening_score: Optional[float] = None,
        cloud_obstruction_pct: Optional[float] = None,
        flare_candidate: bool = False,
        confidence_score: float = 1.0,
        features_json: Optional[dict] = None,
    ) -> VisionAnalysis:
        """Stores a computer vision analysis result."""
        analysis = VisionAnalysis(
            analysis_id=analysis_id,
            image_id=image_id,
            observation_id=observation_id,
            analyzed_at=analyzed_at or datetime.now(timezone.utc),
            model_version=model_version,
            solar_disk_detected=solar_disk_detected,
            disk_center_x=disk_center_x,
            disk_center_y=disk_center_y,
            disk_radius_px=disk_radius_px,
            sunspot_count=sunspot_count,
            limb_darkening_score=limb_darkening_score,
            cloud_obstruction_pct=cloud_obstruction_pct,
            flare_candidate=flare_candidate,
            confidence_score=confidence_score,
            features_json=features_json,
            created_at=datetime.now(timezone.utc),
        )
        return self.create(analysis)

    def get_by_image_id(self, image_id: str) -> List[VisionAnalysis]:
        """Returns all analysis passes executed on a specific image."""
        stmt = (
            select(VisionAnalysis)
            .where(VisionAnalysis.image_id == image_id)
            .order_by(VisionAnalysis.analyzed_at.desc())
        )
        return list(self.session.scalars(stmt).all())

    def list_recent(self, limit: int = 50) -> List[VisionAnalysis]:
        """Returns the most recent vision analysis results."""
        stmt = select(VisionAnalysis).order_by(VisionAnalysis.analyzed_at.desc()).limit(limit)
        return list(self.session.scalars(stmt).all())

    def list_sunspot_detections(self, min_sunspots: int = 1, limit: int = 50) -> List[VisionAnalysis]:
        """Returns solar images where sunspots were identified."""
        stmt = (
            select(VisionAnalysis)
            .where(VisionAnalysis.sunspot_count >= min_sunspots)
            .order_by(VisionAnalysis.analyzed_at.desc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())
