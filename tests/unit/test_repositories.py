"""
Unit tests for Solar Sentry data access repositories.
"""

from datetime import datetime, timezone, timedelta
import unittest
from backend.database.config import DatabaseConfig, create_db_engine, get_session_factory, init_db
from backend.database.repositories import (
    DeviceRepository,
    SensorRepository,
    TelemetryRepository,
    ObservationRepository,
    ImageRepository,
    VisionAnalysisRepository,
    EnvironmentPredictionRepository,
    HealthRepository,
    AnomalyRepository,
    DecisionRepository,
    MissionRepository,
    MissionActionRepository,
    MissionMemoryRepository,
    CommandRepository,
    VerificationRepository,
    ModelVersionRepository,
)


class TestRepositories(unittest.TestCase):
    """Validates query logic, time-series operations, and repository contracts."""

    def setUp(self):
        self.engine = create_db_engine(DatabaseConfig(url="sqlite:///:memory:"))
        init_db(self.engine)
        self.SessionFactory = get_session_factory(self.engine)
        self.session = self.SessionFactory()

    def tearDown(self):
        self.session.close()

    def test_device_and_sensor_repo(self):
        dev_repo = DeviceRepository(self.session)
        sens_repo = SensorRepository(self.session)

        device = dev_repo.register_or_update(
            device_id="esp32-01",
            name="Sentry Primary",
            hardware_version="ESP32-DevKit",
            firmware_version="1.0.0",
        )
        self.assertIsNotNone(device)
        self.assertEqual(device.device_id, "esp32-01")

        sensor = sens_repo.register_or_update(
            sensor_id="esp32-01-bmp",
            device_id="esp32-01",
            sensor_type="BMP280",
            bus_type="I2C",
            address_or_pin="0x76",
        )
        self.assertEqual(sensor.sensor_id, "esp32-01-bmp")

        dev_with_sens = dev_repo.get_with_sensors("esp32-01")
        self.assertEqual(len(dev_with_sens.sensors), 1)

    def test_telemetry_repo_time_series_and_aggregates(self):
        dev_repo = DeviceRepository(self.session)
        dev_repo.register_or_update(device_id="esp32-tele", name="Telemetry Unit")

        tele_repo = TelemetryRepository(self.session)
        base_time = datetime(2026, 9, 13, 10, 0, 0, tzinfo=timezone.utc)

        # Batch insert 5 telemetry records
        records = []
        for i in range(5):
            t = base_time + timedelta(minutes=i)
            records.append({
                "device_id": "esp32-tele",
                "timestamp": t,
                "uptime_seconds": 100 * i,
                "temperature": 25.0 + i,
                "humidity": 40.0 + i,
                "pressure": 1013.0,
                "lux": 10000.0 * (i + 1),
                "rain_raw": 4000 - (100 * i),
                "rain_detected": (i == 4),
                "pan": 90,
                "tilt": 45,
                "state": "OBSERVE" if i < 4 else "SUSPEND",
                "health": 100,
            })
        inserted_count = tele_repo.record_batch(records)
        self.assertEqual(inserted_count, 5)

        # Query latest
        latest = tele_repo.get_latest("esp32-tele")
        self.assertIsNotNone(latest)
        self.assertEqual(latest.state, "SUSPEND")
        self.assertTrue(latest.rain_detected)

        # Query range
        range_records = tele_repo.get_range(
            "esp32-tele",
            start_time=base_time + timedelta(minutes=1),
            end_time=base_time + timedelta(minutes=3),
        )
        self.assertEqual(len(range_records), 3)

        # Query rain events
        rain_events = tele_repo.get_rain_events("esp32-tele")
        self.assertEqual(len(rain_events), 1)

        # Aggregation summary
        summary = tele_repo.get_aggregate_summary(
            "esp32-tele",
            start_time=base_time,
            end_time=base_time + timedelta(minutes=4),
        )
        self.assertEqual(summary["sample_count"], 5)
        self.assertEqual(summary["min_temp"], 25.0)
        self.assertEqual(summary["max_temp"], 29.0)
        self.assertEqual(summary["avg_temp"], 27.0)

    def test_command_repo_lifecycle(self):
        dev_repo = DeviceRepository(self.session)
        dev_repo.register_or_update(device_id="esp32-cmd", name="Cmd Unit")

        cmd_repo = CommandRepository(self.session)
        cmd = cmd_repo.record_command(
            command_id="cmd-999",
            device_id="esp32-cmd",
            command="SET_SERVO",
            pan=120,
            tilt=60,
        )
        self.assertEqual(cmd.command_id, "cmd-999")

        unconfirmed = cmd_repo.list_unconfirmed("esp32-cmd")
        self.assertEqual(len(unconfirmed), 1)

        # Edge returns result
        result = cmd_repo.record_result(
            command_id="cmd-999",
            status="SUCCESS",
            current_pan=120,
            current_tilt=60,
            current_state="OBSERVE",
            message="Servo transition completed",
        )
        self.assertEqual(result.status, "SUCCESS")

        # Now unconfirmed should be 0
        unconfirmed = cmd_repo.list_unconfirmed("esp32-cmd")
        self.assertEqual(len(unconfirmed), 0)

        cmd_with_res = cmd_repo.get_with_result("cmd-999")
        self.assertIsNotNone(cmd_with_res.result)
        self.assertEqual(cmd_with_res.result.current_pan, 120)

    def test_anomaly_repo_resolution(self):
        dev_repo = DeviceRepository(self.session)
        dev_repo.register_or_update(device_id="esp32-ano", name="Anomaly Unit")

        ano_repo = AnomalyRepository(self.session)
        event = ano_repo.record_anomaly(
            anomaly_id="ano-01",
            device_id="esp32-ano",
            source_subsystem="SENSOR",
            anomaly_type="VALUE_DISAGREEMENT",
            severity="CRITICAL",
            score=0.92,
            details_json={"disagreement": "DHT22 vs BMP280 delta > 5C"},
        )
        self.assertEqual(event.severity, "CRITICAL")
        self.assertFalse(event.is_resolved)

        unresolved = ano_repo.list_unresolved("esp32-ano")
        self.assertEqual(len(unresolved), 1)

        resolved = ano_repo.resolve_anomaly("ano-01", resolution_notes="Recalibrated DHT22 offset.")
        self.assertTrue(resolved.is_resolved)
        self.assertIsNotNone(resolved.resolved_at)

        unresolved_after = ano_repo.list_unresolved("esp32-ano")
        self.assertEqual(len(unresolved_after), 0)

    def test_model_version_repo(self):
        model_repo = ModelVersionRepository(self.session)
        m1 = model_repo.register_model(
            model_id="mod-vis-01",
            subsystem="VISION",
            name="solar_disk_yolo",
            version="1.0.0",
            weights_path="/models/solar_disk_v1.pt",
            is_active=True,
        )
        self.assertEqual(m1.version, "1.0.0")

        m2 = model_repo.register_model(
            model_id="mod-vis-02",
            subsystem="VISION",
            name="solar_disk_yolo",
            version="1.1.0",
            weights_path="/models/solar_disk_v1.1.pt",
            is_active=False,
        )

        # Switch active version to v1.1.0
        model_repo.set_active_version("mod-vis-02")
        active = model_repo.get_active_model("VISION", "solar_disk_yolo")
        self.assertEqual(active.model_id, "mod-vis-02")
        self.assertEqual(active.version, "1.1.0")

        # Verify old was deactivated
        old = model_repo.get_by_id("mod-vis-01")
        self.assertFalse(old.is_active)


if __name__ == "__main__":
    unittest.main()
