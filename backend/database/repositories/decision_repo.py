"""
Solar Sentry - Decision Repository
Data access operations for cognitive decision records and explainable AI reasoning traces (Agent 8).
"""

from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.models.decision import DecisionRecord
from backend.database.repositories.base import BaseRepository


class DecisionRepository(BaseRepository[DecisionRecord]):
    """Repository managing cognitive decisions and explainability traces."""

    def __init__(self, session: Session):
        super().__init__(DecisionRecord, session)

    def record_decision(
        self,
        decision_id: str,
        device_id: str,
        action_proposed: str,
        reasoning_trace: str,
        confidence: float = 1.0,
        mission_id: Optional[str] = None,
        inputs_summary_json: Optional[dict] = None,
        override_applied: bool = False,
        override_reason: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ) -> DecisionRecord:
        """Stores an authoritative cognitive decision and reasoning trace."""
        decision = DecisionRecord(
            decision_id=decision_id,
            device_id=device_id,
            action_proposed=action_proposed,
            reasoning_trace=reasoning_trace,
            confidence=confidence,
            mission_id=mission_id,
            inputs_summary_json=inputs_summary_json,
            override_applied=override_applied,
            override_reason=override_reason,
            timestamp=timestamp or datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
        )
        return self.create(decision)

    def get_latest(self, device_id: str) -> Optional[DecisionRecord]:
        """Returns the most recent decision for the device."""
        stmt = (
            select(DecisionRecord)
            .where(DecisionRecord.device_id == device_id)
            .order_by(DecisionRecord.timestamp.desc())
            .limit(1)
        )
        return self.session.scalars(stmt).first()

    def list_by_mission(self, mission_id: str) -> List[DecisionRecord]:
        """Returns all decision records associated with a specific mission."""
        stmt = (
            select(DecisionRecord)
            .where(DecisionRecord.mission_id == mission_id)
            .order_by(DecisionRecord.timestamp.asc())
        )
        return list(self.session.scalars(stmt).all())

    def list_recent(self, limit: int = 50) -> List[DecisionRecord]:
        """Returns the most recent decisions across the platform."""
        stmt = select(DecisionRecord).order_by(DecisionRecord.timestamp.desc()).limit(limit)
        return list(self.session.scalars(stmt).all())
