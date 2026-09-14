"""
Solar Sentry - Verification Repository
Data access operations for post-action closed-loop perception verifications (Agent 9).
"""

from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.models.verification import VerificationRecord
from backend.database.repositories.base import BaseRepository


class VerificationRepository(BaseRepository[VerificationRecord]):
    """Repository managing closed-loop verification records."""

    def __init__(self, session: Session):
        super().__init__(VerificationRecord, session)

    def record_verification(
        self,
        verification_id: str,
        action_id: Optional[str] = None,
        observation_id: Optional[str] = None,
        status: str = "VERIFIED_OPTIMAL",
        pointing_error_degrees: Optional[float] = None,
        optical_quality_confirmed: bool = True,
        verification_metrics_json: Optional[dict] = None,
        notes: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ) -> VerificationRecord:
        """Stores a post-action optical and pointing verification result."""
        ver = VerificationRecord(
            verification_id=verification_id,
            action_id=action_id,
            observation_id=observation_id,
            timestamp=timestamp or datetime.now(timezone.utc),
            status=status,
            pointing_error_degrees=pointing_error_degrees,
            optical_quality_confirmed=optical_quality_confirmed,
            verification_metrics_json=verification_metrics_json,
            notes=notes,
            created_at=datetime.now(timezone.utc),
        )
        return self.create(ver)

    def get_by_action(self, action_id: str) -> List[VerificationRecord]:
        """Returns verification records associated with a specific action."""
        stmt = (
            select(VerificationRecord)
            .where(VerificationRecord.action_id == action_id)
            .order_by(VerificationRecord.timestamp.desc())
        )
        return list(self.session.scalars(stmt).all())

    def get_by_observation(self, observation_id: str) -> List[VerificationRecord]:
        """Returns verification records associated with a specific observation."""
        stmt = (
            select(VerificationRecord)
            .where(VerificationRecord.observation_id == observation_id)
            .order_by(VerificationRecord.timestamp.desc())
        )
        return list(self.session.scalars(stmt).all())

    def list_recent(self, limit: int = 50) -> List[VerificationRecord]:
        """Returns the most recent verification records."""
        stmt = select(VerificationRecord).order_by(VerificationRecord.timestamp.desc()).limit(limit)
        return list(self.session.scalars(stmt).all())
