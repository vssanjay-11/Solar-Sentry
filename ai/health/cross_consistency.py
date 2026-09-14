"""Cross-sensor consistency validation and physical correlation checks.

Agent 7 Ownership.
Validates multi-sensor plausibility against physical laws, dual-sensor redundancies,
and meteorological relationships.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Any, Tuple

from ai.health.schemas import (
    AnomalyReport,
    AnomalyType,
    FaultSeverity,
    SensorConfidence,
)


def calculate_dew_point(temp_c: float, humidity_pct: float) -> float:
    """Calculates dew point using the Magnus-Tetens approximation.

    Formula:
      gamma = (a * T) / (b + T) + ln(RH / 100)
      T_dew = (b * gamma) / (a - gamma)
    where a = 17.27, b = 237.7°C.
    """
    if humidity_pct <= 0.0:
        return -50.0
    a = 17.27
    b = 237.7
    rh_fraction = max(0.01, min(1.0, humidity_pct / 100.0))
    gamma = (a * temp_c) / (b + temp_c) + math.log(rh_fraction)
    dew_point = (b * gamma) / (a - gamma)
    return round(dew_point, 2)


class CrossSensorConsistencyChecker:
    """Cross-validates multiple sensor telemetry streams against physical constraints."""

    def __init__(
        self,
        temp_delta_warning: float = 3.5,
        temp_delta_critical: float = 7.0,
    ):
        self.temp_delta_warning = temp_delta_warning
        self.temp_delta_critical = temp_delta_critical

    def check_consistency(
        self,
        telemetry: Dict[str, Any],
        sensor_confidences: Dict[str, SensorConfidence],
        bmp280_temp: Optional[float] = None
    ) -> List[AnomalyReport]:
        """Evaluates cross-sensor physical consistency.

        Args:
            telemetry: Raw telemetry payload
            sensor_confidences: Individual sensor confidence results from validators
            bmp280_temp: Optional secondary temperature reading from BMP280 if available
        """
        anomalies: List[AnomalyReport] = []

        temp_dht = telemetry.get("temperature")
        humidity = telemetry.get("humidity")
        lux = telemetry.get("lux")
        rain_detected = telemetry.get("rain_detected", False)
        rain_raw = telemetry.get("rain_raw", 3800)

        # 1. Dual Temperature Consistency (DHT22 vs BMP280)
        # If edge simulator or edge hardware provides secondary BMP280 temperature
        if bmp280_temp is not None and temp_dht is not None:
            if isinstance(temp_dht, (int, float)) and temp_dht > -100:
                t_delta = abs(float(temp_dht) - float(bmp280_temp))
                if t_delta >= self.temp_delta_critical:
                    anomalies.append(
                        AnomalyReport(
                            sensor="temperature_redundancy",
                            type=AnomalyType.CROSS_SENSOR_INCONSISTENCY,
                            severity=FaultSeverity.HIGH,
                            description=(
                                f"Critical dual-temperature discrepancy: DHT22={temp_dht:.1f}°C vs "
                                f"BMP280={bmp280_temp:.1f}°C (delta={t_delta:.1f}°C > {self.temp_delta_critical}°C)"
                            ),
                            observed_value=t_delta,
                            expected_range=[0.0, self.temp_delta_warning],
                        )
                    )
                    # Degrade confidence of both or lower the outlier
                    if "temperature" in sensor_confidences:
                        sensor_confidences["temperature"].confidence = min(
                            sensor_confidences["temperature"].confidence, 0.4
                        )
                elif t_delta >= self.temp_delta_warning:
                    anomalies.append(
                        AnomalyReport(
                            sensor="temperature_redundancy",
                            type=AnomalyType.CROSS_SENSOR_INCONSISTENCY,
                            severity=FaultSeverity.MEDIUM,
                            description=(
                                f"Dual-temperature divergence: DHT22={temp_dht:.1f}°C vs "
                                f"BMP280={bmp280_temp:.1f}°C (delta={t_delta:.1f}°C)"
                            ),
                            observed_value=t_delta,
                            expected_range=[0.0, self.temp_delta_warning],
                        )
                    )
                    if "temperature" in sensor_confidences:
                        sensor_confidences["temperature"].confidence = min(
                            sensor_confidences["temperature"].confidence, 0.7
                        )

        # 2. Rain vs Humidity & Illuminance Consistency
        # Scenario A: Rain detected as active, but relative humidity is arid (< 25%) and bright direct sun (> 60,000 Lux)
        if rain_detected or (isinstance(rain_raw, (int, float)) and rain_raw < 1500):
            if isinstance(humidity, (int, float)) and humidity < 25.0:
                if isinstance(lux, (int, float)) and lux > 50000.0:
                    anomalies.append(
                        AnomalyReport(
                            sensor="rain",
                            type=AnomalyType.CROSS_SENSOR_INCONSISTENCY,
                            severity=FaultSeverity.HIGH,
                            description=(
                                f"Unphysical rain detection: Rain sensor active (raw={rain_raw}) but "
                                f"relative humidity is arid ({humidity}%) under high solar illuminance ({lux} Lux). "
                                f"Probable debris, bird dropping, or optical/conductive short on rain plate."
                            ),
                            observed_value=float(humidity),
                            expected_range=[60.0, 100.0],
                        )
                    )
                    if "rain" in sensor_confidences:
                        sensor_confidences["rain"].confidence = min(
                            sensor_confidences["rain"].confidence, 0.3
                        )

        # Scenario B: Saturated humidity (100%) and low depression, but rain raw indicates bone dry in downpour
        # (covered under observation quality / warning if persistent)

        # 3. Dew point and physical limits
        if isinstance(temp_dht, (int, float)) and isinstance(humidity, (int, float)):
            if temp_dht > -50 and 0 <= humidity <= 100:
                dew_point = calculate_dew_point(temp_dht, humidity)
                # Dew point cannot exceed ambient temperature by basic thermodynamics
                if dew_point > temp_dht + 0.5:
                    anomalies.append(
                        AnomalyReport(
                            sensor="humidity",
                            type=AnomalyType.CROSS_SENSOR_INCONSISTENCY,
                            severity=FaultSeverity.MEDIUM,
                            description=f"Thermodynamic violation: Dew point {dew_point}°C > ambient temperature {temp_dht}°C",
                            observed_value=dew_point,
                            expected_range=[-50.0, float(temp_dht)],
                        )
                    )

        return anomalies
