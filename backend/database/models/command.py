"""
Solar Sentry - Command & Execution History Models
Dispatched edge control commands and execution results adhering to Command.json & CommandResult.json contracts.
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import BigInteger, Integer, String, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.core import Base, UTCDateTime, PortableJSON


class CommandRecord(Base):
    """Authoritative control command dispatched to edge controllers."""
    __tablename__ = "commands"

    command_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    device_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("devices.device_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    command: Mapped[str] = mapped_column(String(32), nullable=False)  # OBSERVE, PARK, SCAN, SET_SERVO, SET_STATE, REBOOT, CALIBRATE, EMERGENCY_STOP
    pan: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tilt: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    speed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=100)
    target_state: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    dispatched_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="MISSION_PLANNER")
    parameters_json: Mapped[Optional[dict]] = mapped_column(PortableJSON, nullable=True)

    # Relationships
    device: Mapped["Device"] = relationship("Device", back_populates="commands")
    result: Mapped[Optional["CommandResultRecord"]] = relationship(
        "CommandResultRecord", back_populates="command", uselist=False, cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_commands_device_dispatched", "device_id", "dispatched_at"),
        Index("ix_commands_verb", "command"),
    )


class CommandResultRecord(Base):
    """Authoritative execution confirmation returned by the Solar Sentry ESP32 edge controller."""
    __tablename__ = "command_results"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    command_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("commands.command_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # SUCCESS, REJECTED_SAFETY, INVALID_PARAMS, EXECUTION_ERROR
    message: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    current_pan: Mapped[int] = mapped_column(Integer, nullable=False)
    current_tilt: Mapped[int] = mapped_column(Integer, nullable=False)
    current_state: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    executed_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, index=True)
    received_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    command: Mapped["CommandRecord"] = relationship("CommandRecord", back_populates="result")

    __table_args__ = (
        Index("ix_command_results_state_status", "current_state", "status"),
    )
