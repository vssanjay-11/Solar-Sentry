"""Sunspot Detection and Solar Feature Segmentation for Solar Sentry Agent 5 (Computer Vision).

Performs:
- Localized dark feature segmentation on the quiet solar photosphere
- Umbra (dark core) and Penumbra (filamentary halo) decomposition
- Heliographic disk-relative coordinate transformation (r, theta)
- Area estimation (pixel area and disk fraction)
- Rejection of camera dust / sensor dead pixels
- Strict scientific boundaries: No unverified solar flare prediction claims
"""

from __future__ import annotations

from typing import List, Tuple

import cv2
import numpy as np

from ai.vision.models import SolarDisk, SunspotCandidate


class SunspotDetector:
    """Detects and segments sunspot candidates within the localized solar disk."""

    def __init__(
        self,
        contrast_threshold: float = 0.12,  # Must be at least 12% darker than local photosphere
        min_spot_area_pixels: int = 3,
        max_spot_area_fraction: float = 0.05,  # Real sunspots rarely exceed 5% of solar disk
        dust_aspect_ratio_max: float = 4.0,   # Elongated fibers or scratches are likely dust
    ) -> None:
        self.contrast_threshold = contrast_threshold
        self.min_spot_area_pixels = min_spot_area_pixels
        self.max_spot_area_fraction = max_spot_area_fraction
        self.dust_aspect_ratio_max = dust_aspect_ratio_max

    def detect(
        self,
        gray: np.ndarray,
        disk: SolarDisk,
    ) -> List[SunspotCandidate]:
        """Detects sunspot candidates within the solar disk.

        Args:
            gray: Full-frame grayscale image.
            disk: Validated SolarDisk geometry.

        Returns:
            List of confirmed SunspotCandidate models.
        """
        h, w = gray.shape
        cx, cy, r = disk.center_x, disk.center_y, disk.radius
        disk_area = np.pi * (r ** 2)

        # 1. Create disk mask slightly inset (0.95 * r) to prevent limb transition false positives
        inset_r = int(round(r * 0.94))
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.circle(mask, (int(round(cx)), int(round(cy))), inset_r, 255, -1)

        # 2. Compute smooth background model of the quiet photosphere
        # Using a large median/Gaussian blur to model the large-scale photosphere gradient (including limb darkening)
        kernel_size = max(15, int(r * 0.15))
        if kernel_size % 2 == 0:
            kernel_size += 1
        photosphere_model = cv2.GaussianBlur(gray, (kernel_size, kernel_size), 0)

        # 3. Calculate relative darkness: (Photosphere - Image) / Photosphere
        # Where gray < photosphere_model
        photo_float = np.maximum(photosphere_model.astype(np.float32), 1.0)
        gray_float = gray.astype(np.float32)
        relative_darkness = np.zeros_like(gray_float)

        # Only compute inside the solar disk
        inside_disk = (mask == 255)
        relative_darkness[inside_disk] = (photo_float[inside_disk] - gray_float[inside_disk]) / photo_float[inside_disk]

        # 4. Binary threshold for candidate dark spots
        spot_mask = np.zeros((h, w), dtype=np.uint8)
        spot_mask[inside_disk & (relative_darkness >= self.contrast_threshold)] = 255

        # Morphological clean up to remove single-pixel salt/pepper sensor noise
        clean_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        spot_mask = cv2.morphologyEx(spot_mask, cv2.MORPH_OPEN, clean_kernel)

        # 5. Connected component analysis
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(spot_mask, connectivity=8)

        candidates: List[SunspotCandidate] = []
        spot_id = 1

        for label_idx in range(1, num_labels):
            area = int(stats[label_idx, cv2.CC_STAT_AREA])
            if area < self.min_spot_area_pixels:
                continue

            area_fraction = float(area / disk_area)
            if area_fraction > self.max_spot_area_fraction:
                # Too massive for a physical sunspot; likely cloud band or shadow
                continue

            # Bounding box and aspect ratio to filter fiber/scratch dust artifacts
            bw = stats[label_idx, cv2.CC_STAT_WIDTH]
            bh = stats[label_idx, cv2.CC_STAT_HEIGHT]
            aspect_ratio = max(bw, bh) / max(min(bw, bh), 1)
            if aspect_ratio > self.dust_aspect_ratio_max and area > 15:
                continue

            cent_x, cent_y = centroids[label_idx]

            # Compute disk-relative polar coordinates
            dx = cent_x - cx
            dy = cent_y - cy
            dist_from_center = float(np.sqrt(dx**2 + dy**2))
            rel_r = float(np.clip(dist_from_center / r, 0.0, 1.0))
            theta_rad = np.arctan2(dy, dx)
            theta_deg = float(np.degrees(theta_rad) % 360.0)

            # Intensity metrics
            component_mask = (labels == label_idx)
            component_pixels = gray[component_mask]
            min_intensity = float(np.min(component_pixels))
            mean_intensity = float(np.mean(component_pixels))
            local_photo = float(np.mean(photo_float[component_mask]))

            contrast_ratio = float(np.clip(1.0 - (mean_intensity / max(local_photo, 1.0)), 0.0, 1.0))

            # Umbra / Penumbra segmentation
            # Umbra: intensely dark core (typically > 35% darker than photosphere)
            umbra_mask = component_mask & (relative_darkness >= 0.35)
            umbra_area = int(np.count_nonzero(umbra_mask))
            has_penumbra = (umbra_area > 0 and (area - umbra_area) >= 2)

            # Confidence estimation based on:
            # - contrast depth
            # - presence of umbra/penumbra structure
            # - distance from limb (limb features have slightly lower geometric certainty)
            limb_confidence_factor = 1.0 if rel_r < 0.85 else (1.0 - (rel_r - 0.85) * 3.0)
            area_confidence = min(1.0, area / 8.0)
            contrast_confidence = min(1.0, contrast_ratio / 0.30)
            
            confidence = float(np.clip(
                0.4 * contrast_confidence + 0.3 * area_confidence + 0.3 * max(0.1, limb_confidence_factor),
                0.1,
                0.99
            ))

            candidates.append(
                SunspotCandidate(
                    id=spot_id,
                    centroid_x=float(cent_x),
                    centroid_y=float(cent_y),
                    disk_relative_r=rel_r,
                    disk_relative_theta_deg=theta_deg,
                    area_pixels=area,
                    relative_area_fraction=area_fraction,
                    min_intensity=min_intensity,
                    contrast_ratio=contrast_ratio,
                    has_penumbra=has_penumbra,
                    umbra_area_pixels=umbra_area,
                    confidence=confidence,
                )
            )
            spot_id += 1

        # Sort candidates by area descending
        candidates = sorted(candidates, key=lambda c: c.area_pixels, reverse=True)
        # Re-index
        for idx, c in enumerate(candidates):
            c.id = idx + 1

        return candidates
