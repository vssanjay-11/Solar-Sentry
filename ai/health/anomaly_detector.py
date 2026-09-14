"""Statistical and machine learning anomaly detection for Solar Sentry.

Agent 7 Ownership.
Implements:
1. Robust Statistical Outlier Detection (Median, MAD, Rolling Z-Score).
2. Scikit-learn Isolation Forest on multi-modal telemetry vectors.
3. CUSUM (Cumulative Sum) drift detection for gradual sensor degradation.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Any, Tuple
from collections import deque
import numpy as np
from sklearn.ensemble import IsolationForest

from ai.health.schemas import (
    AnomalyReport,
    AnomalyType,
    FaultSeverity,
    SensorConfidence,
)


class RobustStatisticsDetector:
    """Computes median and Median Absolute Deviation (MAD) for robust outlier detection.

    Z_robust = 0.6745 * (x - median) / MAD
    """

    def __init__(self, window_size: int = 40, z_threshold: float = 3.8):
        self.window_size = window_size
        self.z_threshold = z_threshold
        self.buffers: Dict[str, deque[float]] = {
            "temperature": deque(maxlen=window_size),
            "humidity": deque(maxlen=window_size),
            "pressure": deque(maxlen=window_size),
            "lux": deque(maxlen=window_size),
        }

    def update_and_check(
        self,
        sensor: str,
        value: float
    ) -> Optional[Tuple[float, float, float]]:
        """Updates window and checks if value is a statistical outlier.

        Returns (z_robust, median, mad) if outlier, else None.
        """
        buf = self.buffers.get(sensor)
        if buf is None:
            return None

        buf.append(value)
        if len(buf) < 15:
            # Need minimum history for reliable statistics
            return None

        arr = np.array(buf)
        med = float(np.median(arr))
        mad = float(np.median(np.abs(arr - med)))

        if mad < 1e-4:
            # Near-zero variance: fallback to std dev
            std = float(np.std(arr))
            if std < 1e-4:
                return None
            z = abs(value - med) / std
        else:
            z = 0.6745 * abs(value - med) / mad

        if z > self.z_threshold:
            return z, med, mad
        return None


class CUSUMDriftDetector:
    """Cumulative Sum (CUSUM) drift detection for tracking calibration decay.

    Detects subtle persistent shifts in sensor readings over time.
    """

    def __init__(
        self,
        sensors: List[str],
        slack_k: float = 0.5,
        threshold_h: float = 5.0
    ):
        self.slack_k = slack_k
        self.threshold_h = threshold_h
        self.s_pos: Dict[str, float] = {s: 0.0 for s in sensors}
        self.s_neg: Dict[str, float] = {s: 0.0 for s in sensors}
        self.baseline_mean: Dict[str, float] = {}
        self.baseline_std: Dict[str, float] = {}
        self.drift_count: Dict[str, int] = {s: 0 for s in sensors}

    def set_baseline(self, sensor: str, mean: float, std: float):
        self.baseline_mean[sensor] = mean
        self.baseline_std[sensor] = max(1e-3, std)

    def check_drift(self, sensor: str, value: float) -> bool:
        """Updates CUSUM accumulator and returns True if drift threshold exceeded."""
        if sensor not in self.baseline_mean:
            return False

        mu0 = self.baseline_mean[sensor]
        sigma0 = self.baseline_std[sensor]
        normalized_val = (value - mu0) / sigma0

        # CUSUM accumulation
        self.s_pos[sensor] = max(0.0, self.s_pos[sensor] + normalized_val - self.slack_k)
        self.s_neg[sensor] = max(0.0, self.s_neg[sensor] - normalized_val - self.slack_k)

        if self.s_pos[sensor] > self.threshold_h or self.s_neg[sensor] > self.threshold_h:
            self.drift_count[sensor] += 1
            # Decay slightly to prevent permanent latching
            self.s_pos[sensor] *= 0.8
            self.s_neg[sensor] *= 0.8
            return True

        return False


class IsolationForestAnomalyScorer:
    """Multi-dimensional machine learning anomaly detection using Isolation Forest.

    Evaluates interaction between temperature, humidity, pressure, illuminance, and rain ADC.
    """

    def __init__(self, contamination: float = 0.04, random_state: int = 42):
        self.contamination = contamination
        self.model = IsolationForest(
            n_estimators=80,
            contamination=contamination,
            random_state=random_state
        )
        self.is_fitted = False
        self._fit_synthetic_baseline()

    def _fit_synthetic_baseline(self):
        """Pre-fits model with physical operational baseline envelope for Solar Sentry."""
        np.random.seed(42)
        n_samples = 600

        # Typical daytime solar sentry environment
        temp = np.random.normal(25.0, 4.0, n_samples)
        humid = np.clip(np.random.normal(45.0, 15.0, n_samples), 10.0, 90.0)
        press = np.random.normal(1013.25, 6.0, n_samples)
        lux = np.clip(np.random.normal(45000.0, 20000.0, n_samples), 0.0, 100000.0)
        rain_adc = np.random.normal(3800.0, 100.0, n_samples)

        X = np.column_stack([temp, humid, press, np.log1p(lux), rain_adc])
        self.model.fit(X)
        self.is_fitted = True

    def score(self, telemetry: Dict[str, Any]) -> Tuple[float, bool]:
        """Computes anomaly score for a telemetry vector.

        Returns:
            (normalized_anomaly_score from 0.0 to 1.0, is_anomaly)
        """
        temp = telemetry.get("temperature", 25.0)
        humid = telemetry.get("humidity", 45.0)
        press = telemetry.get("pressure", 1013.25)
        lux = telemetry.get("lux", 40000.0)
        rain_adc = telemetry.get("rain_raw", 3800)

        # Dropouts are handled deterministically by validators; skip ML outlier scoring
        if temp < -50 or humid < 0 or press < 500 or rain_adc < 0:
            return 0.0, False

        vec = np.array([[float(temp), float(humid), float(press), np.log1p(max(0.0, float(lux))), float(rain_adc)]])
        # Decision function: lower values mean more abnormal (negative = anomaly)
        raw_score = float(self.model.decision_function(vec)[0])
        pred = int(self.model.predict(vec)[0])  # -1 = anomaly, 1 = normal

        # Normalize score into [0.0, 1.0] where 1.0 is severe anomaly
        norm_score = max(0.0, min(1.0, 0.5 - raw_score * 2.0))
        is_anom = (pred == -1 and norm_score > 0.6)
        return round(norm_score, 3), is_anom


class AnomalyDetectionSuite:
    """Coordinates statistical checks, drift tracking, and machine learning scoring."""

    def __init__(self):
        self.robust_stats = RobustStatisticsDetector()
        self.drift_detector = CUSUMDriftDetector(
            sensors=["temperature", "humidity", "pressure", "lux"]
        )
        self.iso_forest = IsolationForestAnomalyScorer()

        # Seed initial baselines for drift detection
        self.drift_detector.set_baseline("temperature", 25.0, 4.0)
        self.drift_detector.set_baseline("humidity", 45.0, 12.0)
        self.drift_detector.set_baseline("pressure", 1013.25, 4.0)
        self.drift_detector.set_baseline("lux", 40000.0, 18000.0)

    def detect_anomalies(
        self,
        telemetry: Dict[str, Any],
        confidences: Dict[str, SensorConfidence]
    ) -> List[AnomalyReport]:
        """Runs the combined anomaly detection pipeline across all channels."""
        anomalies: List[AnomalyReport] = []

        # 1. Robust Statistical Checks (Z-score & MAD)
        for sensor_name, val in [
            ("temperature", telemetry.get("temperature")),
            ("humidity", telemetry.get("humidity")),
            ("pressure", telemetry.get("pressure")),
            ("lux", telemetry.get("lux")),
        ]:
            if val is not None and isinstance(val, (int, float)) and val > -100:
                result = self.robust_stats.update_and_check(sensor_name, float(val))
                if result is not None:
                    z_score, med, mad = result
                    # Nuanced severity: don't make every anomaly critical!
                    severity = FaultSeverity.LOW if z_score < 4.5 else FaultSeverity.MEDIUM
                    if z_score > 7.0:
                        severity = FaultSeverity.HIGH

                    anomalies.append(
                        AnomalyReport(
                            sensor=sensor_name,
                            type=AnomalyType.SPIKE if z_score > 5.0 else AnomalyType.NOISE_VARIANCE,
                            severity=severity,
                            description=(
                                f"Robust statistical deviation on {sensor_name}: "
                                f"observed={val}, median={med:.2f}, MAD={mad:.2f}, Z_robust={z_score:.1f}"
                            ),
                            confidence=min(1.0, round(z_score / 10.0, 2)),
                            observed_value=float(val),
                        )
                    )
                    # Slightly soften sensor confidence
                    if sensor_name in confidences:
                        confidences[sensor_name].confidence = min(
                            confidences[sensor_name].confidence, 0.75
                        )

        # 2. CUSUM Drift Checks
        for sensor_name in ["humidity", "pressure", "temperature"]:
            val = telemetry.get(sensor_name)
            if val is not None and isinstance(val, (int, float)) and val > -100:
                if self.drift_detector.check_drift(sensor_name, float(val)):
                    anomalies.append(
                        AnomalyReport(
                            sensor=sensor_name,
                            type=AnomalyType.DRIFT,
                            severity=FaultSeverity.MEDIUM,
                            description=(
                                f"Gradual calibration drift detected on {sensor_name} via CUSUM accumulator; "
                                f"persistent statistical offset from nominal baseline."
                            ),
                            confidence=0.85,
                            observed_value=float(val),
                        )
                    )
                    if sensor_name in confidences:
                        confidences[sensor_name].drift = True
                        confidences[sensor_name].confidence = min(
                            confidences[sensor_name].confidence, 0.65
                        )

        # 3. Isolation Forest Multi-dimensional Check
        ml_score, is_ml_anom = self.iso_forest.score(telemetry)
        if is_ml_anom:
            anomalies.append(
                AnomalyReport(
                    sensor="multimodal_envelope",
                    type=AnomalyType.OUT_OF_RANGE,
                    severity=FaultSeverity.MEDIUM,
                    description=(
                        f"Multivariate telemetry combination isolated as anomalous by Isolation Forest "
                        f"(score={ml_score:.2f}). Unusual joint distribution of environmental metrics."
                    ),
                    confidence=ml_score,
                    observed_value=ml_score,
                )
            )

        return anomalies
