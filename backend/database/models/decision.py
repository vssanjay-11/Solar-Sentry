"""
Solar Sentry - Decision Records Model
Cognitive decision records and explainable AI (XAI) reasoning traces (Agent 8).
Adheres strictly to docs/contracts/CognitiveDecision.json.
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Float, Boolean, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.core import Base, UTCDateTime, PortableJSON


class DecisionRecord(Base):
    """Authoritative cognitive decision and explainable reasoning trace."""
    __tablename__ = "decision_records"

    decision_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    device_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("devices.device_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mission_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        ForeignKey("missions.mission_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, index=True)
    action_proposed: Mapped[str] = mapped_column(String(32), nullable=False)  # OBSERVE, WAIT, SUSPEND, SAFE, SCAN
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)  # 0.0 - 1.0
    risk: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # LOW, MODERATE, HIGH, CRITICAL
    mode: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # NORMAL, DEGRADED, UNCERTAIN, SAFE_MODE
    fused_utility: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0.0 - 1.0
    total_uncertainty: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0.0 - 1.0
    reasoning_trace: Mapped[str] = mapped_column(Text, nullable=False)
    inputs_summary_json: Mapped[Optional[dict]] = mapped_column(PortableJSON, nullable=True)
    override_applied: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    override_reason: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    device: Mapped["Device"] = relationship("Device", back_populates="decisions")
    mission: Mapped[Optional["Mission"]] = relationship("Mission", back_populates="decisions")

    __table_args__ = (
        Index("ix_decisions_device_timestamp", "device_id", "timestamp"),
        Index("ix_decisions_action", "action_proposed"),
        Index("ix_decisions_risk_mode", "risk", "mode"),
    )
