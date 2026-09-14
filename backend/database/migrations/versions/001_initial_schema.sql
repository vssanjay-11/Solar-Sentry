-- Solar Sentry Schema Migration 001
-- Initial schema: Devices, Sensors, Telemetry, Images, Observations, Vision,
-- Predictions, Health, Anomalies, Decisions, Missions, Actions, Commands, Results, Verifications, Memory, Models

-- 1. Devices
CREATE TABLE IF NOT EXISTS devices (
    device_id VARCHAR(64) PRIMARY KEY,
    device_type VARCHAR(32) NOT NULL DEFAULT 'CONTROLLER_ESP32',
    name VARCHAR(128) NOT NULL,
    hardware_version VARCHAR(32),
    firmware_version VARCHAR(32),
    ip_address VARCHAR(45),
    mac_address VARCHAR(32),
    status VARCHAR(32) NOT NULL DEFAULT 'ONLINE',
    registered_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_seen_at TIMESTAMP WITH TIME ZONE,
    config_json TEXT
);
CREATE INDEX IF NOT EXISTS ix_devices_status ON devices(status);
CREATE INDEX IF NOT EXISTS ix_devices_type ON devices(device_type);
CREATE INDEX IF NOT EXISTS ix_devices_last_seen ON devices(last_seen_at);

