"""
Solar Sentry - Image Metadata Model
Authoritative metadata for captured optical solar disk and sky frames.
"""

from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import String, Integer, BigInteger, Float, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.core import Base, UTCDateTime, PortableJSON


class ImageMetadata(Base):
    """Authoritative image capture metadata emitted by optical nodes (e.g. ESP32-CAM)."""
    __tablename__ = "image_metadata"

    image_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    device_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("devices.device_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    storage_uri: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    format: Mapped[str] = mapped_column(String(16), nullable=False, default="JPEG")
    width: Mapped[int] = mapped_column(Integer, nullable=False, default=640)
    height: Mapped[int] = mapped_column(Integer, nullable=False, default=480)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), nullable=False, default=0)
    exposure_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gain: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pan_angle: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tilt_angle: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    checksum_sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(PortableJSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    device: Mapped["Device"] = relationship("Device", back_populates="images")
    observations: Mapped[List["Observation"]] = relationship("Observation", back_populates="image")
    analyses: Mapped[List["VisionAnalysis"]] = relationship(
        "VisionAnalysis", back_populates="image", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_images_device_timestamp", "device_id", "timestamp"),
    )
