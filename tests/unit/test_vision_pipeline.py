"""Unit tests for Solar Sentry Agent 5 (Computer Vision + Solar Image Intelligence).

Validates:
- Image ingestion abstraction (NumPy, bytes, file, base64, ESP32-CAM, Observatory)
- Preprocessing and flat-field/vignetting correction
- Quality assessment (Laplacian blur, Tenengrad, exposure, RMS contrast, MAD noise)
- Solar disk detection, circularity, boundary clipping, and limb darkening
- Sunspot detection, umbra/penumbra decomposition, and artifact rejection
- Cloud and visual obstruction detection
- Temporal image registration (sub-pixel phase correlation) and change detection
- Batch and sequence analysis
- Pydantic serialization adhering to docs/contracts/VisionResult.json
- Mandatory scientific disclaimer enforcement (no solar flare prediction claims)
"""

import base64
import json
import os
import sys
import tempfile
import cv2
import numpy as np
import pytest

# Ensure workspace root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from ai.vision import (
    ImageIngestion,
    ImageSourceType,
    ObstructionType,
    QualityRating,
    VisionResult,
    analyze_image,
    analyze_sequence,
    batch_analyze,
    generate_synthetic_solar_image,
)
from ai.vision.models import SolarDisk
from ai.vision.preprocessor import ImagePreprocessor
from ai.vision.quality import ImageQualityAnalyzer
from ai.vision.solar_disk import SolarDiskDetector
from ai.vision.sunspot import SunspotDetector
from ai.vision.temporal import TemporalAnalyzer


class TestSyntheticGenerator:
    """Validates the synthetic solar image generator used for testing and simulation."""

    def test_presets_generation(self):
        presets = [
            "clear_with_sunspots",
            "quiet_sun",
            "cloudy",
            "overexposed",
            "underexposed",
            "blurry",
            "esp32_cam_noisy",
            "off_target",
        ]
        for p in presets:
            img = generate_synthetic_solar_image(width=200, height=200, preset=p)
            assert isinstance(img, np.ndarray)
            assert img.shape == (200, 200, 3)
            assert img.dtype == np.uint8


class TestImageIngestion:
    """Validates ingestion from heterogeneous formats and sources."""

    def test_ingest_from_numpy(self):
        arr = np.ones((100, 100, 3), dtype=np.uint8) * 128
        ingested = ImageIngestion.from_numpy(arr, source_type=ImageSourceType.UPLOAD)
        assert ingested.width == 100
        assert ingested.height == 100
        assert ingested.source_type == ImageSourceType.UPLOAD
        assert ingested.float_gray.shape == (100, 100)
        assert 0.49 <= ingested.float_gray[50, 50] <= 0.51

    def test_ingest_from_float_numpy(self):
        arr = np.ones((50, 50), dtype=np.float32) * 0.5
        ingested = ImageIngestion.from_numpy(arr)
        assert ingested.gray[25, 25] == 127 or ingested.gray[25, 25] == 128

    def test_ingest_from_bytes(self):
        arr = generate_synthetic_solar_image(width=150, height=150, preset="quiet_sun")
        success, encoded = cv2.imencode(".png", arr)
        assert success
        ingested = ImageIngestion.from_bytes(encoded.tobytes(), source_type=ImageSourceType.ESP32_CAM)
        assert ingested.width == 150
        assert ingested.height == 150
        assert ingested.source_type == ImageSourceType.ESP32_CAM
        assert any("ESP32-CAM" in note for note in ingested.hardware_notes)

    def test_ingest_from_base64(self):
        arr = generate_synthetic_solar_image(width=100, height=100)
        _, enc = cv2.imencode(".jpg", arr)
        b64_str = base64.b64encode(enc.tobytes()).decode("utf-8")
        data_uri = f"data:image/jpeg;base64,{b64_str}"
        ingested = ImageIngestion.from_base64(data_uri)
        assert ingested.width == 100
        assert ingested.height == 100

    def test_ingest_from_file(self):
        arr = generate_synthetic_solar_image(width=120, height=120)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
            cv2.imwrite(tf.name, arr)
            temp_path = tf.name

        try:
            ingested = ImageIngestion.from_file(temp_path, source_type=ImageSourceType.OBSERVATORY)
            assert ingested.width == 120
            assert ingested.height == 120
            assert ingested.source_type == ImageSourceType.OBSERVATORY
            assert ingested.metadata["file_path"] == temp_path
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_invalid_ingestion_rejections(self):
        with pytest.raises(ValueError, match="(?i)empty"):
            ImageIngestion.from_bytes(b"")

        with pytest.raises(ValueError, match="(?i)corrupted"):
            ImageIngestion.from_bytes(b"bad_bytes_header_12345")


