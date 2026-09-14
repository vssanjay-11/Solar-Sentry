"""Solar Sentry — Mission Scheduler & Priority Queue.

Agent 9 Ownership.
Manages observatory mission queuing, priority-based scheduling,
and preemption by emergency or safety-critical directives.
"""

from __future__ import annotations

import heapq
import logging
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field

from .types import (
    Mission,
    MissionState,
    MissionResult,
    MissionType,
)
from .executor import MissionExecutor

logger = logging.getLogger("MissionScheduler")


@dataclass(order=True)
class PrioritizedMissionItem:
    """Heap queue item sorted by inverted priority for max-heap behavior."""
    priority_key: int  # Negative of mission.priority so highest priority pops first
    counter: int       # Tiebreaker counter
    mission: Mission = field(compare=False)


class MissionScheduler:
    """
    Priority-based mission scheduler with preemption support.
    Ensures safety and emergency missions immediately preempt routine observations.
    """

    def __init__(self, executor: MissionExecutor):
        self.executor = executor
        self._queue: List[PrioritizedMissionItem] = []
        self._counter: int = 0
        self.current_mission: Optional[Mission] = None
        self.completed_missions: List[Mission] = []
        self.history: List[MissionResult] = []

    @property
    def pending_count(self) -> int:
        return len(self._queue)

    def submit_mission(self, mission: Mission) -> str:
        """
        Submits a mission to the scheduler.
        If the mission priority exceeds the currently running mission, triggers preemption.
        """
        self._counter += 1
        item = PrioritizedMissionItem(
            priority_key=-mission.priority,
            counter=self._counter,
            mission=mission,
        )

        # Check if preemption is needed
        if self.current_mission and self.current_mission.status == MissionState.EXECUTING:
            if mission.priority > self.current_mission.priority:
                logger.warning(
                    f"Preempting active mission {self.current_mission.mission_id} (priority {self.current_mission.priority}) "
                    f"with higher-priority mission {mission.mission_id} (priority {mission.priority})"
                )
                self.current_mission.status = MissionState.ABORTED
                self.current_mission.log(f"Preempted by incoming higher-priority mission {mission.mission_id}")
                # Execute preempting mission immediately
                heapq.heappush(self._queue, item)
                return mission.mission_id

        heapq.heappush(self._queue, item)
        mission.log(f"Queued in scheduler with priority {mission.priority}.")
        return mission.mission_id

    def step(
        self,
        quality_before: float = 0.71,
        quality_after: float = 0.86,
        safety_interlock_active: bool = False,
    ) -> Optional[MissionResult]:
        """
        Extracts and executes the highest-priority pending mission.
        """
        if not self._queue:
            return None

        item = heapq.heappop(self._queue)
        mission = item.mission
        self.current_mission = mission

        result = self.executor.execute_mission(
            mission=mission,
            quality_before=quality_before,
            quality_after=quality_after,
            safety_interlock_active=safety_interlock_active,
        )

        self.completed_missions.append(mission)
        self.history.append(result)
        self.current_mission = None
        return result

    def clear(self) -> None:
        """Clears all pending missions."""
        self._queue.clear()
        self.current_mission = None

    def cancel_mission(self, mission_id: str) -> bool:
        """Cancels a queued mission by ID."""
        for i, item in enumerate(self._queue):
            if item.mission.mission_id == mission_id:
                item.mission.status = MissionState.ABORTED
                item.mission.log("Mission cancelled while in queue.")
                self.completed_missions.append(item.mission)
                del self._queue[i]
                heapq.heapify(self._queue)
                return True
        return False
