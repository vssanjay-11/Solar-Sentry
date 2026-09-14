"""Solar Sentry — Computer Vision & Solar Image Intelligence Subsystem (Agent 5).

Provides structured image quality evaluation, solar disk localization, sunspot counting
and segmentation, visual obstruction detection, and temporal change tracking.
"""

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
from ai.vision.pipeline import (
    SolarVisionPipeline,
    analyze_image,
    analyze_sequence,
    batch_analyze,
    generate_synthetic_solar_image,
)

__all__ = [
    "ImageIngestion",
    "PreprocessedImage",
    "ImageSourceType",
    "QualityRating",
    "ObstructionType",
    "SolarDisk",
    "SunspotCandidate",
    "QualityMetrics",
    "ObstructionMetrics",
    "TemporalAnalysisResult",
    "VisionResult",
    "SolarVisionPipeline",
    "analyze_image",
    "batch_analyze",
    "analyze_sequence",
    "generate_synthetic_solar_image",
]
