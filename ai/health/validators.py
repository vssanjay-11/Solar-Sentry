"""Sensor validation, physical boundary checking, rate-of-change, and dropout detection.

Agent 7 Ownership.
Validates raw telemetry readings from Agent 1 before cross-sensor fusion.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Any, Tuple
from collections import deque
from datetime import datetime, timezone

from ai.health.schemas import (
    AnomalyReport,
    AnomalyType,
    FaultSeverity,
    SensorConfidence,
)


class SensorBounds:
    """Standard physical plausibility boundaries for Solar Sentry instrumentation."""
    TEMP_MIN = -20.0
    TEMP_MAX = 65.0     # Above 65.0C is thermal hazard
    HUMID_MIN = 0.0
    HUMID_MAX = 100.0
    PRESSURE_MIN = 800.0
    PRESSURE_MAX = 1100.0
    LUX_MIN = 0.0
    LUX_MAX = 130000.0  # Clear sun direct illumination peak ~120k lux
    RAIN_ADC_MIN = 0
    RAIN_ADC_MAX = 4095
    SERVO_MIN = 0
    SERVO_MAX = 180

    # Max plausible rate of change per second
    MAX_TEMP_RATE_PER_SEC = 3.0       # deg C / sec
    MAX_HUMID_RATE_PER_SEC = 10.0     # % / sec
    MAX_PRESSURE_RATE_PER_SEC = 5.0   # hPa / sec
    MAX_LUX_RATE_PER_SEC = 50000.0    # Lux / sec (clouds can rapidly block sun)


class SensorValidator:
    """Performs bounds checking, spike detection, dropout diagnosis, and staleness detection."""

    def __init__(self, history_window_size: int = 20, staleness_threshold: int = 15):
        self.history_window_size = history_window_size
        self.staleness_threshold = staleness_threshold

        # Historical buffers for staleness and rate-of-change analysis
        self._history: Dict[str, deque[float]] = {
            "temperature": deque(maxlen=history_window_size),
            "humidity": deque(maxlen=history_window_size),
            "pressure": deque(maxlen=history_window_size),
            "lux": deque(maxlen=history_window_size),
            "rain_raw": deque(maxlen=history_window_size),
        }
        self._last_timestamp: Optional[float] = None

    def validate(
        self,
        telemetry: Dict[str, Any],
        current_time_sec: Optional[float] = None
    ) -> Tuple[List[AnomalyReport], Dict[str, SensorConfidence]]:
        """Validates all raw sensor fields in a telemetry packet.

        Returns:
            Tuple of (anomalies_detected, sensor_confidence_map)
        """
        anomalies: List[AnomalyReport] = []
        confidences: Dict[str, SensorConfidence] = {}

        # 1. Inspect sensor_status flags reported directly by ESP32 firmware
        firmware_status = telemetry.get("sensor_status", {})
        dt = 1.0
        if self._last_timestamp is not None and current_time_sec is not None:
            dt = max(0.01, current_time_sec - self._last_timestamp)
        if current_time_sec is not None:
            self._last_timestamp = current_time_sec

        # 2. Temperature validation (DHT22 / BMP280 fallback)
        temp_val = telemetry.get("temperature")
        dht_hw_ok = firmware_status.get("dht22", True)
        anoms, conf = self._validate_temperature(temp_val, dht_hw_ok, dt)
        anomalies.extend(anoms)
        confidences["temperature"] = conf

        # 3. Humidity validation (DHT22)
        humid_val = telemetry.get("humidity")
        anoms, conf = self._validate_humidity(humid_val, dht_hw_ok, dt)
        anomalies.extend(anoms)
        confidences["humidity"] = conf

        # 4. Pressure validation (BMP280)
        press_val = telemetry.get("pressure")
        bmp_hw_ok = firmware_status.get("bmp280", True)
        anoms, conf = self._validate_pressure(press_val, bmp_hw_ok, dt)
        anomalies.extend(anoms)
        confidences["pressure"] = conf

        # 5. Lux validation (BH1750)
        lux_val = telemetry.get("lux")
        bh1750_hw_ok = firmware_status.get("bh1750", True)
        anoms, conf = self._validate_lux(lux_val, bh1750_hw_ok, dt)
        anomalies.extend(anoms)
        confidences["lux"] = conf

        # 6. Rain sensor ADC validation
        rain_adc = telemetry.get("rain_raw")
        rain_hw_ok = firmware_status.get("rain", True)
        anoms, conf = self._validate_rain(rain_adc, rain_hw_ok)
        anomalies.extend(anoms)
        confidences["rain"] = conf

        return anomalies, confidences

    def _is_dropout(self, val: Any) -> bool:
        """Determines if a reading indicates a disconnected or missing sensor."""
        if val is None:
            return True
        if isinstance(val, (int, float)):
            if math.isnan(val) or math.isinf(val):
                return True
            if val == -999.0 or val == -999:  # ESP32 standard error code
                return True
        return False

    def _check_staleness(self, sensor_key: str, val: float) -> bool:
        """Detects if a naturally noisy sensor has been frozen on identical float value."""
        history = self._history[sensor_key]
        history.append(val)
        if len(history) >= self.staleness_threshold:
            # Check if all values in history are identical within floating point tolerance
            first = history[0]
            if all(abs(x - first) < 1e-4 for x in history):
                return True
        return False

    def _validate_temperature(
        self,
        val: Any,
        hw_ok: bool,
        dt: float
    ) -> Tuple[List[AnomalyReport], SensorConfidence]:
        anomalies: List[AnomalyReport] = []
        sensor_id = "temperature"

        if not hw_ok or self._is_dropout(val):
            anomalies.append(
                AnomalyReport(
                    sensor=sensor_id,
                    type=AnomalyType.DROPOUT_DISCONNECTED,
                    severity=FaultSeverity.HIGH,
                    description="DHT22 temperature sensor disconnected or reporting error code (-999)",
                    observed_value=val if isinstance(val, (int, float)) else None,
                    expected_range=[SensorBounds.TEMP_MIN, SensorBounds.TEMP_MAX],
                )
            )
            return anomalies, SensorConfidence(
                sensor=sensor_id,
                confidence=0.0,
                status="DROPPED",
                dropout=True,
                degradation_reason="Hardware disconnected or -999 sentinel received"
            )

        val_f = float(val)

        # Range bounds
        if not (SensorBounds.TEMP_MIN <= val_f <= SensorBounds.TEMP_MAX):
            severity = FaultSeverity.CRITICAL if val_f > SensorBounds.TEMP_MAX else FaultSeverity.HIGH
            anomalies.append(
                AnomalyReport(
                    sensor=sensor_id,
                    type=AnomalyType.OUT_OF_RANGE,
                    severity=severity,
                    description=f"Temperature {val_f}°C outside plausibility window [{SensorBounds.TEMP_MIN}, {SensorBounds.TEMP_MAX}]°C",
                    observed_value=val_f,
                    expected_range=[SensorBounds.TEMP_MIN, SensorBounds.TEMP_MAX],
                )
            )
            return anomalies, SensorConfidence(
                sensor=sensor_id,
                confidence=0.1,
                status="FAULTY",
                last_valid_value=val_f,
                degradation_reason=f"Temperature {val_f}°C out of plausible physical range"
            )

        # Rate of change / Spike
        confidence = 1.0
        if len(self._history["temperature"]) > 0:
            last = self._history["temperature"][-1]
            rate = abs(val_f - last) / dt
            if rate > SensorBounds.MAX_TEMP_RATE_PER_SEC:
                anomalies.append(
                    AnomalyReport(
                        sensor=sensor_id,
                        type=AnomalyType.SPIKE,
                        severity=FaultSeverity.MEDIUM,
                        description=f"Temperature spike detected: {rate:.1f}°C/s exceeds threshold {SensorBounds.MAX_TEMP_RATE_PER_SEC}°C/s",
                        observed_value=val_f,
                    )
                )
                confidence = 0.6

        # Staleness check
        if self._check_staleness("temperature", val_f):
            anomalies.append(
                AnomalyReport(
                    sensor=sensor_id,
                    type=AnomalyType.STUCK_STALE,
                    severity=FaultSeverity.MEDIUM,
                    description=f"Temperature reading stuck invariant at {val_f}°C for {self.staleness_threshold} consecutive samples",
                    observed_value=val_f,
                )
            )
            confidence = min(confidence, 0.5)

        status = "HEALTHY" if confidence >= 0.8 else "DEGRADED"
        return anomalies, SensorConfidence(
            sensor=sensor_id,
            confidence=confidence,
            status=status,
            stale=(confidence <= 0.5),
            last_valid_value=val_f
        )

    def _validate_humidity(
        self,
        val: Any,
        hw_ok: bool,
        dt: float
    ) -> Tuple[List[AnomalyReport], SensorConfidence]:
        anomalies: List[AnomalyReport] = []
        sensor_id = "humidity"

        if not hw_ok or self._is_dropout(val):
            anomalies.append(
                AnomalyReport(
                    sensor=sensor_id,
                    type=AnomalyType.DROPOUT_DISCONNECTED,
                    severity=FaultSeverity.HIGH,
                    description="DHT22 humidity sensor disconnected or reporting error code (-999)",
                    observed_value=val if isinstance(val, (int, float)) else None,
                    expected_range=[SensorBounds.HUMID_MIN, SensorBounds.HUMID_MAX],
                )
            )
            return anomalies, SensorConfidence(
                sensor=sensor_id,
                confidence=0.0,
                status="DROPPED",
                dropout=True,
                degradation_reason="Hardware disconnected or invalid reading"
            )

        val_f = float(val)

        # Range bounds
        if not (SensorBounds.HUMID_MIN <= val_f <= SensorBounds.HUMID_MAX):
            anomalies.append(
                AnomalyReport(
                    sensor=sensor_id,
                    type=AnomalyType.OUT_OF_RANGE,
                    severity=FaultSeverity.HIGH,
                    description=f"Relative humidity {val_f}% outside plausible range [0, 100]%",
                    observed_value=val_f,
                    expected_range=[SensorBounds.HUMID_MIN, SensorBounds.HUMID_MAX],
                )
            )
            return anomalies, SensorConfidence(
                sensor=sensor_id,
                confidence=0.1,
                status="FAULTY",
                last_valid_value=val_f,
                degradation_reason=f"Humidity {val_f}% out of valid [0, 100]% bounds"
            )

        confidence = 1.0
        if len(self._history["humidity"]) > 0:
            last = self._history["humidity"][-1]
            rate = abs(val_f - last) / dt
            if rate > SensorBounds.MAX_HUMID_RATE_PER_SEC:
                anomalies.append(
                    AnomalyReport(
                        sensor=sensor_id,
                        type=AnomalyType.SPIKE,
                        severity=FaultSeverity.LOW,
                        description=f"Rapid humidity step change: {rate:.1f}%/s",
                        observed_value=val_f,
                    )
                )
                confidence = 0.7

        if self._check_staleness("humidity", val_f):
            anomalies.append(
                AnomalyReport(
                    sensor=sensor_id,
                    type=AnomalyType.STUCK_STALE,
                    severity=FaultSeverity.MEDIUM,
                    description=f"Humidity reading frozen at {val_f}% for {self.staleness_threshold} cycles",
                    observed_value=val_f,
                )
            )
            confidence = min(confidence, 0.5)

        status = "HEALTHY" if confidence >= 0.8 else "DEGRADED"
        return anomalies, SensorConfidence(
            sensor=sensor_id,
            confidence=confidence,
            status=status,
            stale=(confidence <= 0.5),
            last_valid_value=val_f
        )

    def _validate_pressure(
        self,
        val: Any,
        hw_ok: bool,
        dt: float
    ) -> Tuple[List[AnomalyReport], SensorConfidence]:
        anomalies: List[AnomalyReport] = []
        sensor_id = "pressure"

        if not hw_ok or self._is_dropout(val):
            anomalies.append(
                AnomalyReport(
                    sensor=sensor_id,
                    type=AnomalyType.DROPOUT_DISCONNECTED,
                    severity=FaultSeverity.HIGH,
                    description="BMP280 barometric pressure sensor disconnected or invalid I2C response",
                    observed_value=val if isinstance(val, (int, float)) else None,
                    expected_range=[SensorBounds.PRESSURE_MIN, SensorBounds.PRESSURE_MAX],
                )
            )
            return anomalies, SensorConfidence(
                sensor=sensor_id,
                confidence=0.0,
                status="DROPPED",
                dropout=True,
                degradation_reason="BMP280 disconnected or I2C failure"
            )

        val_f = float(val)

        if not (SensorBounds.PRESSURE_MIN <= val_f <= SensorBounds.PRESSURE_MAX):
            anomalies.append(
                AnomalyReport(
                    sensor=sensor_id,
                    type=AnomalyType.OUT_OF_RANGE,
                    severity=FaultSeverity.HIGH,
                    description=f"Barometric pressure {val_f} hPa outside atmospheric range [800, 1100] hPa",
                    observed_value=val_f,
                    expected_range=[SensorBounds.PRESSURE_MIN, SensorBounds.PRESSURE_MAX],
                )
            )
            return anomalies, SensorConfidence(
                sensor=sensor_id,
                confidence=0.1,
                status="FAULTY",
                last_valid_value=val_f,
                degradation_reason=f"Pressure {val_f} hPa out of range"
            )

        confidence = 1.0
        if len(self._history["pressure"]) > 0:
            last = self._history["pressure"][-1]
            rate = abs(val_f - last) / dt
            if rate > SensorBounds.MAX_PRESSURE_RATE_PER_SEC:
                anomalies.append(
                    AnomalyReport(
                        sensor=sensor_id,
                        type=AnomalyType.SPIKE,
                        severity=FaultSeverity.MEDIUM,
                        description=f"Unphysical barometric pressure jump {rate:.2f} hPa/s",
                        observed_value=val_f,
                    )
                )
                confidence = 0.6

        if self._check_staleness("pressure", val_f):
            anomalies.append(
                AnomalyReport(
                    sensor=sensor_id,
                    type=AnomalyType.STUCK_STALE,
                    severity=FaultSeverity.MEDIUM,
                    description=f"BMP280 pressure invariant at {val_f} hPa across {self.staleness_threshold} samples",
                    observed_value=val_f,
                )
            )
            confidence = min(confidence, 0.5)

        status = "HEALTHY" if confidence >= 0.8 else "DEGRADED"
        return anomalies, SensorConfidence(
            sensor=sensor_id,
            confidence=confidence,
            status=status,
            stale=(confidence <= 0.5),
            last_valid_value=val_f
        )

    def _validate_lux(
        self,
        val: Any,
        hw_ok: bool,
        dt: float
    ) -> Tuple[List[AnomalyReport], SensorConfidence]:
        anomalies: List[AnomalyReport] = []
        sensor_id = "lux"

        if not hw_ok or self._is_dropout(val):
            anomalies.append(
                AnomalyReport(
                    sensor=sensor_id,
                    type=AnomalyType.DROPOUT_DISCONNECTED,
                    severity=FaultSeverity.HIGH,
                    description="BH1750 illuminance sensor dropped or I2C communication failed",
                    observed_value=val if isinstance(val, (int, float)) else None,
                    expected_range=[SensorBounds.LUX_MIN, SensorBounds.LUX_MAX],
                )
            )
            return anomalies, SensorConfidence(
                sensor=sensor_id,
                confidence=0.0,
                status="DROPPED",
                dropout=True,
                degradation_reason="BH1750 disconnected or I2C failure"
            )

        val_f = float(val)

        if not (SensorBounds.LUX_MIN <= val_f <= SensorBounds.LUX_MAX):
            anomalies.append(
                AnomalyReport(
                    sensor=sensor_id,
                    type=AnomalyType.OUT_OF_RANGE,
                    severity=FaultSeverity.MEDIUM,
                    description=f"Lux value {val_f} outside bounds [0, 130000]",
                    observed_value=val_f,
                    expected_range=[SensorBounds.LUX_MIN, SensorBounds.LUX_MAX],
                )
            )
            return anomalies, SensorConfidence(
                sensor=sensor_id,
                confidence=0.2,
                status="FAULTY",
                last_valid_value=val_f
            )

        confidence = 1.0
        # Lux can drop quickly with cloud transit, but can check for frozen high values during night
        self._history["lux"].append(val_f)

        return anomalies, SensorConfidence(
            sensor=sensor_id,
            confidence=confidence,
            status="HEALTHY",
            last_valid_value=val_f
        )

    def _validate_rain(
        self,
        val: Any,
        hw_ok: bool
    ) -> Tuple[List[AnomalyReport], SensorConfidence]:
        anomalies: List[AnomalyReport] = []
        sensor_id = "rain"

        if not hw_ok or self._is_dropout(val):
            anomalies.append(
                AnomalyReport(
                    sensor=sensor_id,
                    type=AnomalyType.DROPOUT_DISCONNECTED,
                    severity=FaultSeverity.CRITICAL,  # Rain sensor is safety critical
                    description="Rain sensor analog ADC disconnected or grounded out",
                    observed_value=val if isinstance(val, (int, float)) else None,
                    expected_range=[SensorBounds.RAIN_ADC_MIN, SensorBounds.RAIN_ADC_MAX],
                )
            )
            return anomalies, SensorConfidence(
                sensor=sensor_id,
                confidence=0.0,
                status="DROPPED",
                dropout=True,
                degradation_reason="Rain sensor disconnected (ADC1 Channel 6)"
            )

        val_int = int(val)
        if not (SensorBounds.RAIN_ADC_MIN <= val_int <= SensorBounds.RAIN_ADC_MAX):
            anomalies.append(
                AnomalyReport(
                    sensor=sensor_id,
                    type=AnomalyType.OUT_OF_RANGE,
                    severity=FaultSeverity.HIGH,
                    description=f"Rain ADC reading {val_int} outside 12-bit range [0, 4095]",
                    observed_value=float(val_int),
                    expected_range=[float(SensorBounds.RAIN_ADC_MIN), float(SensorBounds.RAIN_ADC_MAX)],
                )
            )
            return anomalies, SensorConfidence(
                sensor=sensor_id,
                confidence=0.1,
                status="FAULTY",
                last_valid_value=float(val_int)
            )

        confidence = 1.0
        # Stuck rain check: Analog ADC pins almost always exhibit at least +/- 2 least significant bits of thermal noise
        self._history["rain_raw"].append(float(val_int))
        if len(self._history["rain_raw"]) >= self.staleness_threshold:
            first = self._history["rain_raw"][0]
            if all(x == first for x in self._history["rain_raw"]):
                # True flatline on analog ADC
                anomalies.append(
                    AnomalyReport(
                        sensor=sensor_id,
                        type=AnomalyType.STUCK_STALE,
                        severity=FaultSeverity.MEDIUM,
                        description=f"Rain ADC flatlined at {val_int} without electrical ADC noise; possible pinned pin or open circuit",
                        observed_value=float(val_int),
                    )
                )
                confidence = 0.5

        return anomalies, SensorConfidence(
            sensor=sensor_id,
            confidence=confidence,
            status="HEALTHY" if confidence >= 0.8 else "DEGRADED",
            last_valid_value=float(val_int)
        )
