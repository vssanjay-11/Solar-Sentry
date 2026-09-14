"""
Solar Sentry - Mission Repositories
Data access operations for mission planning, discrete actions, and episodic/semantic mission memory.
"""

from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import select, and_
from sqlalchemy.orm import Session, selectinload

from backend.database.models.mission import Mission, MissionAction, MissionMemory
from backend.database.repositories.base import BaseRepository


class MissionRepository(BaseRepository[Mission]):
    """Repository managing high-level scientific mission campaigns (Agent 9)."""

    def __init__(self, session: Session):
        super().__init__(Mission, session)

    def create_mission(
        self,
        mission_id: str,
        name: str,
        objective: str,
        priority: int = 5,
        state: str = "PLANNED",
        target_coordinates_json: Optional[dict] = None,
        parameters_json: Optional[dict] = None,
    ) -> Mission:
        """Creates a new mission campaign."""
        mission = Mission(
            mission_id=mission_id,
            name=name,
            objective=objective,
            priority=priority,
            state=state,
            target_coordinates_json=target_coordinates_json,
            parameters_json=parameters_json,
            created_at=datetime.now(timezone.utc),
        )
        return self.create(mission)

    def update_state(
        self,
        mission_id: str,
        state: str,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
    ) -> Optional[Mission]:
        """Updates mission state (e.g. ACTIVE, PAUSED, COMPLETED, ABORTED, FAILED)."""
        mission = self.get_by_id(mission_id)
        if mission:
            mission.state = state
            if started_at:
                mission.started_at = started_at
            elif state == "ACTIVE" and mission.started_at is None:
                mission.started_at = datetime.now(timezone.utc)
            if completed_at:
                mission.completed_at = completed_at
            elif state in ("COMPLETED", "ABORTED", "FAILED") and mission.completed_at is None:
                mission.completed_at = datetime.now(timezone.utc)
            self.update(mission)
        return mission

    def get_with_actions(self, mission_id: str) -> Optional[Mission]:
        """Fetches a mission with its sequence of actions eagerly loaded."""
        stmt = (
            select(Mission)
            .where(Mission.mission_id == mission_id)
            .options(selectinload(Mission.actions))
        )
        return self.session.scalars(stmt).first()

    def list_active_missions(self) -> List[Mission]:
        """Returns all missions currently in ACTIVE or PLANNED states."""
        stmt = (
            select(Mission)
            .where(Mission.state.in_(["ACTIVE", "PLANNED"]))
            .order_by(Mission.priority.desc(), Mission.created_at.asc())
        )
        return list(self.session.scalars(stmt).all())


class MissionActionRepository(BaseRepository[MissionAction]):
    """Repository managing discrete action steps within a mission sequence."""

    def __init__(self, session: Session):
        super().__init__(MissionAction, session)

    def add_action(
        self,
        action_id: str,
        mission_id: str,
        sequence_order: int,
        action_type: str,
        target_pan: Optional[int] = None,
        target_tilt: Optional[int] = None,
        status: str = "PENDING",
    ) -> MissionAction:
        """Adds a discrete action to a mission sequence."""
        action = MissionAction(
            action_id=action_id,
            mission_id=mission_id,
            sequence_order=sequence_order,
            action_type=action_type,
            target_pan=target_pan,
            target_tilt=target_tilt,
            status=status,
            created_at=datetime.now(timezone.utc),
        )
        return self.create(action)

    def update_action_status(
        self,
        action_id: str,
        status: str,
        result_json: Optional[dict] = None,
    ) -> Optional[MissionAction]:
        """Updates the status and result of a mission action."""
        action = self.get_by_id(action_id)
        now = datetime.now(timezone.utc)
        if action:
            action.status = status
            if status == "EXECUTING" and action.started_at is None:
                action.started_at = now
            elif status in ("SUCCESS", "FAILED", "SKIPPED") and action.completed_at is None:
                action.completed_at = now
            if result_json:
                action.result_json = result_json
            self.update(action)
        return action

    def get_next_pending_action(self, mission_id: str) -> Optional[MissionAction]:
        """Returns the next action awaiting execution for a mission."""
        stmt = (
            select(MissionAction)
            .where(
                and_(
                    MissionAction.mission_id == mission_id,
                    MissionAction.status == "PENDING",
                )
            )
            .order_by(MissionAction.sequence_order.asc())
            .limit(1)
        )
        return self.session.scalars(stmt).first()

    def list_by_mission(self, mission_id: str) -> List[MissionAction]:
        """Returns all actions belonging to a mission ordered by sequence."""
        stmt = (
            select(MissionAction)
            .where(MissionAction.mission_id == mission_id)
            .order_by(MissionAction.sequence_order.asc())
        )
        return list(self.session.scalars(stmt).all())


class MissionMemoryRepository(BaseRepository[MissionMemory]):
    """Repository managing episodic and semantic mission memory for continual learning (Agents 9 & 10)."""

    def __init__(self, session: Session):
        super().__init__(MissionMemory, session)

    def store_memory(
        self,
        memory_id: str,
        key_finding: str,
        context_tag: str,
        summary_text: str,
        mission_id: Optional[str] = None,
        structured_payload_json: Optional[dict] = None,
        relevance_score: float = 1.0,
        timestamp: Optional[datetime] = None,
    ) -> MissionMemory:
        """Stores a new learning memory or observation summary."""
        mem = MissionMemory(
            memory_id=memory_id,
            mission_id=mission_id,
            timestamp=timestamp or datetime.now(timezone.utc),
            key_finding=key_finding,
            context_tag=context_tag,
            summary_text=summary_text,
            structured_payload_json=structured_payload_json,
            relevance_score=relevance_score,
            created_at=datetime.now(timezone.utc),
        )
        return self.create(mem)

    def search_by_tag(self, context_tag: str, limit: int = 50) -> List[MissionMemory]:
        """Returns memory records classified under a specific context tag."""
        stmt = (
            select(MissionMemory)
            .where(MissionMemory.context_tag == context_tag)
            .order_by(MissionMemory.timestamp.desc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

    def list_recent(self, limit: int = 50) -> List[MissionMemory]:
        """Returns recent mission memory records."""
        stmt = select(MissionMemory).order_by(MissionMemory.timestamp.desc()).limit(limit)
        return list(self.session.scalars(stmt).all())
