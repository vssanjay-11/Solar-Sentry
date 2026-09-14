"""Solar Sentry — Candidate Region & Action Evaluator.

Agent 9 Ownership.
Evaluates, scores, and ranks candidate observation directions / regions.
Balances predicted observation quality, epistemic certainty, and actuator displacement.
"""

from __future__ import annotations

import math
from typing import List, Dict, Tuple, Optional, Any
from .types import CandidateRegion


class CandidateEvaluator:
    """
    Evaluates observation candidates across multiple criteria:
    - Predicted observation quality (weight = 0.70)
    - Epistemic certainty (1 - uncertainty) (weight = 0.15)
    - Actuator displacement cost (weight = 0.15)
    """

    DEFAULT_WEIGHT_QUALITY = 0.70
    DEFAULT_WEIGHT_CERTAINTY = 0.15
    DEFAULT_WEIGHT_DISPLACEMENT = 0.15

    # Standard solar observatory coordinate mapping for typical regions
    STANDARD_REGIONS: Dict[str, Tuple[int, int]] = {
        "CENTER": (90, 82),
        "LEFT": (60, 80),
        "RIGHT": (120, 80),
        "NORTH": (90, 95),
        "SOUTH": (90, 65),
    }

    def __init__(
        self,
        weight_quality: float = DEFAULT_WEIGHT_QUALITY,
        weight_certainty: float = DEFAULT_WEIGHT_CERTAINTY,
        weight_displacement: float = DEFAULT_WEIGHT_DISPLACEMENT,
    ):
        self.w_quality = weight_quality
        self.w_certainty = weight_certainty
        self.w_displacement = weight_displacement

    def score_candidate(
        self,
        candidate: CandidateRegion,
        current_pan: int = 90,
        current_tilt: int = 0,
    ) -> float:
        """
        Computes composite multi-criteria utility score for a candidate region.
        Ensures actuator limits are strictly respected [0, 180].
        """
        # Hard boundary enforcement
        if not (0 <= candidate.pan <= 180 and 0 <= candidate.tilt <= 180):
            candidate.composite_score = -1.0
            return -1.0

        # Normalized actuator displacement cost: [0.0, 1.0]
        delta_pan = abs(candidate.pan - current_pan)
        delta_tilt = abs(candidate.tilt - current_tilt)
        max_displacement = 360.0
        disp_cost = (delta_pan + delta_tilt) / max_displacement
        candidate.displacement_cost = disp_cost

        certainty = max(0.0, min(1.0, candidate.confidence * (1.0 - candidate.uncertainty)))
        quality = max(0.0, min(1.0, candidate.predicted_quality))

        score = (
            (self.w_quality * quality)
            + (self.w_certainty * certainty)
            - (self.w_displacement * disp_cost)
        )
        candidate.composite_score = round(score, 4)
        return candidate.composite_score

    def rank_candidates(
        self,
        candidates: List[CandidateRegion],
        current_pan: int = 90,
        current_tilt: int = 0,
    ) -> List[CandidateRegion]:
        """Scores and sorts candidates in descending order of composite utility."""
        for cand in candidates:
            self.score_candidate(cand, current_pan, current_tilt)

        # Sort descending by composite score, then by predicted quality as tiebreaker
        return sorted(
            candidates,
            key=lambda c: (c.composite_score, c.predicted_quality),
            reverse=True,
        )

    def select_best(
        self,
        candidates: List[CandidateRegion],
        current_pan: int = 90,
        current_tilt: int = 0,
        min_quality_threshold: float = 0.0,
    ) -> Optional[CandidateRegion]:
        """Selects the highest utility candidate meeting the minimum quality threshold."""
        ranked = self.rank_candidates(candidates, current_pan, current_tilt)
        for cand in ranked:
            if cand.composite_score >= 0.0 and cand.predicted_quality >= min_quality_threshold:
                return cand
        return None

    @classmethod
    def from_quality_dict(
        cls,
        qualities: Dict[str, float | Dict[str, Any]],
        current_pan: int = 90,
        current_tilt: int = 0,
    ) -> List[CandidateRegion]:
        """
        Helper to construct candidate regions from a simple mapping, e.g.:
        {"LEFT": 0.61, "CENTER": 0.82, "RIGHT": 0.73}
        """
        candidates: List[CandidateRegion] = []
        for region_id, val in qualities.items():
            reg_upper = region_id.upper()
            coords = cls.STANDARD_REGIONS.get(reg_upper, (90, 80))
            if isinstance(val, (int, float)):
                cand = CandidateRegion(
                    region_id=region_id,
                    pan=coords[0],
                    tilt=coords[1],
                    predicted_quality=float(val),
                    confidence=1.0,
                    uncertainty=0.05,
                )
            elif isinstance(val, dict):
                cand = CandidateRegion(
                    region_id=region_id,
                    pan=int(val.get("pan", coords[0])),
                    tilt=int(val.get("tilt", coords[1])),
                    predicted_quality=float(val.get("quality", 0.0)),
                    confidence=float(val.get("confidence", 1.0)),
                    uncertainty=float(val.get("uncertainty", 0.05)),
                    metadata=dict(val.get("metadata", {})),
                )
            else:
                continue
            candidates.append(cand)
        return candidates
