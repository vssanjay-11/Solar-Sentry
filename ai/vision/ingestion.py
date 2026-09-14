"""Image ingestion abstraction for Solar Sentry Agent 5 (Computer Vision).

Provides unified ingestion from heterogeneous solar image sources:
- ESP32-CAM prototype (OV2640 sensor streams/captures)
- User uploaded files
- Historical solar observatory archives (e.g. SDO/SOHO/Kanzelhöhe proxies)
- Direct observatory feeds
- Synthetic simulation frames
"""

from __future__ import annotations

import base64
import datetime
import os
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Union

import cv2
import numpy as np

from ai.vision.models import ImageSourceType


@dataclass
class PreprocessedImage:
    """Standardized multi-channel internal representation of an ingested solar image."""
    image_id: str
    source_type: ImageSourceType
    raw_bgr: np.ndarray
    gray: np.ndarray
    rgb: np.ndarray
    float_gray: np.ndarray  # Normalized to [0.0, 1.0]
    width: int
    height: int
    timestamp: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    hardware_notes: list[str] = field(default_factory=list)


class ImageIngestion:
    """Unified ingestion service normalizing images into standardized internal representations."""

    @staticmethod
    def _create_preprocessed_image(
        bgr_image: np.ndarray,
        source_type: ImageSourceType,
        image_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[str] = None,
    ) -> PreprocessedImage:
        """Helper to build PreprocessedImage from standard uint8 BGR array."""
        if bgr_image is None or not isinstance(bgr_image, np.ndarray) or bgr_image.size == 0:
            raise ValueError("Ingestion failed: input image array is empty or None.")

        if len(bgr_image.shape) == 2:
            # Grayscale provided, convert to BGR
            gray = bgr_image.copy()
            bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
            rgb = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
        elif len(bgr_image.shape) == 3:
            if bgr_image.shape[2] == 4:
                # BGRA -> BGR
                bgr = cv2.cvtColor(bgr_image, cv2.COLOR_BGRA2BGR)
            else:
                bgr = bgr_image.copy()
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        else:
            raise ValueError(f"Invalid image dimensions: {bgr_image.shape}")

        height, width = gray.shape
        float_gray = gray.astype(np.float32) / 255.0

        assigned_id = image_id or f"img-{uuid.uuid4().hex[:10]}"
        meta = dict(metadata or {})
        notes: list[str] = []

        # Source-specific profiling and hardware notes
        if source_type == ImageSourceType.ESP32_CAM:
            notes.append("Ingested from ESP32-CAM (OV2640). Rolling shutter, 8-bit dynamic range, and JPEG compression artifacts expected.")
            meta["sensor_class"] = "environmental_prototype_ov2640"
        elif source_type == ImageSourceType.OBSERVATORY:
            notes.append("Ingested from observatory-grade optical instrument.")
            meta["sensor_class"] = "observatory_grade"
        elif source_type == ImageSourceType.HISTORICAL:
            notes.append("Ingested from historical solar observation archive.")
            meta["sensor_class"] = "historical_archive"
        elif source_type == ImageSourceType.SIMULATION:
            notes.append("Ingested from synthetic solar simulation generator.")
            meta["sensor_class"] = "synthetic_simulation"

        return PreprocessedImage(
            image_id=assigned_id,
            source_type=source_type,
            raw_bgr=bgr,
            gray=gray,
            rgb=rgb,
            float_gray=float_gray,
            width=width,
            height=height,
            timestamp=timestamp or datetime.datetime.now(datetime.timezone.utc).isoformat(),
            metadata=meta,
            hardware_notes=notes,
        )

    @classmethod
    def from_numpy(
        cls,
        array: np.ndarray,
        source_type: ImageSourceType = ImageSourceType.UPLOAD,
        image_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[str] = None,
    ) -> PreprocessedImage:
        """Ingest directly from an in-memory NumPy array (BGR, RGB, or Grayscale)."""
        if array is None or array.size == 0:
            raise ValueError("Input numpy array is empty.")
        
        # If float array provided in [0.0, 1.0], scale to uint8
        if array.dtype in [np.float32, np.float64]:
            if array.max() <= 1.01:
                array = np.clip(array * 255.0, 0, 255).astype(np.uint8)
            else:
                array = np.clip(array, 0, 255).astype(np.uint8)
        elif array.dtype != np.uint8:
            array = np.clip(array, 0, 255).astype(np.uint8)

        return cls._create_preprocessed_image(
            bgr_image=array,
            source_type=source_type,
            image_id=image_id,
            metadata=metadata,
            timestamp=timestamp,
        )

    @classmethod
    def from_bytes(
        cls,
        data: bytes,
        source_type: ImageSourceType = ImageSourceType.UPLOAD,
        image_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[str] = None,
    ) -> PreprocessedImage:
        """Ingest from encoded image bytes (JPEG, PNG, WebP, etc.)."""
        if not data or len(data) == 0:
            raise ValueError("Empty image byte buffer received.")

        np_arr = np.frombuffer(data, np.uint8)
        decoded = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if decoded is None:
            raise ValueError("Failed to decode image bytes. Unsupported or corrupted format.")

        return cls._create_preprocessed_image(
            bgr_image=decoded,
            source_type=source_type,
            image_id=image_id,
            metadata=metadata,
            timestamp=timestamp,
        )

    @classmethod
    def from_file(
        cls,
        file_path: str,
        source_type: Optional[ImageSourceType] = None,
        image_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PreprocessedImage:
        """Ingest an image from local filesystem path."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Solar image file does not exist: {file_path}")

        img = cv2.imread(file_path, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError(f"OpenCV could not read image from path: {file_path}")

        assigned_source = source_type or ImageSourceType.UPLOAD
        assigned_id = image_id or os.path.splitext(os.path.basename(file_path))[0]
        meta = metadata or {}
        meta["file_path"] = file_path
        meta["file_size_bytes"] = os.path.getsize(file_path)

        return cls._create_preprocessed_image(
            bgr_image=img,
            source_type=assigned_source,
            image_id=assigned_id,
            metadata=meta,
        )

    @classmethod
    def from_base64(
        cls,
        b64_string: str,
        source_type: ImageSourceType = ImageSourceType.UPLOAD,
        image_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PreprocessedImage:
        """Ingest from a base64 encoded image string (e.g. data URI or API payload)."""
        if not b64_string:
            raise ValueError("Empty base64 string provided.")

        if "," in b64_string:
            b64_string = b64_string.split(",", 1)[1]

        try:
            raw_bytes = base64.b64decode(b64_string)
        except Exception as err:
            raise ValueError(f"Invalid base64 payload: {err}") from err

        return cls.from_bytes(
            data=raw_bytes,
            source_type=source_type,
            image_id=image_id,
            metadata=metadata,
        )

    @classmethod
    def ingest(
        cls,
        image_input: Union[np.ndarray, bytes, str, PreprocessedImage],
        source_type: ImageSourceType = ImageSourceType.UPLOAD,
        image_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PreprocessedImage:
        """Polymorphic entry point for any supported input format."""
        if isinstance(image_input, PreprocessedImage):
            return image_input
        elif isinstance(image_input, np.ndarray):
            return cls.from_numpy(image_input, source_type=source_type, image_id=image_id, metadata=metadata)
        elif isinstance(image_input, bytes):
            return cls.from_bytes(image_input, source_type=source_type, image_id=image_id, metadata=metadata)
        elif isinstance(image_input, str):
            if os.path.exists(image_input):
                return cls.from_file(image_input, source_type=source_type, image_id=image_id, metadata=metadata)
            else:
                return cls.from_base64(image_input, source_type=source_type, image_id=image_id, metadata=metadata)
        else:
            raise TypeError(f"Unsupported image input type: {type(image_input)}")
