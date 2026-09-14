"""
Solar Sentry - Mission Records, Actions, and Memory Models
Mission planning, active perception action sequences, and episodic/long-term memory.
Adheres strictly to docs/contracts/MissionPlan.json & docs/contracts/MissionResult.json.
"""

from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import String, Integer, Float, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.core import Base, UTCDateTime, PortableJSON


class Mission(Base):
    """Authoritative scientific mission campaign record (Agent 9)."""
    __tablename__ = "missions"

    mission_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    mission_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="OBSERVE",
    )  # OBSERVE, SCAN, WAIT, SUSPEND, SAFE, ACTIVE_PERCEPTION, CALIBRATE
    objective: Mapped[str] = mapped_column(String(64), nullable=False)  # SOLAR_ACTIVE_REGION_SURVEY, etc.
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    state: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="PLANNED",
        index=True,
    )  # PENDING, PLANNING, EXECUTING, VERIFYING, COMPLETED, FAILED, ABORTED, SUSPENDED
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, nullable=True)
    target_coordinates_json: Mapped[Optional[dict]] = mapped_column(PortableJSON, nullable=True)
    parameters_json: Mapped[Optional[dict]] = mapped_column(PortableJSON, nullable=True)

    # Relationships
    actions: Mapped[List["MissionAction"]] = relationship(
        "MissionAction", back_populates="mission", cascade="all, delete-orphan", order_by="MissionAction.sequence_order"
    )
    observations: Mapped[List["Observation"]] = relationship("Observation", back_populates="mission")
    decisions: Mapped[List["DecisionRecord"]] = relationship("DecisionRecord", back_populates="mission")
    memories: Mapped[List["MissionMemory"]] = relationship("MissionMemory", back_populates="mission")

    __table_args__ = (
        Index("ix_missions_state_created", "state", "created_at"),
        Index("ix_missions_priority", "priority"),
        Index("ix_missions_type", "mission_type"),
    )


class MissionAction(Base):
    """Authoritative discrete action step within a mission execution sequence."""
    __tablename__ = "mission_actions"

    action_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    mission_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("missions.mission_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)
    action_type: Mapped[str] = mapped_column(String(32), nullable=False)  # SLEW, CAPTURE, CALIBRATE, DWELL, VERIFY
    target_pan: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    target_tilt: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING", index=True)  # PENDING, EXECUTING, SUCCESS, FAILED, SKIPPED
    started_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, nullable=True)
    result_json: Mapped[Optional[dict]] = mapped_column(PortableJSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    mission: Mapped["Mission"] = relationship("Mission", back_populates="actions")
    verifications: Mapped[List["VerificationRecord"]] = relationship("VerificationRecord", back_populates="action")

    __table_args__ = (
        Index("ix_mission_actions_order", "mission_id", "sequence_order"),
    )


class MissionMemory(Base):
    """Authoritative episodic and semantic mission memory for continual learning (Agents 9 & 10)."""
    __tablename__ = "mission_memories"

    memory_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    mission_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        ForeignKey("missions.mission_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, index=True)
    key_finding: Mapped[str] = mapped_column(String(256), nullable=False)
    context_tag: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # SOLAR_CYCLE, CLOUD_DYNAMICS, etc.
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    structured_payload_json: Mapped[Optional[dict]] = mapped_column(PortableJSON, nullable=True)
    relevance_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    mission: Mapped[Optional["Mission"]] = relationship("Mission", back_populates="memories")

    __table_args__ = (
        Index("ix_mission_memories_tag_time", "context_tag", "timestamp"),
    )
