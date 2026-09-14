"""Cloud and Visual Obstruction Detection for Solar Sentry Agent 5 (Computer Vision).

Evaluates atmospheric and environmental visibility impairments:
- Solar limb profile integrity (bite-outs and occlusions caused by cloud edges)
- Surrounding sky texture and dispersion entropy
- Glare, flare halo, and saturation spillover
- Visual obstruction index (0.0=clear, 1.0=fully obstructed)

NOTE: This module strictly assesses instantaneous visual obstruction present in the frame.
It does NOT own readiness prediction or 15/30/60m forecasting, which is exclusively owned by Agent 6.
"""

from __future__ import annotations

from typing import Optional

import cv2
import numpy as np

from ai.vision.models import ObstructionMetrics, ObstructionType, SolarDisk


class ObstructionDetector:
    """Measures physical visual obstruction, clouds, and optical glare."""

    def analyze(
        self,
        gray: np.ndarray,
        disk: Optional[SolarDisk],
    ) -> ObstructionMetrics:
        """Analyzes instantaneous visual obstruction and cloud occlusion."""
        h, w = gray.shape
        total_pixels = h * w

        # 1. Glare assessment (intense blown out pixels spilling across frame)
        glare_mask = (gray >= 252)
        glare_count = np.count_nonzero(glare_mask)
        glare_fraction = float(glare_count / total_pixels)

        # 2. Case when no solar disk is detected
        if disk is None:
            # Check if image is completely dark (night / lens cap), completely blown out (glare), or overcast
            mean_intensity = float(np.mean(gray))
            if glare_fraction > 0.40:
                obs_type = ObstructionType.OVEREXPOSURE_GLARE
                obs_score = 0.95
                cloud_frac = 0.0
            elif mean_intensity < 15.0:
                obs_type = ObstructionType.OFF_TARGET
                obs_score = 1.0
                cloud_frac = 0.0
            else:
                # Moderate non-zero light with no disk => diffuse cloud overcast
                obs_type = ObstructionType.HEAVY_CLOUD
                obs_score = 0.90
                cloud_frac = 0.85

            return ObstructionMetrics(
                obstruction_score=obs_score,
                cloud_fraction=cloud_frac,
                glare_fraction=glare_fraction,
                limb_integrity=0.0,
                obstruction_type=obs_type,
            )

        # 3. Solar disk is present: evaluate limb integrity and cloud occlusion
        cx, cy, r = disk.center_x, disk.center_y, disk.radius

        # Limb integrity: sample along disk boundary (r +/- 2 pixels)
        # In a clear observation, the limb is a sharp, uniform boundary.
        # Passing clouds create localized drops in perimeter intensity.
        n_samples = 72
        angles = np.linspace(0, 2 * np.pi, n_samples, endpoint=False)
        limb_xs = np.round(cx + r * np.cos(angles)).astype(int)
        limb_ys = np.round(cy + r * np.sin(angles)).astype(int)

        valid_coords = (limb_xs >= 0) & (limb_xs < w) & (limb_ys >= 0) & (limb_ys < h)
        if np.count_nonzero(valid_coords) > 20:
            limb_vals = gray[limb_ys[valid_coords], limb_xs[valid_coords]]
            median_limb = float(np.median(limb_vals))
            # Fraction of perimeter that dropped below 40% of median limb intensity
            occluded_perimeter = np.count_nonzero(limb_vals < (0.40 * max(median_limb, 1.0)))
            limb_occlusion_ratio = float(occluded_perimeter / len(limb_vals))
            limb_integrity = float(np.clip(1.0 - limb_occlusion_ratio, 0.0, 1.0))
        else:
            limb_integrity = 0.5

        # Sky texture analysis: outside disk
        sky_mask = np.ones((h, w), dtype=np.uint8) * 255
        cv2.circle(sky_mask, (int(round(cx)), int(round(cy))), int(round(r * 1.05)), 0, -1)

        # In filtered solar imaging, sky outside disk should be dark or uniform.
        # Thin/cumulus clouds scatter light, creating gradient variances in the sky region.
        sky_pixels = gray[sky_mask == 255]
        if sky_pixels.size > 100:
            sky_std = float(np.std(sky_pixels))
            sky_mean = float(np.mean(sky_pixels))
            # High sky texture or non-trivial brightness indicates clouds/haze
            cloud_evidence = min(1.0, (sky_std / 30.0) * (sky_mean / 60.0))
        else:
            cloud_evidence = 0.0

        # Disk contrast variance: clouds across disk cause patchy attenuation
        disk_mask = np.zeros((h, w), dtype=np.uint8)
        cv2.circle(disk_mask, (int(round(cx)), int(round(cy))), int(round(r * 0.90)), 255, -1)
        disk_pixels = gray[disk_mask == 255]
        disk_std = float(np.std(disk_pixels)) if disk_pixels.size > 50 else 0.0
        # A quiet disk has low std (aside from smooth limb darkening); heavy blotchiness indicates clouds
        patchy_factor = float(np.clip((disk_std - 18.0) / 35.0, 0.0, 1.0)) if disk_std > 18.0 else 0.0

        # Estimated cloud fraction
        cloud_fraction = float(np.clip(
            0.5 * (1.0 - limb_integrity) + 0.3 * cloud_evidence + 0.2 * patchy_factor,
            0.0,
            1.0
        ))

        # Overall obstruction score
        if glare_fraction > 0.25:
            obstruction_score = min(1.0, glare_fraction * 2.0)
            obs_type = ObstructionType.OVEREXPOSURE_GLARE
        elif cloud_fraction > 0.60:
            obstruction_score = cloud_fraction
            obs_type = ObstructionType.HEAVY_CLOUD
        elif cloud_fraction > 0.15:
            obstruction_score = cloud_fraction
            obs_type = ObstructionType.PARTIAL_CLOUD
        else:
            obstruction_score = cloud_fraction
            obs_type = ObstructionType.CLEAR

        return ObstructionMetrics(
            obstruction_score=float(np.clip(obstruction_score, 0.0, 1.0)),
            cloud_fraction=cloud_fraction,
            glare_fraction=glare_fraction,
            limb_integrity=limb_integrity,
            obstruction_type=obs_type,
        )
