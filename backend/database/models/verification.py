"""
Solar Sentry - Verification Records Model
Closed-loop active perception verification records (Agent 9).
Adheres strictly to docs/contracts/MissionResult.json (verification_summary).
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Float, Boolean, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.core import Base, UTCDateTime, PortableJSON


class VerificationRecord(Base):
    """Authoritative closed-loop verification record after physical action execution."""
    __tablename__ = "verification_records"

    verification_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    action_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        ForeignKey("mission_actions.action_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    observation_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        ForeignKey("observations.observation_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="SUCCESS",
        index=True,
    )  # SUCCESS, FAILED, SKIPPED, VERIFIED_OPTIMAL, VERIFIED_SUBOPTIMAL
    pointing_error_degrees: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    optical_quality_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    quality_before: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0.0 - 1.0
    quality_after: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0.0 - 1.0
    delta_quality: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    converged: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True, default=True)
    verification_metrics_json: Mapped[Optional[dict]] = mapped_column(PortableJSON, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    action: Mapped[Optional["MissionAction"]] = relationship("MissionAction", back_populates="verifications")
    observation: Mapped[Optional["Observation"]] = relationship("Observation", back_populates="verifications")

    __table_args__ = (
        Index("ix_verification_status_time", "status", "timestamp"),
    )
