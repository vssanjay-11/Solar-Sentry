"""Main Vision Pipeline & Orchestrator for Solar Sentry Agent 5 (Computer Vision).

Provides unified analysis interfaces:
- analyze_image(image, ...) -> VisionResult
- batch_analyze(images, ...) -> List[VisionResult]
- analyze_sequence(sequence, ...) -> List[VisionResult]
- generate_synthetic_solar_image(...) -> np.ndarray for automated offline testing
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional, Union

import cv2
import numpy as np

from ai.vision.ingestion import ImageIngestion, PreprocessedImage
from ai.vision.models import (
    ImageSourceType,
    ObstructionMetrics,
    ObstructionType,
    QualityMetrics,
    QualityRating,
    SolarDisk,
    SunspotCandidate,
    TemporalAnalysisResult,
    VisionResult,
)
from ai.vision.obstruction import ObstructionDetector
from ai.vision.preprocessor import ImagePreprocessor
from ai.vision.quality import ImageQualityAnalyzer
from ai.vision.solar_disk import SolarDiskDetector
from ai.vision.sunspot import SunspotDetector
from ai.vision.temporal import TemporalAnalyzer


class SolarVisionPipeline:
    """End-to-end solar computer vision pipeline."""

    def __init__(self) -> None:
        self.preprocessor = ImagePreprocessor()
        self.quality_analyzer = ImageQualityAnalyzer()
        self.disk_detector = SolarDiskDetector()
        self.sunspot_detector = SunspotDetector()
        self.obstruction_detector = ObstructionDetector()
        self.temporal_analyzer = TemporalAnalyzer()

    def analyze(
        self,
        image_input: Union[np.ndarray, bytes, str, PreprocessedImage],
        source_type: ImageSourceType = ImageSourceType.UPLOAD,
        reference_image: Optional[Union[np.ndarray, bytes, str, PreprocessedImage]] = None,
        image_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> VisionResult:
        """Executes full scientific analysis on a single solar image.

        Args:
            image_input: NumPy array, image bytes, file path, or PreprocessedImage.
            source_type: Hardware/source origin of the image.
            reference_image: Optional prior observation for temporal change detection.
            image_id: Optional tracking identifier.
            metadata: Optional sensor or telemetry metadata.

        Returns:
            Structured VisionResult containing metrics, detections, and disclaimers.
        """
        # 1. Ingest
        img = ImageIngestion.ingest(
            image_input,
            source_type=source_type,
            image_id=image_id,
            metadata=metadata,
        )

        ref_img: Optional[PreprocessedImage] = None
        if reference_image is not None:
            ref_img = ImageIngestion.ingest(
                reference_image,
                source_type=source_type,
                image_id=f"ref-{img.image_id}",
            )

        # 2. Preprocess & Enhance
        denoised_gray, enhanced_gray = self.preprocessor.process(img)

        # 3. Quality Assessment
        quality_metrics: QualityMetrics = self.quality_analyzer.analyze(img)

        # 4. Solar Disk Detection
        solar_disk: Optional[SolarDisk] = self.disk_detector.detect(enhanced_gray)
        solar_disk_detected = (solar_disk is not None)

        # 5. Sunspot Detection
        sunspots: List[SunspotCandidate] = []
        if solar_disk is not None:
            sunspots = self.sunspot_detector.detect(enhanced_gray, solar_disk)

        # 6. Obstruction & Cloud Detection
        obstruction_metrics: ObstructionMetrics = self.obstruction_detector.analyze(
            gray=denoised_gray,
            disk=solar_disk,
        )

        # 7. Temporal Comparison
        temporal_result: Optional[TemporalAnalysisResult] = None
        if ref_img is not None:
            temporal_result = self.temporal_analyzer.analyze(
                curr_gray=denoised_gray,
                ref_gray=ref_img.gray,
                curr_disk=solar_disk,
                curr_sunspots=sunspots,
            )

        # 8. High-level descriptive feature tagging
        features: List[str] = []
        if solar_disk_detected:
            features.append("SOLAR_DISK_ACQUIRED")
            if solar_disk.limb_darkening_fitted:
                features.append("LIMB_DARKENING_CONFIRMED")
            if solar_disk.is_clipped:
                features.append("DISK_MARGIN_CLIPPED")
        else:
            features.append("NO_SOLAR_DISK")

        if sunspots:
            features.append(f"ACTIVE_REGIONS_COUNT_{len(sunspots)}")
            if any(s.has_penumbra for s in sunspots):
                features.append("PENUMBRA_RESOLVED")
        else:
            if solar_disk_detected:
                features.append("QUIET_SUN_SURFACE")

        if obstruction_metrics.obstruction_type == ObstructionType.CLEAR:
            features.append("CLEAR_SKY")
        elif obstruction_metrics.obstruction_type == ObstructionType.PARTIAL_CLOUD:
            features.append("PARTIAL_CLOUD_OCCLUSION")
        elif obstruction_metrics.obstruction_type == ObstructionType.HEAVY_CLOUD:
            features.append("HEAVY_CLOUD_OVERCAST")
        elif obstruction_metrics.obstruction_type == ObstructionType.OVEREXPOSURE_GLARE:
            features.append("OVEREXPOSURE_GLARE")

        if temporal_result and temporal_result.motion_detected:
            features.append("TRACKING_JITTER_DETECTED")

        # 9. Hardware warnings
        warnings = list(img.hardware_notes)
        if quality_metrics.rating == QualityRating.DEGRADED:
            warnings.append("Image optical quality is degraded (low contrast, excessive noise, or blur).")
        elif quality_metrics.rating == QualityRating.UNUSABLE:
            warnings.append("Image is unusable for scientific solar tracking or measurement.")

        if obstruction_metrics.obstruction_score > 0.60:
            warnings.append("High visual obstruction detected. Solar tracking lock may be compromised.")

        # 10. Algorithm confidence estimation
        # Confidence reflects how certain the algorithm is in its visual extraction
        base_confidence = quality_metrics.composite_quality * (1.0 - 0.5 * obstruction_metrics.obstruction_score)
        if solar_disk_detected:
            disk_factor = 0.5 * solar_disk.circularity + (0.3 if solar_disk.limb_darkening_fitted else 0.0) + (0.2 if not solar_disk.is_clipped else 0.0)
            final_confidence = float(np.clip(0.6 * base_confidence + 0.4 * disk_factor, 0.05, 0.99))
        else:
            final_confidence = float(np.clip(base_confidence * 0.5, 0.05, 0.80))

        change_score = temporal_result.change_score if temporal_result else 0.0

        return VisionResult(
            image_id=img.image_id,
            timestamp=img.timestamp,
            source_type=img.source_type,
            image_width=img.width,
            image_height=img.height,
            quality_score=quality_metrics.composite_quality,
            solar_disk_detected=solar_disk_detected,
            sunspot_count=len(sunspots),
            features=features,
            obstruction_score=obstruction_metrics.obstruction_score,
            change_score=change_score,
            confidence=final_confidence,
            quality_metrics=quality_metrics,
            solar_disk=solar_disk,
            sunspots=sunspots,
            obstruction_metrics=obstruction_metrics,
            temporal_result=temporal_result,
            metadata=img.metadata,
            warnings=warnings,
        )


# Global default pipeline instance for simple functional access
_default_pipeline = SolarVisionPipeline()


def analyze_image(
    image: Union[np.ndarray, bytes, str, PreprocessedImage],
    source_type: ImageSourceType = ImageSourceType.UPLOAD,
    reference_image: Optional[Union[np.ndarray, bytes, str, PreprocessedImage]] = None,
    image_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> VisionResult:
    """Convenience functional wrapper for analyzing a single solar image."""
    return _default_pipeline.analyze(
        image_input=image,
        source_type=source_type,
        reference_image=reference_image,
        image_id=image_id,
        metadata=metadata,
    )


def batch_analyze(
    images: List[Union[np.ndarray, bytes, str, PreprocessedImage]],
    source_type: ImageSourceType = ImageSourceType.UPLOAD,
) -> List[VisionResult]:
    """Analyzes a collection of independent solar images."""
    return [_default_pipeline.analyze(img, source_type=source_type) for img in images]


def analyze_sequence(
    sequence: List[Union[np.ndarray, bytes, str, PreprocessedImage]],
    source_type: ImageSourceType = ImageSourceType.HISTORICAL,
) -> List[VisionResult]:
    """Analyzes an ordered time-series sequence, linking consecutive observations."""
    results: List[VisionResult] = []
    prior_image: Optional[Union[np.ndarray, bytes, str, PreprocessedImage]] = None

    for img in sequence:
        res = _default_pipeline.analyze(
            image_input=img,
            source_type=source_type,
            reference_image=prior_image,
        )
        results.append(res)
        prior_image = img

    return results


def generate_synthetic_solar_image(
    width: int = 400,
    height: int = 400,
    preset: str = "clear_with_sunspots",
    sunspot_count: int = 2,
    disk_radius_fraction: float = 0.35,
    seed: Optional[int] = 42,
) -> np.ndarray:
    """Generates a synthetic solar image for automated unit testing and simulation.

    Presets:
    - 'clear_with_sunspots': Clean disk, limb darkening, and dark sunspot features.
    - 'quiet_sun': Clean disk, limb darkening, no sunspots.
    - 'cloudy': Solar disk with passing cloud attenuation and occluded limb.
    - 'overexposed': Saturated white blowout with optical glare halo.
    - 'underexposed': Dim, low SNR disk.
    - 'blurry': Heavy Gaussian defocus.
    - 'esp32_cam_noisy': High sensor noise, mild vignetting, 8-bit quantization.
    - 'off_target': Dark sky with no solar disk.
    """
    if seed is not None:
        np.random.seed(seed)

    img = np.zeros((height, width), dtype=np.float32)
    cx, cy = width / 2.0, height / 2.0
    r = min(width, height) * disk_radius_fraction

    if preset == "off_target":
        # Pure dark sky background noise
        noise = np.random.normal(5.0, 2.0, (height, width))
        uint_noise = np.clip(noise, 0, 255).astype(np.uint8)
        return cv2.cvtColor(uint_noise, cv2.COLOR_GRAY2BGR)

    # 1. Base solar disk with Eddington-Barbier limb darkening
    # I(mu) = I_0 * [1 - u*(1 - mu)], mu = sqrt(1 - (dist/R)^2), u ~ 0.55
    y_idx, x_idx = np.indices((height, width))
    dist = np.sqrt((x_idx - cx) ** 2 + (y_idx - cy) ** 2)
    inside = dist <= r

    center_intensity = 220.0
    if preset == "underexposed":
        center_intensity = 60.0
    elif preset == "overexposed":
        center_intensity = 255.0

    mu = np.sqrt(np.maximum(0.0, 1.0 - (dist[inside] / r) ** 2))
    u = 0.55
    limb_intensity = center_intensity * (1.0 - u * (1.0 - mu))
    img[inside] = limb_intensity

    # 2. Add Sunspots
    if preset in ["clear_with_sunspots", "esp32_cam_noisy"] and sunspot_count > 0:
        for idx in range(sunspot_count):
            # Place sunspot randomly within 0.7 * r
            spot_angle = (idx * (2 * np.pi / sunspot_count)) + 0.3
            spot_dist = r * (0.2 + 0.3 * (idx % 2))
            sx = int(cx + spot_dist * np.cos(spot_angle))
            sy = int(cy + spot_dist * np.sin(spot_angle))
            spot_r = max(3, int(r * 0.05 * (1 + 0.5 * (idx % 2))))

            # Penumbra: lighter ring
            cv2.circle(img, (sx, sy), spot_r, float(center_intensity * 0.45), -1)
            # Umbra: intensely dark core
            cv2.circle(img, (sx, sy), max(1, int(spot_r * 0.5)), float(center_intensity * 0.20), -1)

    # 3. Add Clouds if requested
    if preset in ["cloudy", "heavy_clouds"]:
        attenuation = 0.88 if preset == "heavy_clouds" else 0.65
        cloud_width = 90.0 if preset == "heavy_clouds" else 45.0
        # Create a wavy cloud attenuation band across frame
        cloud_band = np.exp(-((y_idx - 0.8 * x_idx - 20) ** 2) / (2 * cloud_width**2))
        img[inside] *= (1.0 - attenuation * cloud_band[inside])
        # Background sky scattering
        scatter = 70.0 if preset == "heavy_clouds" else 35.0
        img[~inside] += (scatter * cloud_band[~inside])

    # 4. Overexposure / Glare halo
    if preset == "overexposed":
        halo = np.exp(-(dist**2) / (2 * (r * 1.6)**2)) * 255.0
        img = np.maximum(img, halo)
        img[dist <= r * 0.6] = 255.0

    # 5. ESP32-CAM Noise Profile & Vignetting
    if preset == "esp32_cam_noisy":
        # Add additive Gaussian sensor noise
        sensor_noise = np.random.normal(0.0, 6.0, (height, width))
        img += sensor_noise
        # Add lens vignetting (corners 20% darker)
        max_dist = np.sqrt(cx**2 + cy**2)
        vignette = 1.0 - 0.25 * (dist / max_dist) ** 2
        img *= vignette

    # 6. Blur preset
    uint_img = np.clip(img, 0, 255).astype(np.uint8)
    if preset == "blurry":
        uint_img = cv2.GaussianBlur(uint_img, (25, 25), 0)

    # Convert to 3-channel BGR image
    bgr = cv2.cvtColor(uint_img, cv2.COLOR_GRAY2BGR)
    return bgr
