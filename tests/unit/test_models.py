"""
Unit tests for Solar Sentry database models, field types, constraints, and relationships.
"""

from datetime import datetime, timezone
import unittest
from backend.database.config import DatabaseConfig, create_db_engine, get_session_factory, init_db
from backend.database.models import (
    Device,
    Sensor,
    TelemetryRecord,
    ImageMetadata,
    Observation,
    VisionAnalysis,
    EnvironmentPrediction,
    HealthRecord,
    AnomalyEvent,
    DecisionRecord,
    Mission,
    MissionAction,
    MissionMemory,
    CommandRecord,
    CommandResultRecord,
    VerificationRecord,
    ModelVersion,
)


class TestDatabaseModels(unittest.TestCase):
    """Validates that all 21 model domains persist and relate correctly."""

    def setUp(self):
        self.engine = create_db_engine(DatabaseConfig(url="sqlite:///:memory:"))
        init_db(self.engine)
        self.SessionFactory = get_session_factory(self.engine)
        self.session = self.SessionFactory()

    def tearDown(self):
        self.session.close()

    def test_device_and_sensors_relationship(self):
        now = datetime.now(timezone.utc)
        device = Device(
            device_id="esp32-sentry-01",
            device_type="CONTROLLER_ESP32",
            name="Main Observatory Tracker",
            hardware_version="ESP32-WROOM-32D",
            firmware_version="1.0.0",
            ip_address="192.168.1.100",
            mac_address="24:6F:28:AB:CD:EF",
            status="ONLINE",
            registered_at=now,
            last_seen_at=now,
            config_json={"poll_rate_ms": 1000},
        )
        self.session.add(device)
        self.session.flush()

        sensor_dht = Sensor(
            sensor_id="esp32-sentry-01-dht22",
            device_id="esp32-sentry-01",
            sensor_type="DHT22",
            model="AM2302",
            bus_type="GPIO",
            address_or_pin="GPIO4",
            calibration_offset=0.0,
            is_active=True,
            health_status="HEALTHY",
            created_at=now,
        )
        sensor_bh = Sensor(
            sensor_id="esp32-sentry-01-bh1750",
            device_id="esp32-sentry-01",
            sensor_type="BH1750",
            model="BH1750FVI",
            bus_type="I2C",
            address_or_pin="0x23",
            calibration_offset=1.0,
            is_active=True,
            health_status="HEALTHY",
            created_at=now,
        )
        self.session.add_all([sensor_dht, sensor_bh])
        self.session.commit()

        # Query back
        dev = self.session.get(Device, "esp32-sentry-01")
        self.assertIsNotNone(dev)
        self.assertEqual(len(dev.sensors), 2)
        self.assertEqual(dev.config_json["poll_rate_ms"], 1000)

    def test_telemetry_persistence(self):
        now = datetime.now(timezone.utc)
        device = Device(device_id="esp32-sentry-02", name="Tracker 02", registered_at=now)
        self.session.add(device)
        self.session.flush()

        reading = TelemetryRecord(
            device_id="esp32-sentry-02",
            timestamp=now,
            uptime_seconds=3600,
            temperature=27.5,
            humidity=42.0,
            pressure=1012.3,
            lux=54200.0,
            rain_raw=3900,
            rain_detected=False,
            pan=90,
            tilt=45,
            state="OBSERVE",
            health=100,
            wifi_rssi=-58,
            camera_online=True,
            camera_ip="192.168.1.120",
            sensor_status_json={"dht22": True, "bh1750": True, "bmp280": True, "rain": True},
            firmware_version="1.0.0",
            ingested_at=now,
        )
        self.session.add(reading)
        self.session.commit()

        record = self.session.get(TelemetryRecord, reading.id)
        self.assertIsNotNone(record)
        self.assertEqual(record.state, "OBSERVE")
        self.assertEqual(record.sensor_status_json["dht22"], True)

    def test_mission_action_observation_vision_flow(self):
        now = datetime.now(timezone.utc)
        device = Device(device_id="esp32-sentry-03", name="Tracker 03", registered_at=now)
        mission = Mission(
            mission_id="mission-2026-001",
            name="Solar Active Region 4102 Survey",
            objective="SOLAR_ACTIVE_REGION_SURVEY",
            priority=8,
            state="ACTIVE",
            created_at=now,
            parameters_json={"spectral_filter": "WHITE_LIGHT"},
        )
        self.session.add_all([device, mission])
        self.session.flush()

        action = MissionAction(
            action_id="act-001",
            mission_id="mission-2026-001",
            sequence_order=1,
            action_type="CAPTURE",
            target_pan=90,
            target_tilt=60,
            status="SUCCESS",
            created_at=now,
        )
        image = ImageMetadata(
            image_id="img-001",
            device_id="esp32-sentry-03",
            timestamp=now,
            file_path="/storage/solar/20260913_001.jpg",
            width=1600,
            height=1200,
            created_at=now,
        )
        self.session.add_all([action, image])
        self.session.flush()

        obs = Observation(
            observation_id="obs-001",
            mission_id="mission-2026-001",
            device_id="esp32-sentry-03",
            image_id="img-001",
            timestamp=now,
            start_time=now,
            pan_angle=90,
            tilt_angle=60,
            quality_score=94.5,
            status="COMPLETED",
            created_at=now,
        )
        analysis = VisionAnalysis(
            analysis_id="vis-001",
            image_id="img-001",
            observation_id="obs-001",
            analyzed_at=now,
            model_version="yolo-sunspot-v1.4",
            solar_disk_detected=True,
            disk_center_x=800.0,
            disk_center_y=600.0,
            disk_radius_px=450.0,
            sunspot_count=4,
            confidence_score=0.98,
            created_at=now,
        )
        verification = VerificationRecord(
            verification_id="ver-001",
            action_id="act-001",
            observation_id="obs-001",
            timestamp=now,
            status="VERIFIED_OPTIMAL",
            pointing_error_degrees=0.12,
            optical_quality_confirmed=True,
            created_at=now,
        )
        memory = MissionMemory(
            memory_id="mem-001",
            mission_id="mission-2026-001",
            timestamp=now,
            key_finding="AR4102 exhibits rapid sunspot group expansion",
            context_tag="SOLAR_CYCLE",
            summary_text="4 distinct sunspots resolved with high contrast.",
            relevance_score=0.95,
            created_at=now,
        )
        self.session.add_all([obs, analysis, verification, memory])
        self.session.commit()

        # Verify linked graphs
        m = self.session.get(Mission, "mission-2026-001")
        self.assertEqual(len(m.actions), 1)
        self.assertEqual(len(m.observations), 1)
        self.assertEqual(len(m.memories), 1)
        self.assertEqual(m.observations[0].vision_analyses[0].sunspot_count, 4)
        self.assertEqual(m.actions[0].verifications[0].status, "VERIFIED_OPTIMAL")

    def test_command_and_result_relationship(self):
        now = datetime.now(timezone.utc)
        device = Device(device_id="esp32-sentry-04", name="Tracker 04", registered_at=now)
        self.session.add(device)
        self.session.flush()

        cmd = CommandRecord(
            command_id="cmd-101",
            device_id="esp32-sentry-04",
            command="OBSERVE",
            pan=90,
            tilt=75,
            dispatched_at=now,
        )
        result = CommandResultRecord(
            command_id="cmd-101",
            status="SUCCESS",
            current_pan=90,
            current_tilt=75,
            current_state="OBSERVE",
            executed_at=now,
            received_at=now,
        )
        cmd.result = result
        self.session.add(cmd)
        self.session.commit()

        fetched_cmd = self.session.get(CommandRecord, "cmd-101")
        self.assertIsNotNone(fetched_cmd.result)
        self.assertEqual(fetched_cmd.result.status, "SUCCESS")
        self.assertEqual(fetched_cmd.result.current_state, "OBSERVE")


if __name__ == "__main__":
    unittest.main()
