"""Observatory Health, Sensor Fusion, and Anomaly Detection Engine.

Agent 7 Ownership.
Primary orchestrator coordinating validation, cross-consistency, Bayesian fusion,
anomaly detection, and health state classification.
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional, Any, Tuple

from ai.health.schemas import (
    HealthState,
    ObservatoryHealthReport,
    AnomalyReport,
    SensorConfidence,
    FusedEnvironmentalState,
    CommsHealthIndicator,
    ActuatorHealthIndicator,
)
from ai.health.validators import SensorValidator
from ai.health.cross_consistency import CrossSensorConsistencyChecker
from ai.health.fusion import MultimodalSensorFusionEngine
from ai.health.anomaly_detector import AnomalyDetectionSuite
from ai.health.comms_actuator import CommsAndTelemetryMonitor, ActuatorTelemetryMonitor
from ai.health.health_classifier import ObservatoryHealthClassifier


class ObservatoryHealthEngine:
    """End-to-end engine for Sensor Fusion, Observatory Health, and Anomaly Detection."""

    def __init__(self):
        self.validator = SensorValidator()
        self.cross_checker = CrossSensorConsistencyChecker()
        self.fusion_engine = MultimodalSensorFusionEngine()
        self.anomaly_suite = AnomalyDetectionSuite()
        self.comms_monitor = CommsAndTelemetryMonitor()
        self.actuator_monitor = ActuatorTelemetryMonitor()
        self.classifier = ObservatoryHealthClassifier()

        self.last_report: Optional[ObservatoryHealthReport] = None

    def command_actuator_target(self, pan: int, tilt: int):
        """Notifies health engine of an issued pan/tilt command for tracking lag verification."""
        self.actuator_monitor.set_commanded_target(pan, tilt)

    def process_telemetry(
        self,
        telemetry: Dict[str, Any],
        bmp280_temp: Optional[float] = None,
        current_time_sec: Optional[float] = None
    ) -> ObservatoryHealthReport:
        """Processes a single telemetry frame through the full Agent 7 pipeline.

        Pipeline Stages:
        1. Single-sensor validation (Bounds, rates, staleness, dropouts).
        2. Cross-sensor consistency checks (DHT vs BMP, rain vs RH/lux).
        3. Multimodal Bayesian/inverse-variance sensor fusion.
        4. Statistical & Machine Learning anomaly detection (Z-score, CUSUM drift, Isolation Forest).
        5. Communication & Actuator health analysis.
        6. Observatory health scoring (0-100), health state classification, and root-cause evidence.

        Returns:
            Authoritative ObservatoryHealthReport adhering to contracts.
        """
        now = time.time() if current_time_sec is None else current_time_sec

        # 1. Validate individual sensors
        val_anomalies, confidences = self.validator.validate(telemetry, current_time_sec=now)

        # 2. Cross-sensor physical consistency
        cross_anomalies = self.cross_checker.check_consistency(
            telemetry=telemetry,
            sensor_confidences=confidences,
            bmp280_temp=bmp280_temp
        )

        # 3. Multimodal sensor fusion
        fused_state = self.fusion_engine.fuse(
            telemetry=telemetry,
            confidences=confidences,
            bmp280_temp=bmp280_temp
        )

        # 4. Statistical, Drift, and Isolation Forest Anomaly Detection
        suite_anomalies = self.anomaly_suite.detect_anomalies(
            telemetry=telemetry,
            confidences=confidences
        )

        # 5. Comms and Actuator telemetry monitoring
        comms_health, comms_anomalies = self.comms_monitor.inspect_comms(
            telemetry=telemetry,
            current_time_sec=now
        )
        actuator_health, actuator_anomalies = self.actuator_monitor.inspect_actuators(
            telemetry=telemetry,
            current_time_sec=now
        )

        # Aggregate all detected anomalies
        all_anomalies: List[AnomalyReport] = (
            val_anomalies
            + cross_anomalies
            + suite_anomalies
            + comms_anomalies
            + actuator_anomalies
        )

        # 6. Composite scoring, state classification, root-cause evidence compilation
        report = self.classifier.evaluate(
            telemetry=telemetry,
            confidences=confidences,
            anomalies=all_anomalies,
            fused_state=fused_state,
            comms_health=comms_health,
            actuator_health=actuator_health
        )

        self.last_report = report
        return report

    def to_agent8_input(
        self,
        report: Optional[ObservatoryHealthReport] = None
    ) -> Dict[str, Any]:
        """Convenience method to export health results formatted for Agent 8's Agent7HealthInput."""
        target_report = report if report is not None else self.last_report
        if target_report is None:
            # Return safe default
            return {
                "hardware_health_score": 1.0,
                "sensor_health": {
                    "dht22": True,
                    "bh1750": True,
                    "bmp280": True,
                    "rain": True,
                    "camera": True
                },
                "anomaly_score": 0.0,
                "sensor_conflict": False,
                "sensor_conflict_details": [],
                "communication_loss": False,
                "hardware_safety_interlock": False
            }
        return target_report.to_agent8_health_input()
