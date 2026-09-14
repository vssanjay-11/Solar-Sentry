"""Image Quality Assessment for Solar Sentry Agent 5 (Computer Vision).

Performs objective optical evaluation:
- Blur estimation via Modified Laplacian Variance & Tenengrad gradient magnitude
- Exposure and dynamic range fidelity analysis (saturation/underexposure clipping)
- RMS contrast estimation
- High-frequency noise estimation via Donoho-Johnstone Median Absolute Deviation (MAD)
- Source-calibrated composite quality scoring
"""

from __future__ import annotations

import cv2
import numpy as np

from ai.vision.ingestion import PreprocessedImage
from ai.vision.models import ImageSourceType, QualityMetrics, QualityRating


class ImageQualityAnalyzer:
    """Evaluates optical sharpness, photometric dynamic range, and digital noise."""

    @staticmethod
    def calculate_laplacian_variance(gray: np.ndarray) -> float:
        """Computes variance of the Laplacian operator as a focus/sharpness metric.

        Higher values indicate sharp edges; values < 50-100 indicate severe blur.
        """
        laplacian = cv2.Laplacian(gray, cv2.CV_64F, ksize=3)
        return float(np.var(laplacian))

    @staticmethod
    def calculate_tenengrad(gray: np.ndarray) -> float:
        """Computes Tenengrad gradient energy density.

        Measures energy of high-frequency gradient components using Sobel operators.
        """
        gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        grad_sq = gx ** 2 + gy ** 2
        return float(np.mean(grad_sq))

    @staticmethod
    def analyze_exposure(gray: np.ndarray) -> tuple[float, float, float]:
        """Analyzes histogram distribution and clipping boundaries.

        Returns:
            Tuple of (exposure_score, clipped_black_fraction, clipped_white_fraction)
        """
        total_pixels = gray.size
        if total_pixels == 0:
            return 0.0, 1.0, 1.0

        black_clipped = np.count_nonzero(gray <= 4)
        white_clipped = np.count_nonzero(gray >= 251)

        frac_black = float(black_clipped / total_pixels)
        frac_white = float(white_clipped / total_pixels)

        # Solar images often have dark space around the disk (up to 70% black pixels),
        # but white clipping (sun overexposure blowout) is particularly damaging.
        # Non-clipped dynamic range:
        mean_val = float(np.mean(gray))
        std_val = float(np.std(gray))

        # Penalty for blowout or severe underexposure
        white_penalty = min(1.0, frac_white * 2.5)  # severe penalty for glare blowout
        # Black penalty is milder because solar disk is a circle surrounded by black space
        black_penalty = max(0.0, (frac_black - 0.75) * 2.0) if frac_black > 0.75 else 0.0

        # Exposure centering metric
        dynamic_score = min(1.0, std_val / 45.0)

        raw_score = (1.0 - white_penalty) * (1.0 - black_penalty) * (0.5 + 0.5 * dynamic_score)
        exposure_score = float(np.clip(raw_score, 0.0, 1.0))

        return exposure_score, frac_black, frac_white

    @staticmethod
    def calculate_rms_contrast(gray: np.ndarray) -> float:
        """Computes Root Mean Square (RMS) luminance contrast.

        RMS Contrast = sqrt( (1 / N) * sum((I_i - I_mean)^2) )
        """
        norm_img = gray.astype(np.float64) / 255.0
        mean_norm = np.mean(norm_img)
        rms = np.sqrt(np.mean((norm_img - mean_norm) ** 2))
        return float(rms)

    @staticmethod
    def estimate_noise_mad(gray: np.ndarray) -> float:
        """Estimates additive high-frequency noise using Median Absolute Deviation (MAD).

        Based on the Donoho & Johnstone wavelet/Laplacian high-frequency formulation:
        sigma = median(|detail - median(detail)|) / 0.6745
        """
        # Extract high-frequency detail using a 3x3 Laplacian residual
        kernel = np.array([[1, -2, 1], [-2, 4, -2], [1, -2, 1]], dtype=np.float32)
        residual = cv2.filter2D(gray.astype(np.float32), cv2.CV_32F, kernel)
        abs_res = np.abs(residual - np.median(residual))
        mad = float(np.median(abs_res))
        sigma = mad / 0.6745
        return float(sigma)

    def analyze(self, image: PreprocessedImage) -> QualityMetrics:
        """Runs comprehensive optical quality assessment on ingested frame."""
        gray = image.gray
        blur_score = self.calculate_laplacian_variance(gray)
        tenengrad = self.calculate_tenengrad(gray)
        exposure_score, frac_black, frac_white = self.analyze_exposure(gray)
        rms_contrast = self.calculate_rms_contrast(gray)
        noise_estimate = self.estimate_noise_mad(gray)

        # Baseline calibration depends on image source
        # ESP32-CAM OV2640 has inherent sensor noise (sigma ~ 3-8) and softer optics.
        is_esp32 = (image.source_type == ImageSourceType.ESP32_CAM)

        blur_threshold_min = 30.0 if is_esp32 else 80.0
        blur_target = 250.0 if is_esp32 else 500.0
        blur_factor = float(np.clip((blur_score - blur_threshold_min) / (blur_target - blur_threshold_min), 0.0, 1.0))

        # Contrast component (target RMS contrast ~ 0.20 - 0.45)
        contrast_factor = float(np.clip(rms_contrast / 0.30, 0.0, 1.0))

        # Noise component (lower noise sigma is better)
        max_acceptable_noise = 20.0 if is_esp32 else 10.0
        noise_factor = float(np.clip(1.0 - (noise_estimate / max_acceptable_noise), 0.0, 1.0))

        # Composite score weighting
        composite = (
            0.35 * blur_factor +
            0.35 * exposure_score +
            0.15 * contrast_factor +
            0.15 * noise_factor
        )
        composite = float(np.clip(composite, 0.0, 1.0))

        # Categorical rating
        if composite >= 0.75:
            rating = QualityRating.EXCELLENT
        elif composite >= 0.50:
            rating = QualityRating.USABLE
        elif composite >= 0.25:
            rating = QualityRating.DEGRADED
        else:
            rating = QualityRating.UNUSABLE

        return QualityMetrics(
            blur_score=blur_score,
            tenengrad_score=tenengrad,
            exposure_score=exposure_score,
            clipped_black_fraction=frac_black,
            clipped_white_fraction=frac_white,
            rms_contrast=rms_contrast,
            noise_estimate=noise_estimate,
            composite_quality=composite,
            rating=rating,
        )


def analyze_solar_image(*args, **kwargs):
    """Convenience wrapper re-exporting analyze_image from pipeline."""
    from ai.vision.pipeline import analyze_image
    return analyze_image(*args, **kwargs)
