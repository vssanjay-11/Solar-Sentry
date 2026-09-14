"""Data contracts and serialization schemas for Solar Sentry Agent 5 (Computer Vision).

Defines structured models for image quality, solar disk geometry, sunspot detections,
atmospheric obstructions, temporal comparisons, and overall vision analysis results.
"""

from __future__ import annotations

import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class ImageSourceType(str, Enum):
    """Supported source origins for solar imagery."""
    ESP32_CAM = "ESP32_CAM"
    UPLOAD = "UPLOAD"
    HISTORICAL = "HISTORICAL"
    OBSERVATORY = "OBSERVATORY"
    SIMULATION = "SIMULATION"


class QualityRating(str, Enum):
    """Categorical quality tier based on composite score."""
    EXCELLENT = "EXCELLENT"
    USABLE = "USABLE"
    DEGRADED = "DEGRADED"
    UNUSABLE = "UNUSABLE"


class ObstructionType(str, Enum):
    """Visual obstruction classification."""
    CLEAR = "CLEAR"
    PARTIAL_CLOUD = "PARTIAL_CLOUD"
    HEAVY_CLOUD = "HEAVY_CLOUD"
    OVEREXPOSURE_GLARE = "OVEREXPOSURE_GLARE"
    OFF_TARGET = "OFF_TARGET"


class SolarDisk(BaseModel):
    """Geometric and photometric characterization of the detected solar disk."""
    center_x: float = Field(..., description="Disk centroid X in pixel coordinates")
    center_y: float = Field(..., description="Disk centroid Y in pixel coordinates")
    radius: float = Field(..., ge=0.0, description="Disk radius in pixels")
    circularity: float = Field(..., ge=0.0, le=1.0, description="Form factor 4*pi*Area / Perimeter^2")
    is_clipped: bool = Field(False, description="True if disk boundary touches or exceeds image margins")
    limb_darkening_fitted: bool = Field(False, description="True if radial profile matches expected solar limb darkening")
    mean_photosphere_intensity: float = Field(0.0, ge=0.0, le=255.0, description="Average quiet photosphere intensity (0-255)")
    bounding_box: Tuple[int, int, int, int] = Field(..., description="(x, y, w, h) of disk bounding box")


class SunspotCandidate(BaseModel):
    """Detected candidate sunspot or dark solar feature."""
    id: int = Field(..., description="Index identifier for this candidate within the frame")
    centroid_x: float = Field(..., description="Centroid X in full image coordinates")
    centroid_y: float = Field(..., description="Centroid Y in full image coordinates")
    disk_relative_r: float = Field(..., ge=0.0, le=1.0, description="Normalized radial distance from disk center [0=center, 1=limb]")
    disk_relative_theta_deg: float = Field(..., ge=0.0, le=360.0, description="Polar angle from disk center (degrees)")
    area_pixels: int = Field(..., ge=1, description="Pixel footprint area")
    relative_area_fraction: float = Field(..., ge=0.0, description="Fraction of solar disk area")
    min_intensity: float = Field(..., ge=0.0, le=255.0, description="Minimum pixel intensity in spot core")
    contrast_ratio: float = Field(..., ge=0.0, le=1.0, description="Darkness ratio relative to surrounding photosphere")
    has_penumbra: bool = Field(False, description="True if intermediate penumbral intensity halo is resolved")
    umbra_area_pixels: int = Field(0, description="Area of deep umbral core")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence that candidate is a genuine solar feature vs sensor artifact")


class QualityMetrics(BaseModel):
    """Objective optical and digital quality measurements."""
    blur_score: float = Field(..., ge=0.0, description="Modified Laplacian variance sharpness metric")
    tenengrad_score: float = Field(..., ge=0.0, description="Tenengrad gradient energy density")
    exposure_score: float = Field(..., ge=0.0, le=1.0, description="Dynamic range fidelity (1.0 = well exposed, 0.0 = crushed/blown)")
    clipped_black_fraction: float = Field(..., ge=0.0, le=1.0, description="Fraction of under-saturated pixels (< 5)")
    clipped_white_fraction: float = Field(..., ge=0.0, le=1.0, description="Fraction of over-saturated pixels (> 250)")
    rms_contrast: float = Field(..., ge=0.0, description="Root mean square luminance contrast")
    noise_estimate: float = Field(..., ge=0.0, description="High-frequency noise sigma via Median Absolute Deviation (MAD)")
    composite_quality: float = Field(..., ge=0.0, le=1.0, description="Normalized composite quality index")
    rating: QualityRating = Field(..., description="Categorical quality tier")


