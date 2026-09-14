"""Multimodal sensor fusion and physical parameter estimation.

Agent 7 Ownership.
Implements Bayesian / inverse-variance sensor fusion for redundant channels,
dynamic uncertainty propagation, and derived physical metrics (Dew point, Vapor Pressure Deficit).
"""

from __future__ import annotations

import math
from typing import Dict, Optional, Any, Tuple

from ai.health.schemas import (
    FusedEnvironmentalState,
    SensorConfidence,
)
from ai.health.cross_consistency import calculate_dew_point


def calculate_vapor_pressure_deficit(temp_c: float, humidity_pct: float) -> float:
    """Calculates Vapor Pressure Deficit (VPD) in kPa.

    Formula:
      e_s(T) = 0.61078 * exp((17.27 * T) / (T + 237.3))
      VPD = e_s(T) * (1 - RH / 100)
    """
    if temp_c < -40.0:
        return 0.0
    es = 0.61078 * math.exp((17.27 * temp_c) / (temp_c + 237.3))
    rh_norm = max(0.0, min(100.0, humidity_pct)) / 100.0
    vpd = es * (1.0 - rh_norm)
    return round(max(0.0, vpd), 3)


class MultimodalSensorFusionEngine:
    """Fuses multi-sensor observations into unified environmental states with explicit uncertainty."""

    # Baseline standard deviations for sensors (manufacturer specifications)
    SIGMA_DHT22_TEMP = 0.5   # ±0.5°C
    SIGMA_BMP280_TEMP = 1.0  # ±1.0°C
    SIGMA_DHT22_HUMID = 2.0  # ±2.0%
    SIGMA_BMP280_PRESS = 1.0 # ±1.0 hPa
    SIGMA_BH1750_LUX = 20.0  # ±20%

    def fuse(
        self,
        telemetry: Dict[str, Any],
        confidences: Dict[str, SensorConfidence],
        bmp280_temp: Optional[float] = None
    ) -> FusedEnvironmentalState:
        """Executes inverse-variance Bayesian fusion across environmental sensors.

        Handles dropouts seamlessly: if DHT22 is disconnected, falls back to BMP280.
        """
        temp_dht = telemetry.get("temperature")
        humid = telemetry.get("humidity", 50.0)
        press = telemetry.get("pressure", 1013.25)
        lux = telemetry.get("lux", 10000.0)
        rain_detected = telemetry.get("rain_detected", False)
        rain_raw = telemetry.get("rain_raw", 3800)

        # 1. Fuse Temperature (DHT22 vs BMP280)
        fused_temp, temp_sigma, temp_source = self._fuse_temperature(
            temp_dht=temp_dht,
            temp_bmp=bmp280_temp,
            conf_dht=confidences.get("temperature", SensorConfidence(sensor="temperature", confidence=1.0)),
            conf_bmp=confidences.get("pressure", SensorConfidence(sensor="pressure", confidence=1.0)) # BMP280 bus health
        )

        # 2. Fuse Humidity
        conf_humid = confidences.get("humidity", SensorConfidence(sensor="humidity", confidence=1.0))
        if conf_humid.dropout or conf_humid.confidence <= 0.05:
            # Fallback estimation based on typical outdoor baseline
            fused_humid = 50.0
            humid_sigma = 15.0
        else:
            fused_humid = float(humid)
            humid_sigma = self.SIGMA_DHT22_HUMID / max(0.1, conf_humid.confidence)

        # 3. Fuse Pressure
        conf_press = confidences.get("pressure", SensorConfidence(sensor="pressure", confidence=1.0))
        if conf_press.dropout or conf_press.confidence <= 0.05:
            fused_press = 1013.25
            press_sigma = 10.0
        else:
            fused_press = float(press)
            press_sigma = self.SIGMA_BMP280_PRESS / max(0.1, conf_press.confidence)

        # 4. Lux
        conf_lux = confidences.get("lux", SensorConfidence(sensor="lux", confidence=1.0))
        if conf_lux.dropout or conf_lux.confidence <= 0.05:
            fused_lux = 0.0
            lux_sigma = 5000.0
        else:
            fused_lux = max(0.0, float(lux))
            lux_sigma = max(10.0, fused_lux * 0.05) / max(0.1, conf_lux.confidence)

        # 5. Derived Physical Quantities
        dew_point = calculate_dew_point(fused_temp, fused_humid)
        vpd = calculate_vapor_pressure_deficit(fused_temp, fused_humid)

        # 6. Rain Cross-Validation
        # Rain is confirmed if rain sensor detects moisture AND rain confidence > 0.4
        conf_rain = confidences.get("rain", SensorConfidence(sensor="rain", confidence=1.0))
        rain_confirmed = False
        if (rain_detected or rain_raw < 2000) and conf_rain.confidence >= 0.35:
            rain_confirmed = True

        return FusedEnvironmentalState(
            temperature=round(fused_temp, 2),
            temperature_uncertainty=round(temp_sigma, 3),
            humidity=round(fused_humid, 1),
            humidity_uncertainty=round(humid_sigma, 2),
            pressure=round(fused_press, 2),
            pressure_uncertainty=round(press_sigma, 2),
            lux=round(fused_lux, 1),
            lux_uncertainty=round(lux_sigma, 1),
            dew_point=dew_point,
            vapor_pressure_deficit_kpa=vpd,
            rain_confirmed=rain_confirmed,
            primary_temp_source=temp_source
        )

    def _fuse_temperature(
        self,
        temp_dht: Any,
        temp_bmp: Optional[float],
        conf_dht: SensorConfidence,
        conf_bmp: SensorConfidence
    ) -> Tuple[float, float, str]:
        """Performs Bayesian inverse-variance fusion between DHT22 and BMP280."""
        dht_valid = (
            temp_dht is not None
            and not conf_dht.dropout
            and conf_dht.confidence > 0.1
            and isinstance(temp_dht, (int, float))
            and temp_dht > -100
        )
        bmp_valid = (
            temp_bmp is not None
            and not conf_bmp.dropout
            and conf_bmp.confidence > 0.1
            and isinstance(temp_bmp, (int, float))
            and temp_bmp > -100
        )

        if dht_valid and bmp_valid:
            # Dynamic variances scaled inversely by confidence
            var_dht = (self.SIGMA_DHT22_TEMP / max(0.1, conf_dht.confidence)) ** 2
            var_bmp = (self.SIGMA_BMP280_TEMP / max(0.1, conf_bmp.confidence)) ** 2

            w_dht = 1.0 / var_dht
            w_bmp = 1.0 / var_bmp
            w_total = w_dht + w_bmp

            fused_t = (w_dht * float(temp_dht) + w_bmp * float(temp_bmp)) / w_total
            sigma_fused = math.sqrt(1.0 / w_total)
            return fused_t, sigma_fused, "FUSED"

        elif dht_valid and not bmp_valid:
            var_dht = (self.SIGMA_DHT22_TEMP / max(0.1, conf_dht.confidence)) ** 2
            return float(temp_dht), math.sqrt(var_dht), "DHT22"

        elif bmp_valid and not dht_valid:
            var_bmp = (self.SIGMA_BMP280_TEMP / max(0.1, conf_bmp.confidence)) ** 2
            return float(temp_bmp), math.sqrt(var_bmp), "BMP280"

        else:
            # Both invalid: return safe default
            val = float(temp_dht) if isinstance(temp_dht, (int, float)) and temp_dht > -100 else 25.0
            return val, 5.0, "FALLBACK"