-- 2. Sensors
CREATE TABLE IF NOT EXISTS sensors (
    sensor_id VARCHAR(64) PRIMARY KEY,
    device_id VARCHAR(64) NOT NULL,
    sensor_type VARCHAR(32) NOT NULL,
    model VARCHAR(64),
    bus_type VARCHAR(32) NOT NULL DEFAULT 'I2C',
    address_or_pin VARCHAR(32),
    calibration_offset FLOAT NOT NULL DEFAULT 0.0,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    health_status VARCHAR(32) NOT NULL DEFAULT 'HEALTHY',
    metadata_json TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_sensors_device_id ON sensors(device_id);
CREATE INDEX IF NOT EXISTS ix_sensors_device_type ON sensors(device_id, sensor_type);

-- 3. Telemetry Records
CREATE TABLE IF NOT EXISTS telemetry_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id VARCHAR(64) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    uptime_seconds INTEGER NOT NULL DEFAULT 0,
    temperature FLOAT NOT NULL,
    humidity FLOAT NOT NULL,
    pressure FLOAT NOT NULL,
    lux FLOAT NOT NULL,
    rain_raw INTEGER NOT NULL,
    rain_detected BOOLEAN NOT NULL DEFAULT 0,
    pan INTEGER NOT NULL,
    tilt INTEGER NOT NULL,
    state VARCHAR(32) NOT NULL,
    health INTEGER NOT NULL DEFAULT 100,
    wifi_rssi INTEGER,
    camera_online BOOLEAN NOT NULL DEFAULT 0,
    camera_ip VARCHAR(45),
    sensor_status_json TEXT,
    firmware_version VARCHAR(32),
    ingested_at TIMESTAMP WITH TIME ZONE NOT NULL,
    FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_telemetry_records_device_id ON telemetry_records(device_id);
CREATE INDEX IF NOT EXISTS ix_telemetry_records_timestamp ON telemetry_records(timestamp);
CREATE INDEX IF NOT EXISTS ix_telemetry_records_state ON telemetry_records(state);
CREATE INDEX IF NOT EXISTS ix_telemetry_device_timestamp ON telemetry_records(device_id, timestamp);
CREATE INDEX IF NOT EXISTS ix_telemetry_timestamp_state ON telemetry_records(timestamp, state);
CREATE INDEX IF NOT EXISTS ix_telemetry_rain_detected ON telemetry_records(rain_detected);

-- 4. Image Metadata
CREATE TABLE IF NOT EXISTS image_metadata (
    image_id VARCHAR(64) PRIMARY KEY,
    device_id VARCHAR(64) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    file_path VARCHAR(512) NOT NULL,
    storage_uri VARCHAR(512),
    format VARCHAR(16) NOT NULL DEFAULT 'JPEG',
    width INTEGER NOT NULL DEFAULT 640,
    height INTEGER NOT NULL DEFAULT 480,
    file_size_bytes INTEGER NOT NULL DEFAULT 0,
    exposure_time_ms FLOAT,
    gain FLOAT,
    pan_angle INTEGER,
    tilt_angle INTEGER,
    checksum_sha256 VARCHAR(64),
    metadata_json TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_images_device_id ON image_metadata(device_id);
CREATE INDEX IF NOT EXISTS ix_images_timestamp ON image_metadata(timestamp);
CREATE INDEX IF NOT EXISTS ix_images_device_timestamp ON image_metadata(device_id, timestamp);

-- 5. Missions
CREATE TABLE IF NOT EXISTS missions (
    mission_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    mission_type VARCHAR(32) NOT NULL DEFAULT 'OBSERVE',
    objective VARCHAR(64) NOT NULL,
    priority INTEGER NOT NULL DEFAULT 5,
    state VARCHAR(32) NOT NULL DEFAULT 'PLANNED',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    target_coordinates_json TEXT,
    parameters_json TEXT
);
CREATE INDEX IF NOT EXISTS ix_missions_state ON missions(state);
CREATE INDEX IF NOT EXISTS ix_missions_type ON missions(mission_type);
CREATE INDEX IF NOT EXISTS ix_missions_created_at ON missions(created_at);
CREATE INDEX IF NOT EXISTS ix_missions_state_created ON missions(state, created_at);
CREATE INDEX IF NOT EXISTS ix_missions_priority ON missions(priority);

-- 6. Observations
CREATE TABLE IF NOT EXISTS observations (
    observation_id VARCHAR(64) PRIMARY KEY,
    mission_id VARCHAR(64),
    device_id VARCHAR(64) NOT NULL,
    image_id VARCHAR(64),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE,
    pan_angle INTEGER NOT NULL DEFAULT 90,
    tilt_angle INTEGER NOT NULL DEFAULT 45,
    solar_elevation FLOAT,
    solar_azimuth FLOAT,
    ambient_lux FLOAT,
    cloud_cover_pct FLOAT,
    status VARCHAR(32) NOT NULL DEFAULT 'COMPLETED',
    quality_score FLOAT,
    notes TEXT,
    metadata_json TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    FOREIGN KEY (mission_id) REFERENCES missions(mission_id) ON DELETE SET NULL,
    FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE,
    FOREIGN KEY (image_id) REFERENCES image_metadata(image_id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS ix_observations_mission_id ON observations(mission_id);
CREATE INDEX IF NOT EXISTS ix_observations_device_id ON observations(device_id);
CREATE INDEX IF NOT EXISTS ix_observations_image_id ON observations(image_id);
CREATE INDEX IF NOT EXISTS ix_observations_timestamp ON observations(timestamp);
CREATE INDEX IF NOT EXISTS ix_observations_device_timestamp ON observations(device_id, timestamp);
CREATE INDEX IF NOT EXISTS ix_observations_status ON observations(status);
CREATE INDEX IF NOT EXISTS ix_observations_quality ON observations(quality_score);

-- 7. Vision Analyses
CREATE TABLE IF NOT EXISTS vision_analyses (
    analysis_id VARCHAR(64) PRIMARY KEY,
    image_id VARCHAR(64) NOT NULL,
    observation_id VARCHAR(64),
    analyzed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    model_version VARCHAR(64) NOT NULL,
    solar_disk_detected BOOLEAN NOT NULL DEFAULT 0,
    disk_center_x FLOAT,
    disk_center_y FLOAT,
    disk_radius_px FLOAT,
    sunspot_count INTEGER NOT NULL DEFAULT 0,
    limb_darkening_score FLOAT,
    cloud_obstruction_pct FLOAT,
    flare_candidate BOOLEAN NOT NULL DEFAULT 0,
    confidence_score FLOAT NOT NULL DEFAULT 1.0,
    features_json TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    FOREIGN KEY (image_id) REFERENCES image_metadata(image_id) ON DELETE CASCADE,
    FOREIGN KEY (observation_id) REFERENCES observations(observation_id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS ix_vision_analyses_image_id ON vision_analyses(image_id);
CREATE INDEX IF NOT EXISTS ix_vision_analyses_observation_id ON vision_analyses(observation_id);
CREATE INDEX IF NOT EXISTS ix_vision_analyses_analyzed_at ON vision_analyses(analyzed_at);
CREATE INDEX IF NOT EXISTS ix_vision_analyses_model_version ON vision_analyses(model_version);
CREATE INDEX IF NOT EXISTS ix_vision_sunspots ON vision_analyses(sunspot_count);
CREATE INDEX IF NOT EXISTS ix_vision_disk_detected ON vision_analyses(solar_disk_detected);

-- 8. Environment Predictions
CREATE TABLE IF NOT EXISTS environment_predictions (
    prediction_id VARCHAR(64) PRIMARY KEY,
    device_id VARCHAR(64) NOT NULL,
    generated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    target_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    horizon_minutes INTEGER NOT NULL,
    predicted_quality_score FLOAT NOT NULL,
    predicted_cloud_cover_pct FLOAT NOT NULL,
    predicted_lux FLOAT,
    rain_probability FLOAT NOT NULL DEFAULT 0.0,
    confidence FLOAT DEFAULT 1.0,
    risk VARCHAR(32) DEFAULT 'LOW',
    model_version VARCHAR(64) NOT NULL,
    uncertainty_bounds_json TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_environment_predictions_device_id ON environment_predictions(device_id);
CREATE INDEX IF NOT EXISTS ix_environment_predictions_generated_at ON environment_predictions(generated_at);
CREATE INDEX IF NOT EXISTS ix_environment_predictions_target_timestamp ON environment_predictions(target_timestamp);
CREATE INDEX IF NOT EXISTS ix_predictions_target_horizon ON environment_predictions(target_timestamp, horizon_minutes);
CREATE INDEX IF NOT EXISTS ix_predictions_device_generated ON environment_predictions(device_id, generated_at);
CREATE INDEX IF NOT EXISTS ix_predictions_risk ON environment_predictions(risk);

-- 9. Health Records
CREATE TABLE IF NOT EXISTS health_records (
    health_id VARCHAR(64) PRIMARY KEY,
    device_id VARCHAR(64) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    overall_health_score INTEGER NOT NULL DEFAULT 100,
    power_status VARCHAR(32) NOT NULL DEFAULT 'NORMAL',
    thermal_status VARCHAR(32) NOT NULL DEFAULT 'NORMAL',
    actuator_status VARCHAR(32) NOT NULL DEFAULT 'OPERATIONAL',
    comms_status VARCHAR(32) NOT NULL DEFAULT 'HEALTHY',
    sensor_health_json TEXT,
    degraded_reason VARCHAR(256),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_health_records_device_id ON health_records(device_id);
CREATE INDEX IF NOT EXISTS ix_health_records_timestamp ON health_records(timestamp);
CREATE INDEX IF NOT EXISTS ix_health_device_timestamp ON health_records(device_id, timestamp);
CREATE INDEX IF NOT EXISTS ix_health_score ON health_records(overall_health_score);

-- 10. Anomaly Events
CREATE TABLE IF NOT EXISTS anomaly_events (
    anomaly_id VARCHAR(64) PRIMARY KEY,
    device_id VARCHAR(64) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    source_subsystem VARCHAR(32) NOT NULL,
    anomaly_type VARCHAR(64) NOT NULL,
    severity VARCHAR(32) NOT NULL DEFAULT 'WARNING',
    score FLOAT NOT NULL DEFAULT 1.0,
    details_json TEXT,
    is_resolved BOOLEAN NOT NULL DEFAULT 0,
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolution_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_anomaly_events_device_id ON anomaly_events(device_id);
CREATE INDEX IF NOT EXISTS ix_anomaly_events_timestamp ON anomaly_events(timestamp);
CREATE INDEX IF NOT EXISTS ix_anomaly_events_anomaly_type ON anomaly_events(anomaly_type);
CREATE INDEX IF NOT EXISTS ix_anomaly_events_is_resolved ON anomaly_events(is_resolved);
CREATE INDEX IF NOT EXISTS ix_anomaly_device_timestamp ON anomaly_events(device_id, timestamp);
CREATE INDEX IF NOT EXISTS ix_anomaly_severity_score ON anomaly_events(severity, score);

-- 11. Decision Records
CREATE TABLE IF NOT EXISTS decision_records (
    decision_id VARCHAR(64) PRIMARY KEY,
    device_id VARCHAR(64) NOT NULL,
    mission_id VARCHAR(64),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    action_proposed VARCHAR(32) NOT NULL,
    confidence FLOAT NOT NULL DEFAULT 1.0,
    risk VARCHAR(32),
    mode VARCHAR(32),
    fused_utility FLOAT,
    total_uncertainty FLOAT,
    reasoning_trace TEXT NOT NULL,
    inputs_summary_json TEXT,
    override_applied BOOLEAN NOT NULL DEFAULT 0,
    override_reason VARCHAR(256),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE,
    FOREIGN KEY (mission_id) REFERENCES missions(mission_id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS ix_decision_records_device_id ON decision_records(device_id);
CREATE INDEX IF NOT EXISTS ix_decision_records_mission_id ON decision_records(mission_id);
CREATE INDEX IF NOT EXISTS ix_decision_records_timestamp ON decision_records(timestamp);
CREATE INDEX IF NOT EXISTS ix_decisions_device_timestamp ON decision_records(device_id, timestamp);
CREATE INDEX IF NOT EXISTS ix_decisions_action ON decision_records(action_proposed);
CREATE INDEX IF NOT EXISTS ix_decisions_risk_mode ON decision_records(risk, mode);

-- 12. Mission Actions
CREATE TABLE IF NOT EXISTS mission_actions (
    action_id VARCHAR(64) PRIMARY KEY,
    mission_id VARCHAR(64) NOT NULL,
    sequence_order INTEGER NOT NULL,
    action_type VARCHAR(32) NOT NULL,
    target_pan INTEGER,
    target_tilt INTEGER,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    result_json TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    FOREIGN KEY (mission_id) REFERENCES missions(mission_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_mission_actions_mission_id ON mission_actions(mission_id);
CREATE INDEX IF NOT EXISTS ix_mission_actions_status ON mission_actions(status);
CREATE INDEX IF NOT EXISTS ix_mission_actions_order ON mission_actions(mission_id, sequence_order);

-- 13. Mission Memories
CREATE TABLE IF NOT EXISTS mission_memories (
    memory_id VARCHAR(64) PRIMARY KEY,
    mission_id VARCHAR(64),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    key_finding VARCHAR(256) NOT NULL,
    context_tag VARCHAR(64) NOT NULL,
    summary_text TEXT NOT NULL,
    structured_payload_json TEXT,
    relevance_score FLOAT NOT NULL DEFAULT 1.0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    FOREIGN KEY (mission_id) REFERENCES missions(mission_id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS ix_mission_memories_mission_id ON mission_memories(mission_id);
CREATE INDEX IF NOT EXISTS ix_mission_memories_timestamp ON mission_memories(timestamp);
CREATE INDEX IF NOT EXISTS ix_mission_memories_context_tag ON mission_memories(context_tag);
CREATE INDEX IF NOT EXISTS ix_mission_memories_tag_time ON mission_memories(context_tag, timestamp);

-- 14. Commands
CREATE TABLE IF NOT EXISTS commands (
    command_id VARCHAR(64) PRIMARY KEY,
    device_id VARCHAR(64) NOT NULL,
    command VARCHAR(32) NOT NULL,
    pan INTEGER,
    tilt INTEGER,
    speed INTEGER DEFAULT 100,
    target_state VARCHAR(32),
    dispatched_at TIMESTAMP WITH TIME ZONE NOT NULL,
    source VARCHAR(64) NOT NULL DEFAULT 'MISSION_PLANNER',
    parameters_json TEXT,
    FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_commands_device_id ON commands(device_id);
CREATE INDEX IF NOT EXISTS ix_commands_dispatched_at ON commands(dispatched_at);
CREATE INDEX IF NOT EXISTS ix_commands_device_dispatched ON commands(device_id, dispatched_at);
CREATE INDEX IF NOT EXISTS ix_commands_verb ON commands(command);

-- 15. Command Results
CREATE TABLE IF NOT EXISTS command_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    command_id VARCHAR(64) NOT NULL UNIQUE,
    status VARCHAR(32) NOT NULL,
    message VARCHAR(512),
    current_pan INTEGER NOT NULL,
    current_tilt INTEGER NOT NULL,
    current_state VARCHAR(32) NOT NULL,
    executed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    received_at TIMESTAMP WITH TIME ZONE NOT NULL,
    FOREIGN KEY (command_id) REFERENCES commands(command_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_command_results_command_id ON command_results(command_id);
CREATE INDEX IF NOT EXISTS ix_command_results_status ON command_results(status);
CREATE INDEX IF NOT EXISTS ix_command_results_current_state ON command_results(current_state);
CREATE INDEX IF NOT EXISTS ix_command_results_executed_at ON command_results(executed_at);
CREATE INDEX IF NOT EXISTS ix_command_results_state_status ON command_results(current_state, status);

-- 16. Verification Records
CREATE TABLE IF NOT EXISTS verification_records (
    verification_id VARCHAR(64) PRIMARY KEY,
    action_id VARCHAR(64),
    observation_id VARCHAR(64),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'SUCCESS',
    pointing_error_degrees FLOAT,
    optical_quality_confirmed BOOLEAN NOT NULL DEFAULT 1,
    quality_before FLOAT,
    quality_after FLOAT,
    delta_quality FLOAT,
    converged BOOLEAN DEFAULT 1,
    verification_metrics_json TEXT,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    FOREIGN KEY (action_id) REFERENCES mission_actions(action_id) ON DELETE SET NULL,
    FOREIGN KEY (observation_id) REFERENCES observations(observation_id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS ix_verification_records_action_id ON verification_records(action_id);
CREATE INDEX IF NOT EXISTS ix_verification_records_observation_id ON verification_records(observation_id);
CREATE INDEX IF NOT EXISTS ix_verification_records_timestamp ON verification_records(timestamp);
CREATE INDEX IF NOT EXISTS ix_verification_records_status ON verification_records(status);
CREATE INDEX IF NOT EXISTS ix_verification_status_time ON verification_records(status, timestamp);

-- 17. Model Versions
CREATE TABLE IF NOT EXISTS model_versions (
    model_id VARCHAR(64) PRIMARY KEY,
    subsystem VARCHAR(32) NOT NULL,
    name VARCHAR(128) NOT NULL,
    version VARCHAR(32) NOT NULL,
    weights_path VARCHAR(512),
    architecture_desc VARCHAR(256),
    parameters_hash VARCHAR(64),
    trained_at TIMESTAMP WITH TIME ZONE,
    metrics_json TEXT,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT uq_model_name_version UNIQUE (name, version)
);
CREATE INDEX IF NOT EXISTS ix_model_versions_subsystem ON model_versions(subsystem);
CREATE INDEX IF NOT EXISTS ix_model_versions_is_active ON model_versions(is_active);
CREATE INDEX IF NOT EXISTS ix_models_subsystem_active ON model_versions(subsystem, is_active);
