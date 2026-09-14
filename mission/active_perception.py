"""Solar Sentry — Active Perception Module.

Agent 9 Ownership.
Evaluates epistemic uncertainty and decides when the observatory must
perform exploratory probing or scanning actions to improve its knowledge,
rather than blindly following a static script.
"""

from __future__ import annotations

from typing import Dict, Any, Optional
from .types import ActivePerceptionInsight


class ActivePerceptionEvaluator:
    """
    Evaluates perception state and triggers active knowledge-acquisition actions
    when epistemic uncertainty is elevated or observation conditions are ambiguous.
    """

    UNCERTAINTY_THRESHOLD = 0.30
    CONFIDENCE_THRESHOLD_MIN = 0.70
    QUALITY_UNCERTAINTY_MARGIN = 0.15

    def __init__(
        self,
        uncertainty_threshold: float = UNCERTAINTY_THRESHOLD,
        confidence_threshold: float = CONFIDENCE_THRESHOLD_MIN,
    ):
        self.uncertainty_threshold = uncertainty_threshold
        self.confidence_threshold = confidence_threshold

    def evaluate(
        self,
        vision_uncertainty: float = 0.0,
        forecast_uncertainty: float = 0.0,
        solar_disk_confidence: float = 1.0,
        solar_disk_detected: bool = True,
        vision_quality: float = 0.8,
        cloud_coverage: float = 0.0,
    ) -> ActivePerceptionInsight:
        """
        Evaluates perception parameters to determine if an exploratory scan
        is required to reduce uncertainty before committing to high-resolution observation.
        """
        max_uncertainty = max(vision_uncertainty, forecast_uncertainty)
        reasons = []

        if max_uncertainty > self.uncertainty_threshold:
            reasons.append(
                f"Epistemic uncertainty ({max_uncertainty:.2f}) exceeds threshold ({self.uncertainty_threshold:.2f})"
            )

        if not solar_disk_detected:
            reasons.append("Solar disk not locked in field of view; scan needed to reacquire disk")
        elif solar_disk_confidence < self.confidence_threshold:
            reasons.append(
                f"Solar disk identification confidence ({solar_disk_confidence:.2f}) below threshold ({self.confidence_threshold:.2f})"
            )

        if cloud_coverage > 0.40 and vision_quality > 0.50:
            reasons.append(
                f"Transient cloud attenuation ({cloud_coverage:.2f}) creating visual ambiguity"
            )

        if reasons:
            trigger_reason = "; ".join(reasons)
            pattern = "BRACKET_3PT" if solar_disk_detected else "RASTER_SWEEP"
            return ActivePerceptionInsight(
                triggered=True,
                trigger_reason=f"The current perception state is uncertain ({trigger_reason}), therefore perform an exploratory scan.",
                uncertainty_before=max_uncertainty,
                uncertainty_after=max_uncertainty,
                information_gain=0.0,
                recommended_scan_pattern=pattern,
                notes="Active perception scan selected to improve knowledge rather than following a fixed script.",
            )

        return ActivePerceptionInsight(
            triggered=False,
            trigger_reason="Perception state is certain; direct observation can proceed.",
            uncertainty_before=max_uncertainty,
            uncertainty_after=max_uncertainty,
            information_gain=0.0,
            recommended_scan_pattern="NONE",
            notes="Perception certainty acceptable.",
        )

    @staticmethod
    def record_post_probe(
        insight: ActivePerceptionInsight,
        uncertainty_after: float,
    ) -> ActivePerceptionInsight:
        """Records post-scan uncertainty and computes information gain."""
        insight.uncertainty_after = uncertainty_after
        insight.information_gain = max(0.0, insight.uncertainty_before - uncertainty_after)
        insight.notes = (
            f"Active perception completed with information gain={insight.information_gain:.3f} "
            f"(uncertainty reduced from {insight.uncertainty_before:.2f} to {uncertainty_after:.2f})."
        )
        return insight
