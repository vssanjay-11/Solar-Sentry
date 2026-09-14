"""Image preprocessing pipeline for Solar Sentry Agent 5 (Computer Vision).

Applies photometric corrections, contrast equalization, edge-preserving denoising,
and flat-field correction tailored for both low-cost CMOS lenses (ESP32-CAM) and
scientific solar images.
"""

from __future__ import annotations

from typing import Tuple

import cv2
import numpy as np

from ai.vision.ingestion import PreprocessedImage
from ai.vision.models import ImageSourceType


class ImagePreprocessor:
    """Preprocesses raw solar frames to maximize SNR and edge definition."""

    def __init__(
        self,
        clahe_clip_limit: float = 2.0,
        clahe_tile_grid_size: Tuple[int, int] = (8, 8),
        bilateral_d: int = 5,
        bilateral_sigma_color: float = 50.0,
        bilateral_sigma_space: float = 50.0,
    ) -> None:
        self.clahe_clip_limit = clahe_clip_limit
        self.clahe_tile_grid_size = clahe_tile_grid_size
        self.bilateral_d = bilateral_d
        self.bilateral_sigma_color = bilateral_sigma_color
        self.bilateral_sigma_space = bilateral_sigma_space
        self._clahe = cv2.createCLAHE(
            clipLimit=self.clahe_clip_limit,
            tileGridSize=self.clahe_tile_grid_size,
        )

    def apply_clahe(self, gray: np.ndarray) -> np.ndarray:
        """Enhances local contrast while preventing over-amplification of noise."""
        return self._clahe.apply(gray)

    def apply_bilateral_denoising(self, image: np.ndarray) -> np.ndarray:
        """Denoises image while preserving sharp solar disk and sunspot edges."""
        return cv2.bilateralFilter(
            image,
            d=self.bilateral_d,
            sigmaColor=self.bilateral_sigma_color,
            sigmaSpace=self.bilateral_sigma_space,
        )

    def correct_vignetting(self, gray: np.ndarray, strength: float = 0.25) -> np.ndarray:
        """Synthetic radial flat-field correction for low-cost wide lenses (e.g. OV2640).

        Corrects cosine-fourth lens falloff near frame edges.
        """
        h, w = gray.shape
        cy, cx = h / 2.0, w / 2.0
        max_r = np.sqrt(cx**2 + cy**2)

        y_indices, x_indices = np.indices((h, w))
        r = np.sqrt((x_indices - cx) ** 2 + (y_indices - cy) ** 2) / max_r

        # Vignetting attenuation model: 1 / (1 - strength * r^2)
        gain = 1.0 + strength * (r ** 2)
        corrected = gray.astype(np.float32) * gain
        return np.clip(corrected, 0, 255).astype(np.uint8)

    def process(self, preprocessed: PreprocessedImage) -> Tuple[np.ndarray, np.ndarray]:
        """Preprocesses the ingested image.

        Returns:
            Tuple of (denoised_gray, enhanced_contrast_gray)
        """
        gray = preprocessed.gray

        # If source is low-cost CMOS (ESP32-CAM), apply radial vignetting compensation
        if preprocessed.source_type == ImageSourceType.ESP32_CAM:
            gray = self.correct_vignetting(gray, strength=0.20)

        # Apply edge-preserving smoothing
        denoised = self.apply_bilateral_denoising(gray)

        # Apply contrast-limited adaptive histogram equalization
        enhanced = self.apply_clahe(denoised)

        return denoised, enhanced


def generate_synthetic_solar_image(*args, **kwargs) -> np.ndarray:
    """Convenience wrapper re-exporting synthetic solar frame generator from pipeline."""
    from ai.vision.pipeline import generate_synthetic_solar_image as _gen
    if "condition" in kwargs and "preset" not in kwargs:
        cond = kwargs.pop("condition")
        if cond in ("clear", "optimal", "clear_sky"):
            kwargs["preset"] = "clear_with_sunspots"
        elif cond in ("cloudy", "clouds"):
            kwargs["preset"] = "cloudy"
        elif cond == "heavy_clouds":
            kwargs["preset"] = "heavy_clouds"
        elif cond in ("blurry", "blur"):
            kwargs["preset"] = "blurry"
        elif cond == "overexposed":
            kwargs["preset"] = "overexposed"
        elif cond == "underexposed":
            kwargs["preset"] = "underexposed"
        else:
            kwargs["preset"] = cond
    return _gen(*args, **kwargs)

