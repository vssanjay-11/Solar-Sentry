"""
Solar Sentry - Model Version Metadata Model
Registry of AI, vision, forecasting, and anomaly models deployed across the platform.
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Boolean, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.core import Base, UTCDateTime, PortableJSON


class ModelVersion(Base):
    """Authoritative metadata and provenance registry for AI model versions."""
    __tablename__ = "model_versions"

    model_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    subsystem: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # VISION, FORECASTING, ANOMALY, DECISION, TWIN
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    weights_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    architecture_desc: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    parameters_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    trained_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, nullable=True)
    metrics_json: Mapped[Optional[dict]] = mapped_column(PortableJSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_model_name_version"),
        Index("ix_models_subsystem_active", "subsystem", "is_active"),
    )
