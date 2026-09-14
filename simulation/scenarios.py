"""
Solar Sentry — Simulation Scenarios
Agent 10: Digital Twin + Mission Memory + Learning + Simulation + Integration

Defines 10 canonical simulation scenarios running without physical hardware:
1. CLEAR_DAY
2. CLOUDY
3. RAIN_APPROACHING
4. HIGH_HUMIDITY
5. SENSOR_FAILURE
6. CAMERA_OBSTRUCTION
7. COMMUNICATION_FAILURE
8. GOOD_OBSERVATION
9. DEGRADING_CONDITIONS
10. RECOVERY
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class ScenarioType(str, Enum):
    CLEAR_DAY = "CLEAR_DAY"
    CLOUDY = "CLOUDY"
    RAIN_APPROACHING = "RAIN_APPROACHING"
    HIGH_HUMIDITY = "HIGH_HUMIDITY"
    SENSOR_FAILURE = "SENSOR_FAILURE"
    CAMERA_OBSTRUCTION = "CAMERA_OBSTRUCTION"
    COMMUNICATION_FAILURE = "COMMUNICATION_FAILURE"
    GOOD_OBSERVATION = "GOOD_OBSERVATION"
    DEGRADING_CONDITIONS = "DEGRADING_CONDITIONS"
    RECOVERY = "RECOVERY"


@dataclass
class SimulatedStepData:
    """Synchronized multi-modal state snapshot generated during a simulation step."""
    step_index: int
    elapsed_seconds: float
    # Environmental telemetry
    temperature: float
    humidity: float
    pressure: float
    lux: float
    rain_raw: int
    rain_detected: bool
    # Sensor status flags
    sensor_status: Dict[str, bool]
    # Visual observation state
    vision_preset: str  # quiet_sun, clear_with_sunspots, limb_darkening, overexposed, heavy_clouds, underexposed
    image_quality: float
    obstruction_score: float
    solar_disk_detected: bool
    sunspot_count: int
    # Edge health & communication
    comms_delay_sec: float
    comms_loss: bool
    edge_state_override: Optional[str] = None


@dataclass
class SimulationScenario:
    """Specification of an autonomous observatory simulation scenario."""
    scenario_type: ScenarioType
    description: str
    duration_seconds: float = 120.0
    step_seconds: float = 1.0
    initial_pan: int = 90
    initial_tilt: int = 45

    def generate_step(self, step_idx: int, elapsed_sec: float) -> SimulatedStepData:
        """Generates synchronized sensor, vision, and comms state for elapsed time."""
        t_norm = min(1.0, elapsed_sec / max(1.0, self.duration_seconds))

        if self.scenario_type == ScenarioType.CLEAR_DAY:
            # Pristine clear day, high irradiance, stable pressure
            lux = 55000.0 + 5000.0 * math.sin(t_norm * math.pi)
            temp = 26.0 + 2.0 * t_norm
            humid = 35.0 + 3.0 * math.sin(t_norm * 2.0)
            press = 1014.0 + 0.5 * math.cos(t_norm)
            return SimulatedStepData(
                step_index=step_idx,
                elapsed_seconds=elapsed_sec,
                temperature=round(temp, 2),
                humidity=round(humid, 1),
                pressure=round(press, 2),
                lux=round(lux, 1),
                rain_raw=3850,
                rain_detected=False,
                sensor_status={"dht22": True, "bh1750": True, "bmp280": True, "rain": True},
                vision_preset="quiet_sun",
                image_quality=0.88,
                obstruction_score=0.05,
                solar_disk_detected=True,
                sunspot_count=2,
                comms_delay_sec=0.05,
                comms_loss=False
            )

        elif self.scenario_type == ScenarioType.CLOUDY:
            # Persistent overcast cloud cover, low irradiance, occluded optical disk
            lux = 12000.0 + 4000.0 * math.sin(t_norm * 6.0)
            temp = 22.0 - 1.0 * t_norm
            humid = 72.0 + 5.0 * math.sin(t_norm * 3.0)
            press = 1010.5
            return SimulatedStepData(
                step_index=step_idx,
                elapsed_seconds=elapsed_sec,
                temperature=round(temp, 2),
                humidity=round(humid, 1),
                pressure=round(press, 2),
                lux=round(lux, 1),
                rain_raw=3700,
                rain_detected=False,
                sensor_status={"dht22": True, "bh1750": True, "bmp280": True, "rain": True},
                vision_preset="heavy_clouds",
                image_quality=0.32,
                obstruction_score=0.78,
                solar_disk_detected=False,
                sunspot_count=0,
                comms_delay_sec=0.08,
                comms_loss=False
            )

        elif self.scenario_type == ScenarioType.RAIN_APPROACHING:
            # Barometric pressure plunge, humidity soaring, rain onset in second half
            is_raining = (t_norm >= 0.55)
            lux = max(2000.0, 48000.0 * (1.0 - t_norm))
            temp = 25.0 - 4.0 * t_norm
            humid = min(96.0, 50.0 + 45.0 * t_norm)
            press = 1013.0 - 8.0 * t_norm
            rain_raw = 650 if is_raining else int(3800 - 1200 * t_norm)
            return SimulatedStepData(
                step_index=step_idx,
                elapsed_seconds=elapsed_sec,
                temperature=round(temp, 2),
                humidity=round(humid, 1),
                pressure=round(press, 2),
                lux=round(lux, 1),
                rain_raw=rain_raw,
                rain_detected=is_raining,
                sensor_status={"dht22": True, "bh1750": True, "bmp280": True, "rain": True},
                vision_preset="heavy_clouds" if t_norm > 0.4 else "quiet_sun",
                image_quality=max(0.1, 0.85 - 0.75 * t_norm),
                obstruction_score=min(1.0, 0.1 + 0.9 * t_norm),
                solar_disk_detected=(not is_raining and t_norm < 0.45),
                sunspot_count=1 if t_norm < 0.4 else 0,
                comms_delay_sec=0.1,
                comms_loss=False
            )

        elif self.scenario_type == ScenarioType.HIGH_HUMIDITY:
            # Clear sky and strong solar disk, but extreme humidity causing condensation warning
            lux = 52000.0
            temp = 24.0
            humid = 88.0 + 4.0 * math.sin(t_norm * 3.0)  # Condensation risk!
            press = 1012.0
            return SimulatedStepData(
                step_index=step_idx,
                elapsed_seconds=elapsed_sec,
                temperature=temp,
                humidity=round(humid, 1),
                pressure=press,
                lux=lux,
                rain_raw=3800,
                rain_detected=False,
                sensor_status={"dht22": True, "bh1750": True, "bmp280": True, "rain": True},
                vision_preset="quiet_sun",
                image_quality=0.74,
                obstruction_score=0.15,
                solar_disk_detected=True,
                sunspot_count=2,
                comms_delay_sec=0.05,
                comms_loss=False
            )

        elif self.scenario_type == ScenarioType.SENSOR_FAILURE:
            # Fault injection: DHT22 fails halfway through scenario
            dht_failed = (t_norm >= 0.40)
            temp = -999.0 if dht_failed else 26.0
            humid = -999.0 if dht_failed else 42.0
            return SimulatedStepData(
                step_index=step_idx,
                elapsed_seconds=elapsed_sec,
                temperature=temp,
                humidity=humid,
                pressure=1013.25,
                lux=49000.0,
                rain_raw=3850,
                rain_detected=False,
                sensor_status={"dht22": not dht_failed, "bh1750": True, "bmp280": True, "rain": True},
                vision_preset="quiet_sun",
                image_quality=0.82,
                obstruction_score=0.10,
                solar_disk_detected=True,
                sunspot_count=1,
                comms_delay_sec=0.05,
                comms_loss=False
            )

        elif self.scenario_type == ScenarioType.CAMERA_OBSTRUCTION:
            # Lens occluded or optical smear
            obstructed = (t_norm >= 0.30)
            return SimulatedStepData(
                step_index=step_idx,
                elapsed_seconds=elapsed_sec,
                temperature=25.5,
                humidity=40.0,
                pressure=1013.0,
                lux=52000.0,
                rain_raw=3850,
                rain_detected=False,
                sensor_status={"dht22": True, "bh1750": True, "bmp280": True, "rain": True},
                vision_preset="underexposed" if obstructed else "quiet_sun",
                image_quality=0.18 if obstructed else 0.85,
                obstruction_score=0.92 if obstructed else 0.05,
                solar_disk_detected=not obstructed,
                sunspot_count=0 if obstructed else 3,
                comms_delay_sec=0.05,
                comms_loss=False
            )

        elif self.scenario_type == ScenarioType.COMMUNICATION_FAILURE:
            # Backend comms dropout > 30s
            comms_down = (t_norm >= 0.35)
            return SimulatedStepData(
                step_index=step_idx,
                elapsed_seconds=elapsed_sec,
                temperature=26.0,
                humidity=42.0,
                pressure=1013.0,
                lux=50000.0,
                rain_raw=3850,
                rain_detected=False,
                sensor_status={"dht22": True, "bh1750": True, "bmp280": True, "rain": True},
                vision_preset="quiet_sun",
                image_quality=0.85,
                obstruction_score=0.05,
                solar_disk_detected=True,
                sunspot_count=2,
                comms_delay_sec=45.0 if comms_down else 0.05,
                comms_loss=comms_down
            )

        elif self.scenario_type == ScenarioType.GOOD_OBSERVATION:
            # Exceptional scientific seeing, high sunspots, zero artifacts
            return SimulatedStepData(
                step_index=step_idx,
                elapsed_seconds=elapsed_sec,
                temperature=24.5,
                humidity=32.0,
                pressure=1015.0,
                lux=62000.0,
                rain_raw=3900,
                rain_detected=False,
                sensor_status={"dht22": True, "bh1750": True, "bmp280": True, "rain": True},
                vision_preset="clear_with_sunspots",
                image_quality=0.95,
                obstruction_score=0.02,
                solar_disk_detected=True,
                sunspot_count=5,
                comms_delay_sec=0.03,
                comms_loss=False
            )

        elif self.scenario_type == ScenarioType.DEGRADING_CONDITIONS:
            # Starts excellent, progressively deteriorates into cloudiness
            deg = t_norm
            lux = max(8000.0, 58000.0 * (1.0 - 0.7 * deg))
            humid = 38.0 + 35.0 * deg
            q = max(0.2, 0.92 - 0.7 * deg)
            obs = min(0.85, 0.05 + 0.75 * deg)
            return SimulatedStepData(
                step_index=step_idx,
                elapsed_seconds=elapsed_sec,
                temperature=25.0 - 2.0 * deg,
                humidity=round(humid, 1),
                pressure=1013.0 - 3.0 * deg,
                lux=round(lux, 1),
                rain_raw=3850,
                rain_detected=False,
                sensor_status={"dht22": True, "bh1750": True, "bmp280": True, "rain": True},
                vision_preset="quiet_sun" if deg < 0.5 else "heavy_clouds",
                image_quality=round(q, 2),
                obstruction_score=round(obs, 2),
                solar_disk_detected=(deg < 0.65),
                sunspot_count=3 if deg < 0.4 else 0,
                comms_delay_sec=0.05,
                comms_loss=False
            )

        elif self.scenario_type == ScenarioType.RECOVERY:
            # Starts in rain/suspend, clears up at t=0.4, allows clean recovery to STANDBY
            raining = (t_norm < 0.45)
            rain_raw = 700 if raining else 3850
            return SimulatedStepData(
                step_index=step_idx,
                elapsed_seconds=elapsed_sec,
                temperature=21.0 + 4.0 * t_norm,
                humidity=round(85.0 - 45.0 * t_norm, 1),
                pressure=1008.0 + 5.0 * t_norm,
                lux=15000.0 if raining else 50000.0,
                rain_raw=rain_raw,
                rain_detected=raining,
                sensor_status={"dht22": True, "bh1750": True, "bmp280": True, "rain": True},
                vision_preset="heavy_clouds" if raining else "quiet_sun",
                image_quality=0.25 if raining else 0.86,
                obstruction_score=0.85 if raining else 0.08,
                solar_disk_detected=(not raining),
                sunspot_count=0 if raining else 2,
                comms_delay_sec=0.05,
                comms_loss=False,
                edge_state_override="SUSPEND" if raining else None
            )

        # Fallback default
        return SimulatedStepData(
            step_index=step_idx,
            elapsed_seconds=elapsed_sec,
            temperature=25.0,
            humidity=45.0,
            pressure=1013.25,
            lux=45000.0,
            rain_raw=3850,
            rain_detected=False,
            sensor_status={"dht22": True, "bh1750": True, "bmp280": True, "rain": True},
            vision_preset="quiet_sun",
            image_quality=0.80,
            obstruction_score=0.10,
            solar_disk_detected=True,
            sunspot_count=1,
            comms_delay_sec=0.05,
            comms_loss=False
        )


def get_scenario(scenario_type: ScenarioType | str, duration_seconds: float = 60.0, step_seconds: float = 1.0) -> SimulationScenario:
    """Factory helper to obtain a configured SimulationScenario."""
    if isinstance(scenario_type, str):
        scenario_type = ScenarioType(scenario_type)
    
    descriptions = {
        ScenarioType.CLEAR_DAY: "Clear sky with strong irradiance and high optical quality",
        ScenarioType.CLOUDY: "Heavy persistent overcast cloud cover",
        ScenarioType.RAIN_APPROACHING: "Atmospheric front bringing pressure drops and rain emergency",
        ScenarioType.HIGH_HUMIDITY: "High ambient humidity with risk of optical condensation",
        ScenarioType.SENSOR_FAILURE: "Non-critical sensor hardware disconnect / electrical failure",
        ScenarioType.CAMERA_OBSTRUCTION: "Optical path occlusion, dirt or heavy lens glare",
        ScenarioType.COMMUNICATION_FAILURE: "Central communication dropout leading to fail-safe timeout",
        ScenarioType.GOOD_OBSERVATION: "Prime observation conditions with high scientific fidelity",
        ScenarioType.DEGRADING_CONDITIONS: "Progressive weather and seeing quality deterioration",
        ScenarioType.RECOVERY: "Post-rain clearance allowing automated recovery sequence",
    }
    return SimulationScenario(
        scenario_type=scenario_type,
        description=descriptions.get(scenario_type, "Standard simulation scenario"),
        duration_seconds=duration_seconds,
        step_seconds=step_seconds
    )