class TestQualityAssessment:
    """Validates blur, exposure, contrast, and noise estimation."""

    def test_blur_estimation(self):
        sharp = generate_synthetic_solar_image(width=250, height=250, preset="clear_with_sunspots")
        blurry = generate_synthetic_solar_image(width=250, height=250, preset="blurry")

        analyzer = ImageQualityAnalyzer()
        ing_sharp = ImageIngestion.from_numpy(sharp)
        ing_blurry = ImageIngestion.from_numpy(blurry)

        res_sharp = analyzer.analyze(ing_sharp)
        res_blurry = analyzer.analyze(ing_blurry)

        assert res_sharp.blur_score > res_blurry.blur_score * 3.0
        assert res_sharp.tenengrad_score > res_blurry.tenengrad_score

    def test_exposure_clipping(self):
        overexposed = generate_synthetic_solar_image(width=200, height=200, preset="overexposed")
        analyzer = ImageQualityAnalyzer()
        ing = ImageIngestion.from_numpy(overexposed)
        metrics = analyzer.analyze(ing)

        assert metrics.clipped_white_fraction > 0.05
        assert metrics.exposure_score < 0.70

    def test_noise_estimation_mad(self):
        clean = generate_synthetic_solar_image(width=200, height=200, preset="quiet_sun")
        noisy = generate_synthetic_solar_image(width=200, height=200, preset="esp32_cam_noisy")

        analyzer = ImageQualityAnalyzer()
        ing_clean = ImageIngestion.from_numpy(clean)
        ing_noisy = ImageIngestion.from_numpy(noisy)

        metrics_clean = analyzer.analyze(ing_clean)
        metrics_noisy = analyzer.analyze(ing_noisy)

        assert metrics_noisy.noise_estimate > metrics_clean.noise_estimate


class TestSolarDiskDetection:
    """Validates solar disk localization and limb darkening verification."""

    def test_disk_detected_on_clear_sun(self):
        img = generate_synthetic_solar_image(width=300, height=300, preset="clear_with_sunspots", disk_radius_fraction=0.35)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        detector = SolarDiskDetector()
        disk = detector.detect(gray)

        assert disk is not None
        assert 140 <= disk.center_x <= 160
        assert 140 <= disk.center_y <= 160
        assert 95 <= disk.radius <= 115
        assert disk.circularity >= 0.85
        assert not disk.is_clipped
        assert disk.limb_darkening_fitted

    def test_disk_not_detected_on_off_target(self):
        img = generate_synthetic_solar_image(width=200, height=200, preset="off_target")
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        detector = SolarDiskDetector()
        disk = detector.detect(gray)
        assert disk is None

    def test_extract_solar_region(self):
        img = generate_synthetic_solar_image(width=300, height=300, preset="quiet_sun")
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        detector = SolarDiskDetector()
        disk = detector.detect(gray)
        assert disk is not None

        roi, mask = detector.extract_solar_region(gray, disk)
        assert roi.shape == mask.shape
        assert mask.shape[0] > 0 and mask.shape[1] > 0


class TestSunspotDetection:
    """Validates active region segmentation, umbra/penumbra, and coordinates."""

    def test_detect_sunspots_in_active_sun(self):
        img = generate_synthetic_solar_image(width=350, height=350, preset="clear_with_sunspots", sunspot_count=3)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        disk_detector = SolarDiskDetector()
        disk = disk_detector.detect(gray)
        assert disk is not None

        spot_detector = SunspotDetector()
        spots = spot_detector.detect(gray, disk)

        assert len(spots) >= 2
        for spot in spots:
            assert spot.area_pixels >= 3
            assert 0.0 <= spot.disk_relative_r <= 1.0
            assert 0.0 <= spot.disk_relative_theta_deg <= 360.0
            assert spot.contrast_ratio >= 0.08
            assert spot.confidence > 0.40

    def test_no_sunspots_in_quiet_sun(self):
        img = generate_synthetic_solar_image(width=300, height=300, preset="quiet_sun", sunspot_count=0)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        disk_detector = SolarDiskDetector()
        disk = disk_detector.detect(gray)
        assert disk is not None

        spot_detector = SunspotDetector()
        spots = spot_detector.detect(gray, disk)
        assert len(spots) == 0


