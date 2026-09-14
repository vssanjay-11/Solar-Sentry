"""
Solar Sentry - Command & Execution History Repository
Data access operations for dispatched control commands and edge execution confirmations.
Adheres strictly to docs/contracts/Command.json and docs/contracts/CommandResult.json.
"""

from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import select, and_
from sqlalchemy.orm import Session, selectinload

from backend.database.models.command import CommandRecord, CommandResultRecord
from backend.database.repositories.base import BaseRepository


class CommandRepository(BaseRepository[CommandRecord]):
    """Repository managing command dispatch history and execution confirmations."""

    def __init__(self, session: Session):
        super().__init__(CommandRecord, session)

    def record_command(
        self,
        command_id: str,
        device_id: str,
        command: str,
        pan: Optional[int] = None,
        tilt: Optional[int] = None,
        speed: Optional[int] = 100,
        target_state: Optional[str] = None,
        source: str = "MISSION_PLANNER",
        parameters_json: Optional[dict] = None,
        dispatched_at: Optional[datetime] = None,
    ) -> CommandRecord:
        """Stores a dispatched control command."""
        cmd = CommandRecord(
            command_id=command_id,
            device_id=device_id,
            command=command,
            pan=pan,
            tilt=tilt,
            speed=speed,
            target_state=target_state,
            source=source,
            parameters_json=parameters_json,
            dispatched_at=dispatched_at or datetime.now(timezone.utc),
        )
        return self.create(cmd)

    def record_result(
        self,
        command_id: str,
        status: str,
        current_pan: int,
        current_tilt: int,
        current_state: str,
        message: Optional[str] = None,
        executed_at: Optional[datetime] = None,
    ) -> CommandResultRecord:
        """Stores execution confirmation returned by the edge device."""
        result = CommandResultRecord(
            command_id=command_id,
            status=status,
            current_pan=current_pan,
            current_tilt=current_tilt,
            current_state=current_state,
            message=message,
            executed_at=executed_at or datetime.now(timezone.utc),
            received_at=datetime.now(timezone.utc),
        )
        self.session.add(result)
        self.session.flush()
        return result

    def get_with_result(self, command_id: str) -> Optional[CommandRecord]:
        """Fetches a command record with its execution result loaded."""
        stmt = (
            select(CommandRecord)
            .where(CommandRecord.command_id == command_id)
            .options(selectinload(CommandRecord.result))
        )
        return self.session.scalars(stmt).first()

    def list_recent(self, device_id: Optional[str] = None, limit: int = 50) -> List[CommandRecord]:
        """Returns the most recent commands dispatched, with results loaded."""
        stmt = select(CommandRecord).options(selectinload(CommandRecord.result))
        if device_id:
            stmt = stmt.where(CommandRecord.device_id == device_id)
        stmt = stmt.order_by(CommandRecord.dispatched_at.desc()).limit(limit)
        return list(self.session.scalars(stmt).all())

    def list_unconfirmed(self, device_id: Optional[str] = None) -> List[CommandRecord]:
        """Returns commands that do not yet have an edge execution result registered."""
        stmt = (
            select(CommandRecord)
            .outerjoin(CommandResultRecord, CommandRecord.command_id == CommandResultRecord.command_id)
            .where(CommandResultRecord.id.is_(None))
        )
        if device_id:
            stmt = stmt.where(CommandRecord.device_id == device_id)
        stmt = stmt.order_by(CommandRecord.dispatched_at.asc())
        return list(self.session.scalars(stmt).all())
