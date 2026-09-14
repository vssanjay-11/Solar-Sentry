"""
Solar Sentry — Mission Memory Storage Repository
Agent 10: Digital Twin + Mission Memory + Learning + Simulation + Integration

Persistent and in-memory repository for storing, retrieving, and searching
mission execution records, science observations, and post-mission lessons learned.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from memory.schema import MissionObjectiveType, MissionRecord, MissionStatus


class MissionMemoryRepository:
    """
    Storage layer for mission logs, metrics, and retrospective lessons.
    Supports directory-based JSON persistence and in-memory indexing.
    """

    def __init__(self, storage_dir: Optional[str | Path] = None):
        if storage_dir is not None:
            self.storage_dir = Path(storage_dir)
            self.storage_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.storage_dir = None
        self._memory_store: Dict[str, MissionRecord] = {}

    def save_mission(self, mission: MissionRecord) -> str:
        """Stores a MissionRecord in memory and persists to disk if configured."""
        self._memory_store[mission.mission_id] = mission

        if self.storage_dir:
            file_path = self.storage_dir / f"{mission.mission_id}.json"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(json.dumps(mission.to_dict(), indent=2))

        return mission.mission_id

    def get_mission(self, mission_id: str) -> Optional[MissionRecord]:
        """Retrieves a mission record by ID."""
        if mission_id in self._memory_store:
            return self._memory_store[mission_id]

        if self.storage_dir:
            file_path = self.storage_dir / f"{mission_id}.json"
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.loads(f.read())
                    rec = MissionRecord(**data)
                    self._memory_store[mission_id] = rec
                    return rec

        return None

    def list_missions(self, limit: int = 50) -> List[MissionRecord]:
        """Lists all missions currently indexed, ordered by creation time descending."""
        missions = list(self._memory_store.values())
        missions.sort(key=lambda m: m.created_at, reverse=True)
        return missions[:limit]

    def search_missions(
        self,
        objective_type: Optional[MissionObjectiveType | str] = None,
        status: Optional[MissionStatus | str] = None,
        min_quality: Optional[float] = None
    ) -> List[MissionRecord]:
        """Filters stored missions matching criteria."""
        results = []
        obj_str = str(objective_type) if objective_type else None
        stat_str = str(status) if status else None

        for m in self._memory_store.values():
            if obj_str and m.objective.objective_type.value != obj_str and str(m.objective.objective_type) != obj_str:
                continue
            if stat_str and m.status.value != stat_str and str(m.status) != stat_str:
                continue
            if min_quality is not None and m.composite_quality_score < min_quality:
                continue
            results.append(m)

        return results

    def clear(self) -> None:
        """Clears in-memory store."""
        self._memory_store.clear()
