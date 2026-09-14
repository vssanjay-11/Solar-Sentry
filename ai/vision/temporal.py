"""Temporal Image Comparison, Registration, and Change Detection for Agent 5.

Performs:
- Sub-pixel image registration via Fourier Phase Correlation
- Compensation for mechanical pan/tilt tracking jitter
- Difference imaging and structural photometric change scoring
- Transient feature localization
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import cv2
import numpy as np

from ai.vision.models import SolarDisk, SunspotCandidate, TemporalAnalysisResult


class TemporalAnalyzer:
    """Analyzes temporal changes between consecutive observations of the Sun."""

    def __init__(
        self,
        jitter_threshold_pixels: float = 3.0,
        significant_change_threshold: float = 0.15,
    ) -> None:
        self.jitter_threshold_pixels = jitter_threshold_pixels
        self.significant_change_threshold = significant_change_threshold

    def register_frames(
        self,
        curr_gray: np.ndarray,
        ref_gray: np.ndarray,
    ) -> Tuple[bool, float, float, np.ndarray]:
        """Registers curr_gray to ref_gray using Fourier Phase Correlation.

        Returns:
            Tuple of (success, shift_x, shift_y, aligned_reference_image)
        """
        # Ensure dimensions match; if not, resize reference to current
        if curr_gray.shape != ref_gray.shape:
            ref_gray = cv2.resize(ref_gray, (curr_gray.shape[1], curr_gray.shape[0]))

        # Phase correlation requires float32
        curr_f = curr_gray.astype(np.float32)
        ref_f = ref_gray.astype(np.float32)

        # Apply Hanning window to reduce boundary spectral leakage
        h, w = curr_gray.shape
        hann = cv2.createHanningWindow((w, h), cv2.CV_32F)

        try:
            (shift_x, shift_y), response = cv2.phaseCorrelate(curr_f, ref_f, window=hann)
        except Exception:
            return False, 0.0, 0.0, ref_gray

        # If phase response is sufficiently strong, warp reference
        if response > 0.05 and not np.isnan(shift_x) and not np.isnan(shift_y):
            # Warp reference image by (shift_x, shift_y)
            warp_matrix = np.array([[1.0, 0.0, shift_x], [0.0, 1.0, shift_y]], dtype=np.float32)
            aligned_ref = cv2.warpAffine(ref_gray, warp_matrix, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            return True, float(shift_x), float(shift_y), aligned_ref
        else:
            return False, 0.0, 0.0, ref_gray

    def analyze(
        self,
        curr_gray: np.ndarray,
        ref_gray: Optional[np.ndarray],
        curr_disk: Optional[SolarDisk],
        curr_sunspots: List[SunspotCandidate],
        ref_sunspots: Optional[List[SunspotCandidate]] = None,
    ) -> TemporalAnalysisResult:
        """Compares current observation against a reference frame."""
        if ref_gray is None:
            return TemporalAnalysisResult(
                has_reference=False,
                registered_successfully=False,
                translation_x=0.0,
                translation_y=0.0,
                rotation_deg=0.0,
                change_score=0.0,
                motion_detected=False,
                transient_feature_count=0,
            )

        success, dx, dy, aligned_ref = self.register_frames(curr_gray, ref_gray)
        displacement = float(np.sqrt(dx**2 + dy**2))
        motion_detected = (displacement > self.jitter_threshold_pixels)

        # Compute photometric change inside the solar disk (or full frame if no disk)
        h, w = curr_gray.shape
        if curr_disk is not None:
            mask = np.zeros((h, w), dtype=np.uint8)
            cv2.circle(
                mask,
                (int(round(curr_disk.center_x)), int(round(curr_disk.center_y))),
                int(round(curr_disk.radius * 0.90)),
                255,
                -1
            )
        else:
            mask = np.ones((h, w), dtype=np.uint8) * 255

        # Absolute difference on aligned frames
        diff = cv2.absdiff(curr_gray, aligned_ref)
        masked_diff = diff[mask == 255]

        if masked_diff.size > 0:
            mean_diff = float(np.mean(masked_diff))
            # Normalized change score: typical differences are 0-30 intensity levels
            change_score = float(np.clip(mean_diff / 40.0, 0.0, 1.0))
        else:
            change_score = 0.0

        # Identify newly appeared or disappeared features
        transient_count = 0
        if ref_sunspots is not None:
            curr_coords = [(s.centroid_x, s.centroid_y) for s in curr_sunspots]
            ref_coords = [(s.centroid_x + dx, s.centroid_y + dy) for s in ref_sunspots]

            # Count spots in curr that have no match within 15 pixels in aligned ref
            for cx, cy in curr_coords:
                matched = any(np.hypot(cx - rx, cy - ry) < 15.0 for rx, ry in ref_coords)
                if not matched:
                    transient_count += 1

            # Count spots in ref that vanished in curr
            for rx, ry in ref_coords:
                matched = any(np.hypot(cx - rx, cy - ry) < 15.0 for cx, cy in curr_coords)
                if not matched:
                    transient_count += 1
        elif change_score > self.significant_change_threshold:
            transient_count = 1

        return TemporalAnalysisResult(
            has_reference=True,
            registered_successfully=success,
            translation_x=dx,
            translation_y=dy,
            rotation_deg=0.0,
            change_score=change_score,
            motion_detected=motion_detected,
            transient_feature_count=transient_count,
        )
