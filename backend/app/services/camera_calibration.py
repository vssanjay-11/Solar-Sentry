"""
Solar Sentry — Camera Calibration & Optical Image Quality Engine
Supports prototype-grade optical adjustments, contrast enhancement, CLAHE,
unsharp masking, noise reduction, and objective image quality metrics calculation.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import cv2
import numpy as np

from ai.vision.pipeline import analyze_image
from ai.vision.models import ImageSourceType


@dataclass
class CalibrationParams:
    brightness: int = 0          # -100 to 100
    contrast: float = 1.0        # 0.5 to 3.0
    gamma: float = 1.0           # 0.2 to 2.5
    sharpness: float = 0.0       # 0.0 to 100.0
    saturation: float = 100.0    # 0.0 to 200.0 (%)
    noise_reduction: int = 0     # 0 to 10 (filter strength)
    apply_clahe: bool = False
    clahe_clip_limit: float = 2.0
    normalize_hist: bool = False
    invert_colors: bool = False
    rotation_deg: int = 0        # 0, 90, 180, 270


class OpticalQualityEngine:
    """Calculates objective optical quality metrics from image frame."""

    @staticmethod
    def calculate_metrics(bgr: np.ndarray) -> Dict[str, Any]:
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY) if len(bgr.shape) == 3 else bgr

        # 1. Brightness & Dynamic Range
        mean_brightness = float(np.mean(gray))
        min_val, max_val, _, _ = cv2.minMaxLoc(gray)
        dynamic_range = float(max_val - min_val)

        # 2. RMS Contrast
        rms_contrast = float(np.std(gray))

        # 3. Sharpness via Modified Laplacian Variance
        lap = cv2.Laplacian(gray, cv2.CV_64F, ksize=3)
        lap_var = float(np.var(lap))
        sharpness_score = round(min(100.0, lap_var / 12.0), 1)

        # 4. Tenengrad Focus Measure
        gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        tenengrad = float(np.mean(gx**2 + gy**2))

        # 5. Exposure Fidelity (Clipped pixel fractions)
        total_pixels = float(gray.size)
        clipped_black = float(np.count_nonzero(gray <= 4) / total_pixels)
        clipped_white = float(np.count_nonzero(gray >= 251) / total_pixels)
        exposure_fidelity = round(max(0.0, 100.0 * (1.0 - (clipped_black * 0.4 + clipped_white * 1.5))), 1)

        # 6. High-Frequency Noise (MAD)
        med = np.median(gray)
        mad = float(np.median(np.abs(gray - med)))
        noise_level = round(min(100.0, mad * 2.5), 1)

        # 7. Blur Estimation
        blur_score = round(max(0.0, 100.0 - sharpness_score), 1)

        # 8. Overall Image Quality Score (0 - 100)
        # Combines sharpness, exposure, contrast, and noise
        contrast_component = min(100.0, (rms_contrast / 64.0) * 100.0)
        overall_score = round(
            0.35 * sharpness_score +
            0.30 * exposure_fidelity +
            0.20 * contrast_component +
            0.15 * max(0.0, 100.0 - noise_level * 0.8),
            1
        )
        overall_score = max(0.0, min(100.0, overall_score))

        return {
            "overall_quality_score": overall_score,
            "composite_score": overall_score,
            "quality_score": overall_score,
            "sharpness": sharpness_score,
            "exposure_quality": exposure_fidelity,
            "contrast": round(contrast_component, 1),
            "dynamic_range": round(dynamic_range, 1),
            "mean_brightness": round(mean_brightness, 1),
            "blur_estimate": blur_score,
            "noise_level": noise_level,
            "tenengrad": round(tenengrad, 1),
            "clipped_black_pct": round(clipped_black * 100.0, 2),
            "clipped_white_pct": round(clipped_white * 100.0, 2)
        }



class CameraCalibrationService:
    """Applies prototype-grade optical adjustments and returns processed frame with metrics."""

    @staticmethod
    def process_image(
        raw_bytes: bytes,
        params: CalibrationParams
    ) -> Tuple[bytes, Dict[str, Any], Dict[str, Any]]:
        """
        Takes raw JPEG image bytes, applies calibration and enhancement parameters,
        and returns: (processed_jpeg_bytes, quality_metrics, vision_analysis_summary)
        NEVER mutates or overwrites the original raw image bytes.
        """
        # Decode BGR image
        np_arr = np.frombuffer(raw_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Could not decode image from provided raw bytes.")

        processed = img.copy().astype(np.float32)

        # 1. Rotation
        if params.rotation_deg == 90:
            processed = cv2.rotate(processed, cv2.ROTATE_90_CLOCKWISE)
        elif params.rotation_deg == 180:
            processed = cv2.rotate(processed, cv2.ROTATE_180)
        elif params.rotation_deg == 270:
            processed = cv2.rotate(processed, cv2.ROTATE_90_COUNTERCLOCKWISE)

        # 2. Brightness & Contrast
        # formula: out = contrast * in + brightness
        processed = processed * float(params.contrast) + float(params.brightness)
        processed = np.clip(processed, 0, 255)

        # 3. Gamma Correction
        if abs(params.gamma - 1.0) > 0.01 and params.gamma > 0.1:
            inv_gamma = 1.0 / params.gamma
            table = ((np.arange(256) / 255.0) ** inv_gamma) * 255.0
            table = np.clip(table, 0, 255).astype(np.uint8)
            processed = cv2.LUT(processed.astype(np.uint8), table).astype(np.float32)

        # Convert to uint8 for advanced filters
        uint8_img = np.clip(processed, 0, 255).astype(np.uint8)

        # 4. Saturation (HSV space)
        if abs(params.saturation - 100.0) > 1.0:
            hsv = cv2.cvtColor(uint8_img, cv2.COLOR_BGR2HSV).astype(np.float32)
            hsv[:, :, 1] = np.clip(hsv[:, :, 1] * (params.saturation / 100.0), 0, 255)
            uint8_img = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

        # 5. Noise Reduction (Bilateral / Edge-preserving)
        if params.noise_reduction > 0:
            d = min(9, 3 + params.noise_reduction)
            sigma = params.noise_reduction * 10.0
            uint8_img = cv2.bilateralFilter(uint8_img, d=d, sigmaColor=sigma, sigmaSpace=sigma)

        # 6. CLAHE / Histogram Equalization
        if params.apply_clahe:
            lab = cv2.cvtColor(uint8_img, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=max(0.5, params.clahe_clip_limit), tileGridSize=(8, 8))
            l = clahe.apply(l)
            lab = cv2.merge((l, a, b))
            uint8_img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        elif params.normalize_hist:
            lab = cv2.cvtColor(uint8_img, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            l = cv2.equalizeHist(l)
            lab = cv2.merge((l, a, b))
            uint8_img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

        # 7. Sharpness via Unsharp Masking
        if params.sharpness > 0:
            gaussian = cv2.GaussianBlur(uint8_img, (0, 0), sigmaX=2.0)
            amount = float(params.sharpness) / 50.0  # 0 to 2.0 weight
            uint8_img = cv2.addWeighted(uint8_img, 1.0 + amount, gaussian, -amount, 0)
            uint8_img = np.clip(uint8_img, 0, 255).astype(np.uint8)

        # 8. Invert colors (useful for negative sunspot contrast inspection)
        if params.invert_colors:
            uint8_img = cv2.bitwise_not(uint8_img)

        # Calculate optical quality metrics on calibrated image
        metrics = OpticalQualityEngine.calculate_metrics(uint8_img)

        # Run computer vision solar disk analysis on processed image
        vision_summary = {}
        try:
            vis_res = analyze_image(uint8_img, source_type=ImageSourceType.UPLOAD)
            vision_summary = {
                "disk_detected": vis_res.solar_disk_detected,
                "sunspot_count": vis_res.sunspot_count,
                "features": vis_res.features,
                "obstruction_score": vis_res.obstruction_score,
                "confidence": vis_res.confidence,
                "solar_disk": vis_res.solar_disk.model_dump() if vis_res.solar_disk else None,
                "sunspots": [s.model_dump() for s in vis_res.sunspots]
            }
        except Exception:
            pass

        # Encode processed JPEG
        ok, enc = cv2.imencode(".jpg", uint8_img, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
        if not ok:
            raise RuntimeError("Failed to encode processed JPEG image.")

        return enc.tobytes(), metrics, vision_summary

    @staticmethod
    def auto_enhance_params() -> CalibrationParams:
        """Generates optimal baseline enhancements for solar disk observation."""
        return CalibrationParams(
            brightness=5,
            contrast=1.2,
            gamma=1.05,
            sharpness=25.0,
            saturation=105.0,
            noise_reduction=2,
            apply_clahe=True,
            clahe_clip_limit=2.0,
            normalize_hist=False,
            invert_colors=False,
            rotation_deg=0
        )
