"""
Solar Sentry - Observation Record Model
Authoritative observation session records linked to missions, devices, and images.
"""

from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import String, Integer, Float, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.core import Base, UTCDateTime, PortableJSON


class Observation(Base):
    """Authoritative scientific observation session record."""
    __tablename__ = "observations"

    observation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    mission_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        ForeignKey("missions.mission_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    device_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("devices.device_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    image_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        ForeignKey("image_metadata.image_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, index=True)
    start_time: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    end_time: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, nullable=True)
    pan_angle: Mapped[int] = mapped_column(Integer, nullable=False, default=90)
    tilt_angle: Mapped[int] = mapped_column(Integer, nullable=False, default=45)
    solar_elevation: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    solar_azimuth: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ambient_lux: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cloud_cover_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="COMPLETED")
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(PortableJSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    mission: Mapped[Optional["Mission"]] = relationship("Mission", back_populates="observations")
    device: Mapped["Device"] = relationship("Device", back_populates="observations")
    image: Mapped[Optional["ImageMetadata"]] = relationship("ImageMetadata", back_populates="observations")
    vision_analyses: Mapped[List["VisionAnalysis"]] = relationship("VisionAnalysis", back_populates="observation")
    verifications: Mapped[List["VerificationRecord"]] = relationship("VerificationRecord", back_populates="observation")

    __table_args__ = (
        Index("ix_observations_device_timestamp", "device_id", "timestamp"),
        Index("ix_observations_status", "status"),
        Index("ix_observations_quality", "quality_score"),
    )
