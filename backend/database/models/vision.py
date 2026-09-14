"""
Solar Sentry - Vision Analysis Results Model
Computer vision inferences: solar disk localization, sunspot counting, limb-darkening, and cloud coverage.
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Integer, Float, Boolean, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.core import Base, UTCDateTime, PortableJSON


class VisionAnalysis(Base):
    """Authoritative computer vision analysis result for captured solar imagery."""
    __tablename__ = "vision_analyses"

    analysis_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    image_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("image_metadata.image_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    observation_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        ForeignKey("observations.observation_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    analyzed_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, index=True)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    solar_disk_detected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    disk_center_x: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    disk_center_y: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    disk_radius_px: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sunspot_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    limb_darkening_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cloud_obstruction_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    flare_candidate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    features_json: Mapped[Optional[dict]] = mapped_column(PortableJSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    image: Mapped["ImageMetadata"] = relationship("ImageMetadata", back_populates="analyses")
    observation: Mapped[Optional["Observation"]] = relationship("Observation", back_populates="vision_analyses")

    __table_args__ = (
        Index("ix_vision_sunspots", "sunspot_count"),
        Index("ix_vision_disk_detected", "solar_disk_detected"),
    )
