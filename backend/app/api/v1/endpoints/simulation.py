"""
Solar Sentry — Simulation & Scenario Control API Endpoints
Module: Agent 10 (Digital Twin, Simulation & Integration)
"""

from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.core.providers import provider_manager, SystemMode
from simulation.scenarios import ScenarioType


router = APIRouter(prefix="/simulation", tags=["Simulation & Scenarios"])

SCENARIOS_CATALOG = [
    {
        "id": "CLEAR_DAY",
        "name": "1. Clear Sky Optimal Tracking",
        "description": "Nominal high irradiance, ORS > 90%, crisp disk edge, quiet sun or sunspot tracking.",
        "expected_state": "OBSERVE"
    },
    {
        "id": "GOOD_OBSERVATION",
        "name": "2. Active Sunspot Group Tracking",
        "description": "Peak seeing conditions, active region resolved, multi-sunspot tracking.",
        "expected_state": "OBSERVE"
    },
    {
        "id": "CLOUDY",
        "name": "3. Cloud Transit & Quality Dip",
        "description": "Passing cirrus cloud cover, illuminance drops, cognitive decision shifts to WAIT.",
        "expected_state": "WAIT"
    },
    {
        "id": "RAIN_APPROACHING",
        "name": "4. Sudden Rain Approach & Interlock",
        "description": "Barometric pressure drops, humidity spikes, rain ADC triggers emergency SUSPEND.",
        "expected_state": "SUSPEND"
    },
    {
        "id": "SENSOR_FAILURE",
        "name": "5. Sensor Disagreement & Anomaly",
        "description": "DHT22 / BMP280 failure, anomaly detector alerts, system operates in DEGRADED mode.",
        "expected_state": "DEGRADED"
    },
    {
        "id": "CAMERA_OBSTRUCTION",
        "name": "6. Optical Path Obstruction",
        "description": "Severe lens obstruction detected by vision quality analyzer; system holds in WAIT.",
        "expected_state": "WAIT"
    },
    {
        "id": "COMMUNICATION_FAILURE",
        "name": "7. Comms Loss Watchdog Failsafe",
        "description": "Heartbeat expires (>30s), local hardware watchdog activates SAFE park stow.",
        "expected_state": "SAFE"
    },
    {
        "id": "RECOVERY",
        "name": "8. Post-Hazard Automated Recovery",
        "description": "Rain dries up, sensors re-converge, system performs self-check and resumes tracking.",
        "expected_state": "STANDBY"
    },
    {
        "id": "HIGH_HUMIDITY",
        "name": "9. High Quality Window",
        "description": "Stable thermal gradient, low seeing jitter, maximum fidelity optical imaging.",
        "expected_state": "OBSERVE"
    },
    {
        "id": "DEGRADING_CONDITIONS",
        "name": "10. Low Quality Window",
        "description": "Turbulent air mass and declining solar elevation; forecast predicts deteriorating conditions.",
        "expected_state": "WAIT"
    }
]


class SwitchScenarioRequest(BaseModel):
    scenario_id: str


@router.get("/scenarios", summary="List all 10 canonical simulation scenarios")
async def list_simulation_scenarios() -> List[Dict[str, Any]]:
    return SCENARIOS_CATALOG


@router.post("/switch", summary="Switch running simulation scenario")
async def switch_scenario(req: SwitchScenarioRequest) -> Dict[str, Any]:
    matched = next((s for s in SCENARIOS_CATALOG if s["id"].upper() == req.scenario_id.upper()), None)
    if not matched:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown scenario ID '{req.scenario_id}'."
        )

    # If currently in hardware mode, optionally inform caller
    provider_manager.demo_sensor.switch_scenario(matched["id"])
    return {
        "status": "SUCCESS",
        "scenario": matched,
        "system_mode": provider_manager.mode.value
    }


@router.post("/step", summary="Advance simulation step by dt seconds")
async def step_simulation() -> Dict[str, Any]:
    telem = await provider_manager.demo_sensor.get_telemetry()
    return {
        "status": "STEPPED",
        "telemetry": telem.model_dump()
    }
