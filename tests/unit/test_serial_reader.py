import os
import sys
import pytest

try:
    from app.services.serial_reader import SerialTelemetryReader
    from app.core.providers import provider_manager, SystemMode
    from app.schemas.telemetry import DeviceState
except ImportError:
    _backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
    if _backend_dir not in sys.path:
        sys.path.insert(0, _backend_dir)
    from app.services.serial_reader import SerialTelemetryReader
    from app.core.providers import provider_manager, SystemMode
    from app.schemas.telemetry import DeviceState



@pytest.fixture
def reader():
    return SerialTelemetryReader(port="COM_TEST", baudrate=115200)


def test_parse_system_report_block(reader):
    raw_block = """
================================================
          SOLAR-SENTRY ΩX TELEMETRY
================================================
Device ID          : SOLAR-SENTRY-EDGE-01
Uptime             : 12 sec

---- ENVIRONMENT ----
Temperature        : 21.30 °C
Humidity           : 73.20 %
Pressure           : 774.75 hPa
Light              : 292.50 lux
Rain ADC           : 4095

---- SENSOR HEALTH ----
DHT22              : 100.00%
BMP280             : 100.00%
BH1750             : 100.00%
Rain Sensor        : 100.00%
Overall Health     : 100.00%

---- INTELLIGENCE ----
Environment Score  : 90.00%
Local Readiness    : 94.00%
Vision Score       : 100.00%
Solar Data Score   : 100.00%
Predicted Score    : 100.00%
Confidence         : 95.00%
AI Decision        : LOCAL_FALLBACK
Current State      : OBSERVE

---- ACTUATORS ----
Pan                : 90°
Tilt               : 90°

Wi-Fi              : CONNECTED
================================================
"""
    lines = [line.strip() for line in raw_block.strip().split("\n")]
    for line in lines:
        reader._parse_line(line)

    telem = reader.latest_telemetry
    assert telem is not None
    assert telem.device_id == "SOLAR-SENTRY-EDGE-01"
    assert telem.temperature == 21.30
    assert telem.humidity == 73.20
    assert telem.pressure == 774.75
    assert telem.lux == 292.50
    assert telem.rain_raw == 4095
    assert telem.rain_detected is False
    assert telem.pan == 90
    assert telem.tilt == 90
    assert telem.health == 100
    assert telem.state == DeviceState.OBSERVE
    assert telem.sensor_status.dht22 is True
    assert telem.sensor_status.bmp280 is True
    assert telem.sensor_status.bh1750 is True
    assert telem.sensor_status.rain is True


def test_parse_json_telemetry_frame(reader):
    json_line = (
        '{"device_id":"SOLAR-SENTRY-EDGE-01","uptime_ms":15000,'
        '"temperature":24.50,"humidity":55.00,"pressure":1012.00,"bmp_temperature":24.30,'
        '"lux":50000.00,"rain_raw":3900,"dht_ok":true,"bmp_ok":true,"bh1750_ok":true,"rain_ok":true,'
        '"sensor_health":100.00,"environment_score":92.00,"local_readiness":95.00,"vision_score":100.00,'
        '"solar_score":100.00,"predicted_score":100.00,"confidence":96.00,"state":"STANDBY",'
        '"ai_decision":"OBSERVE","pan":90,"tilt":45,"wifi_rssi":-55}'
    )
    reader._parse_line(json_line)

    telem = reader.latest_telemetry
    assert telem is not None
    assert telem.temperature == 24.50
    assert telem.lux == 50000.00
    assert telem.state == DeviceState.STANDBY
    assert telem.pan == 90
    assert telem.tilt == 45


def test_esp32_sensor_provider_connected_status(reader):
    import asyncio
    async def _test():
        test_parse_system_report_block(reader)
        telem = await provider_manager.esp32_sensor.get_telemetry()
        assert telem.temperature == 21.30
        assert telem.health == 100
        assert telem.state == DeviceState.OBSERVE
        assert await provider_manager.esp32_sensor.is_connected() is True

    asyncio.run(_test())

