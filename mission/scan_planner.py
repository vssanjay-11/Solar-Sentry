"""Solar Sentry — Scan Trajectory & Survey Planner.

Agent 9 Ownership.
Generates structured scan trajectories (3-point bracket, elevation sweep, raster grid)
to acquire knowledge, discover candidate regions, or re-lock solar disk.
"""

from __future__ import annotations

import uuid
from typing import List, Dict, Tuple, Optional
from .types import (
    MissionAction,
    ActionVerb,
    ActionStatus,
    Command,
    CandidateRegion,
)


class ScanPlanner:
    """
    Synthesizes spatial scan patterns into sequenced MissionActions.
    Guarantees hardware angular limits [0, 180] deg on both pan and tilt axes.
    """

    DEFAULT_SETTLING_TIME_SEC = 0.5
    DEFAULT_ACTION_TIMEOUT_SEC = 5.0

    @classmethod
    def plan_3pt_bracket(
        cls,
        center_pan: int = 90,
        center_tilt: int = 80,
        span_deg: int = 30,
        speed: int = 80,
    ) -> Tuple[List[CandidateRegion], List[MissionAction]]:
        """
        Plans a 3-point azimuth bracket [LEFT, CENTER, RIGHT].
        Returns candidate regions and the corresponding sequenced actions.
        """
        left_pan = max(0, min(180, center_pan - span_deg))
        right_pan = max(0, min(180, center_pan + span_deg))
        clamped_tilt = max(0, min(180, center_tilt))

        candidates = [
            CandidateRegion(region_id="LEFT", pan=left_pan, tilt=clamped_tilt),
            CandidateRegion(region_id="CENTER", pan=center_pan, tilt=clamped_tilt),
            CandidateRegion(region_id="RIGHT", pan=right_pan, tilt=clamped_tilt),
        ]

        actions: List[MissionAction] = []
        for cand in candidates:
            cmd = Command(
                command_id=f"cmd-scan-{cand.region_id.lower()}-{uuid.uuid4().hex[:6]}",
                command=ActionVerb.SCAN,
                pan=cand.pan,
                tilt=cand.tilt,
                speed=speed,
            )
            act = MissionAction(
                action_id=f"act-scan-{cand.region_id.lower()}-{uuid.uuid4().hex[:6]}",
                action_type=f"SCAN_{cand.region_id}",
                command=cmd,
                timeout_sec=cls.DEFAULT_ACTION_TIMEOUT_SEC,
            )
            actions.append(act)

        return candidates, actions

    @classmethod
    def plan_elevation_sweep(
        cls,
        pan: int = 90,
        tilt_min: int = 45,
        tilt_max: int = 85,
        step_deg: int = 10,
        speed: int = 60,
    ) -> Tuple[List[CandidateRegion], List[MissionAction]]:
        """Plans a vertical elevation sweep at fixed azimuth."""
        candidates = []
        actions = []
        tilt = tilt_min
        idx = 1
        while tilt <= tilt_max:
            reg_id = f"ELEV_{tilt}DEG"
            cand = CandidateRegion(region_id=reg_id, pan=pan, tilt=tilt)
            candidates.append(cand)

            cmd = Command(
                command_id=f"cmd-sweep-{idx}-{uuid.uuid4().hex[:6]}",
                command=ActionVerb.SCAN,
                pan=pan,
                tilt=tilt,
                speed=speed,
            )
            act = MissionAction(
                action_id=f"act-sweep-{idx}-{uuid.uuid4().hex[:6]}",
                action_type="ELEVATION_SWEEP",
                command=cmd,
                timeout_sec=cls.DEFAULT_ACTION_TIMEOUT_SEC,
            )
            actions.append(act)
            tilt += step_deg
            idx += 1

        return candidates, actions

    @classmethod
    def plan_grid_search(
        cls,
        pan_range: Tuple[int, int] = (60, 120),
        tilt_range: Tuple[int, int] = (60, 90),
        step_deg: int = 30,
        speed: int = 75,
    ) -> Tuple[List[CandidateRegion], List[MissionAction]]:
        """Plans a 2D coarse grid search for acquiring the solar disk."""
        candidates = []
        actions = []
        idx = 1
        for p in range(pan_range[0], pan_range[1] + 1, step_deg):
            for t in range(tilt_range[0], tilt_range[1] + 1, step_deg):
                cand = CandidateRegion(region_id=f"GRID_{p}_{t}", pan=p, tilt=t)
                candidates.append(cand)
                cmd = Command(
                    command_id=f"cmd-grid-{idx}-{uuid.uuid4().hex[:6]}",
                    command=ActionVerb.SCAN,
                    pan=p,
                    tilt=t,
                    speed=speed,
                )
                act = MissionAction(
                    action_id=f"act-grid-{idx}-{uuid.uuid4().hex[:6]}",
                    action_type="GRID_SEARCH",
                    command=cmd,
                    timeout_sec=cls.DEFAULT_ACTION_TIMEOUT_SEC,
                )
                actions.append(act)
                idx += 1

        return candidates, actions