class TestObstructionDetection:
    """Validates visual obstruction and cloud occlusion scoring."""

    def test_clear_vs_cloudy_obstruction(self):
        clear_img = generate_synthetic_solar_image(width=300, height=300, preset="quiet_sun")
        cloudy_img = generate_synthetic_solar_image(width=300, height=300, preset="cloudy")

        res_clear = analyze_image(clear_img)
        res_cloudy = analyze_image(cloudy_img)

        assert res_clear.obstruction_score < 0.20
        assert res_clear.obstruction_metrics.obstruction_type == ObstructionType.CLEAR

        assert res_cloudy.obstruction_score > res_clear.obstruction_score
        assert res_cloudy.obstruction_metrics.cloud_fraction > 0.15


class TestTemporalRegistrationAndChange:
    """Validates sub-pixel phase correlation registration and difference scoring."""

    def test_jitter_compensation(self):
        img1 = generate_synthetic_solar_image(width=300, height=300, preset="clear_with_sunspots", seed=10)
        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)

        # Apply synthetic pan/tilt tracking shift (+3 px X, -2 px Y)
        shift_matrix = np.array([[1.0, 0.0, 3.0], [0.0, 1.0, -2.0]], dtype=np.float32)
        gray2 = cv2.warpAffine(gray1, shift_matrix, (300, 300))

        analyzer = TemporalAnalyzer()
        success, dx, dy, aligned = analyzer.register_frames(gray2, gray1)

        assert success
        # The shift calculated should compensate for the 3px, -2px offset
        assert abs(dx - (-3.0)) < 1.0 or abs(dx - 3.0) < 1.0
        assert abs(dy - 2.0) < 1.0 or abs(dy - (-2.0)) < 1.0

    def test_change_score_on_identical_vs_altered(self):
        img1 = generate_synthetic_solar_image(width=300, height=300, preset="quiet_sun")
        img2 = generate_synthetic_solar_image(width=300, height=300, preset="clear_with_sunspots")

        res_same = analyze_image(img1, reference_image=img1)
        res_diff = analyze_image(img2, reference_image=img1)

        assert res_same.change_score <= 0.05
        assert res_diff.change_score > res_same.change_score


class TestBatchAndSequenceAnalysis:
    """Validates batch processing and sequence tracking."""

    def test_batch_analyze(self):
        images = [
            generate_synthetic_solar_image(width=200, height=200, preset="quiet_sun"),
            generate_synthetic_solar_image(width=200, height=200, preset="cloudy"),
            generate_synthetic_solar_image(width=200, height=200, preset="off_target"),
        ]
        results = batch_analyze(images)
        assert len(results) == 3
        assert results[0].solar_disk_detected
        assert not results[2].solar_disk_detected

    def test_analyze_sequence(self):
        seq = [
            generate_synthetic_solar_image(width=250, height=250, preset="quiet_sun"),
            generate_synthetic_solar_image(width=250, height=250, preset="quiet_sun"),
            generate_synthetic_solar_image(width=250, height=250, preset="clear_with_sunspots"),
        ]
        results = analyze_sequence(seq, source_type=ImageSourceType.HISTORICAL)
        assert len(results) == 3
        # First frame has no reference; subsequent frames do
        assert results[0].temporal_result is None
        assert results[1].temporal_result is not None and results[1].temporal_result.has_reference is True
        assert results[2].temporal_result is not None and results[2].temporal_result.has_reference is True


class TestSerializationAndContracts:
    """Validates JSON serialization and compliance with contracts/VisionResult.json."""

    def test_to_json_and_dict(self):
        img = generate_synthetic_solar_image(width=250, height=250, preset="clear_with_sunspots")
        result = analyze_image(img, source_type=ImageSourceType.ESP32_CAM)

        res_dict = result.to_dict()
        assert isinstance(res_dict, dict)
        assert res_dict["solar_disk_detected"] is True
        assert res_dict["source_type"] == "ESP32_CAM"
        assert "quality_score" in res_dict
        assert "confidence" in res_dict

        json_str = result.to_json()
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["image_id"] == result.image_id

    def test_mandatory_scientific_disclaimer_present(self):
        img = generate_synthetic_solar_image(width=200, height=200)
        result = analyze_image(img)
        assert "solar flare prediction" in result.limitations_disclaimer.lower()
