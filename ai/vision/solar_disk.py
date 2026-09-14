"""Solar Disk Detection and Region Extraction for Solar Sentry Agent 5 (Computer Vision).

Performs:
- Solar disk localization via contour morphology and Hough circularity
- Edge clipping detection (Sun partially out of field-of-view)
- Solar region of interest (ROI) extraction and circular masking
- Astrophysical limb darkening verification: I(r) = I_0 * [1 - u * (1 - sqrt(1 - (r/R)^2))]
"""

from __future__ import annotations

from typing import Optional, Tuple

import cv2
import numpy as np

from ai.vision.models import SolarDisk


class SolarDiskDetector:
    """Detects, validates, and extracts the solar disk from full-frame imagery."""

    def __init__(
        self,
        min_circularity: float = 0.75,
        min_disk_radius_fraction: float = 0.05,
        max_disk_radius_fraction: float = 0.55,
    ) -> None:
        self.min_circularity = min_circularity
        self.min_disk_radius_fraction = min_disk_radius_fraction
        self.max_disk_radius_fraction = max_disk_radius_fraction

    def detect(self, gray: np.ndarray) -> Optional[SolarDisk]:
        """Detects the solar disk in a grayscale image.

        Returns:
            SolarDisk model if successfully detected, else None.
        """
        h, w = gray.shape
        min_dim = min(h, w)
        min_radius = min_dim * self.min_disk_radius_fraction
        max_radius = min_dim * self.max_disk_radius_fraction

        # Apply slight blur before thresholding to smooth sensor noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Multi-level threshold search to handle varying sky brightness
        # Try Otsu thresholding first; if too low or high, fallback to percentile
        otsu_val, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # In case Otsu picked up a non-solar threshold, check bright component
        if otsu_val < 40 or np.count_nonzero(binary) > (0.85 * h * w):
            # Fallback: threshold at 75th percentile of non-zero pixels
            p75 = float(np.percentile(gray[gray > 5] if np.any(gray > 5) else [100], 75))
            threshold_val = max(50.0, p75)
            _, binary = cv2.threshold(blurred, int(threshold_val), 255, cv2.THRESH_BINARY)

        # Morphological clean up
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)

        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        # Sort contours by area descending
        contours = sorted(contours, key=cv2.contourArea, reverse=True)

        best_disk: Optional[SolarDisk] = None
        best_score = -1.0

        for cnt in contours[:5]:
            area = cv2.contourArea(cnt)
            perimeter = cv2.arcLength(cnt, True)
            if perimeter <= 0 or area <= 0:
                continue

            # Circularity: 4 * pi * Area / Perimeter^2
            circularity = float(4.0 * np.pi * area / (perimeter ** 2))

            # Fit enclosing circle
            (cx, cy), radius = cv2.minEnclosingCircle(cnt)

            if radius < min_radius or radius > max_radius:
                continue

            # Check if disk is clipped at sensor margins
            is_clipped = (
                (cx - radius <= 2) or
                (cy - radius <= 2) or
                (cx + radius >= w - 3) or
                (cy + radius >= h - 3)
            )

            # For clipped disks, circularity may drop slightly, but should still be reasonable
            required_circularity = self.min_circularity * (0.80 if is_clipped else 1.0)
            if circularity < required_circularity:
                continue

            # Compute bounding box
            bx, by, bw, bh = cv2.boundingRect(cnt)

            # Compute mean intensity inside the disk
            mask = np.zeros((h, w), dtype=np.uint8)
            cv2.circle(mask, (int(round(cx)), int(round(cy))), int(round(radius)), 255, -1)
            mean_photosphere = float(cv2.mean(gray, mask=mask)[0])

            # Verify limb darkening profile
            limb_fitted = self._verify_limb_darkening(gray, cx, cy, radius)

            # Score this candidate: prefer higher circularity and genuine limb darkening
            candidate_score = circularity + (0.5 if limb_fitted else 0.0) + (0.2 if not is_clipped else 0.0)
            if candidate_score > best_score:
                best_score = candidate_score
                best_disk = SolarDisk(
                    center_x=float(cx),
                    center_y=float(cy),
                    radius=float(radius),
                    circularity=float(np.clip(circularity, 0.0, 1.0)),
                    is_clipped=is_clipped,
                    limb_darkening_fitted=limb_fitted,
                    mean_photosphere_intensity=mean_photosphere,
                    bounding_box=(int(bx), int(by), int(bw), int(bh)),
                )

        return best_disk

    def _verify_limb_darkening(
        self,
        gray: np.ndarray,
        cx: float,
        cy: float,
        radius: float,
    ) -> bool:
        """Verifies if radial intensity profile exhibits characteristic solar limb darkening.

        In a true stellar disk, intensity decreases from center to limb:
        I(r) / I(0) ~ 1 - u*(1 - sqrt(1 - (r/R)^2)) with u ~ 0.5-0.6 in optical white light.
        """
        h, w = gray.shape
        r_int = int(round(radius))
        if r_int < 10:
            return False

        # Sample concentric rings at 10%, 30%, 50%, 70%, 85% of radius
        radial_fractions = [0.10, 0.30, 0.50, 0.70, 0.85]
        ring_intensities = []

        for frac in radial_fractions:
            r_sample = frac * radius
            angles = np.linspace(0, 2 * np.pi, 24, endpoint=False)
            xs = np.round(cx + r_sample * np.cos(angles)).astype(int)
            ys = np.round(cy + r_sample * np.sin(angles)).astype(int)

            valid = (xs >= 0) & (xs < w) & (ys >= 0) & (ys < h)
            if np.count_nonzero(valid) < 8:
                continue
            ring_vals = gray[ys[valid], xs[valid]]
            ring_intensities.append(float(np.median(ring_vals)))

        if len(ring_intensities) < 4:
            return False

        # Check monotonic or near-monotonic decay from center ring to outer ring
        center_val = ring_intensities[0]
        limb_val = ring_intensities[-1]

        # In true solar white-light, limb is 15% to 45% darker than disk center
        is_decaying = (limb_val < center_val)
        decay_ratio = limb_val / max(center_val, 1.0)
        
        # Valid limb darkening ratio usually between 0.50 and 0.95
        return is_decaying and (0.50 <= decay_ratio <= 0.96)

    @staticmethod
    def extract_solar_region(
        image: np.ndarray,
        disk: SolarDisk,
        padding: int = 5,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Extracts the cropped solar region and its binary circular mask.

        Returns:
            Tuple of (cropped_roi, cropped_circular_mask)
        """
        h, w = image.shape[:2]
        cx, cy, r = int(round(disk.center_x)), int(round(disk.center_y)), int(round(disk.radius))

        x1 = max(0, cx - r - padding)
        y1 = max(0, cy - r - padding)
        x2 = min(w, cx + r + padding)
        y2 = min(h, cy + r + padding)

        roi = image[y1:y2, x1:x2].copy()

        # Generate circular mask in cropped coordinates
        mask = np.zeros((y2 - y1, x2 - x1), dtype=np.uint8)
        local_cx = cx - x1
        local_cy = cy - y1
        cv2.circle(mask, (local_cx, local_cy), r, 255, -1)

        return roi, mask