class ObstructionMetrics(BaseModel):
    """Atmospheric and environmental visual obstruction metrics."""
    obstruction_score: float = Field(..., ge=0.0, le=1.0, description="Overall occlusion index (0.0=clear, 1.0=fully obstructed)")
    cloud_fraction: float = Field(..., ge=0.0, le=1.0, description="Estimated cloud fraction across field of view")
    glare_fraction: float = Field(..., ge=0.0, le=1.0, description="Saturated glare / scattering fraction")
    limb_integrity: float = Field(..., ge=0.0, le=1.0, description="Consistency of solar perimeter profile")
    obstruction_type: ObstructionType = Field(..., description="Categorical obstruction class")


class TemporalAnalysisResult(BaseModel):
    """Differential analysis between current image and a reference/previous observation."""
    has_reference: bool = Field(False, description="True if a reference frame was provided")
    registered_successfully: bool = Field(False, description="True if sub-pixel registration succeeded")
    translation_x: float = Field(0.0, description="Horizontal registration offset in pixels")
    translation_y: float = Field(0.0, description="Vertical registration offset in pixels")
    rotation_deg: float = Field(0.0, description="Rotational registration offset in degrees")
    change_score: float = Field(0.0, ge=0.0, le=1.0, description="Normalized photometric/structural change index")
    motion_detected: bool = Field(False, description="True if jitter or movement beyond threshold was detected")
    transient_feature_count: int = Field(0, description="Number of newly emerged or displaced features")


class VisionResult(BaseModel):
    """Authoritative structured output produced by Agent 5 (Computer Vision)."""
    image_id: str = Field(..., description="Unique identifier of analyzed image")
    timestamp: str = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp of analysis"
    )
    source_type: ImageSourceType = Field(..., description="Data source origin of image")
    image_width: int = Field(..., ge=1, description="Image width in pixels")
    image_height: int = Field(..., ge=1, description="Image height in pixels")
    
    # Core Summary Scores
    quality_score: float = Field(..., ge=0.0, le=1.0, description="Composite optical quality score (0.0-1.0)")
    solar_disk_detected: bool = Field(..., description="True if solar disk was identified and localized")
    sunspot_count: int = Field(0, ge=0, description="Count of confirmed sunspot candidates")
    features: List[str] = Field(default_factory=list, description="High-level descriptive solar feature tags")
    obstruction_score: float = Field(..., ge=0.0, le=1.0, description="Visual obstruction index (0.0=clear, 1.0=blocked)")
    change_score: float = Field(0.0, ge=0.0, le=1.0, description="Temporal change score relative to prior frame")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall algorithm confidence score")
    
    # Detailed Subsystem Payloads
    quality_metrics: QualityMetrics = Field(..., description="Detailed sharpness, exposure, and noise breakdown")
    solar_disk: Optional[SolarDisk] = Field(None, description="Detailed disk coordinates and limb profile if detected")
    sunspots: List[SunspotCandidate] = Field(default_factory=list, description="List of detected sunspots with coordinates and areas")
    obstruction_metrics: ObstructionMetrics = Field(..., description="Detailed atmospheric obstruction breakdown")
    temporal_result: Optional[TemporalAnalysisResult] = Field(None, description="Registration and change detection details")
    
    # Metadata & Scientific Disclaimers
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary ingestion or sensor metadata")
    warnings: List[str] = Field(default_factory=list, description="Operational warnings or hardware caveats")
    limitations_disclaimer: str = Field(
        default="Solar Sentry Agent 5 provides solar feature localization and optical quality metrics. "
                "DO NOT use this module for solar flare prediction; reliable flare forecasting requires "
                "calibrated vector magnetograms and dedicated spaceborne instrument data.",
        description="Mandatory scientific disclaimer on model capabilities"
    )

    def to_json(self, indent: int = 2) -> str:
        """Serialize result to formatted JSON string."""
        return self.model_dump_json(indent=indent)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize result to nested dictionary."""
        return self.model_dump()
