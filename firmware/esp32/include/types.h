#pragma once

#include <Arduino.h>

/**
 * ============================================================
 * SOLAR SENTRY — DATA TYPES & PROTOCOL DEFINITIONS
 * Module: Edge Device + ESP32 Integration (Agent 1)
 * ============================================================
 */

// System State Enum matching contracts/system-state.md
enum class DeviceState {
    BOOT,
    SELF_CHECK,
    STANDBY,
    OBSERVE,
    WAIT,
    SCAN,
    SUSPEND,
    FAULT,
    SAFE,
    DEGRADED
};

inline const char* deviceStateToString(DeviceState state) {
    switch (state) {
        case DeviceState::BOOT:        return "BOOT";
        case DeviceState::SELF_CHECK:  return "SELF_CHECK";
        case DeviceState::STANDBY:     return "STANDBY";
        case DeviceState::OBSERVE:     return "OBSERVE";
        case DeviceState::WAIT:        return "WAIT";
        case DeviceState::SCAN:        return "SCAN";
        case DeviceState::SUSPEND:     return "SUSPEND";
        case DeviceState::FAULT:       return "FAULT";
        case DeviceState::SAFE:        return "SAFE";
        case DeviceState::DEGRADED:    return "DEGRADED";
        default:                       return "UNKNOWN";
    }
}

inline DeviceState stringToDeviceState(const char* str) {
    if (strcmp(str, "BOOT") == 0)        return DeviceState::BOOT;
    if (strcmp(str, "SELF_CHECK") == 0)  return DeviceState::SELF_CHECK;
    if (strcmp(str, "STANDBY") == 0)     return DeviceState::STANDBY;
    if (strcmp(str, "OBSERVE") == 0)     return DeviceState::OBSERVE;
    if (strcmp(str, "WAIT") == 0)        return DeviceState::WAIT;
    if (strcmp(str, "SCAN") == 0)        return DeviceState::SCAN;
    if (strcmp(str, "SUSPEND") == 0)     return DeviceState::SUSPEND;
    if (strcmp(str, "FAULT") == 0)       return DeviceState::FAULT;
    if (strcmp(str, "SAFE") == 0)        return DeviceState::SAFE;
    if (strcmp(str, "DEGRADED") == 0)    return DeviceState::DEGRADED;
    return DeviceState::STANDBY;
}

// Environmental and Physical Sensor Readings
struct SensorReadings {
    float temperature;    // Celsius (from DHT22 or BMP280 fallback)
    float humidity;       // % RH (from DHT22)
    float pressure;       // hPa (from BMP280)
    float lux;            // Lux (from BH1750)
    int   rain_raw;       // 12-bit ADC (0 - 4095)
    bool  rain_detected;  // Active low detection debounced

    // Diagnostic validation flags
    bool  dht_valid;
    bool  bmp_valid;
    bool  bh1750_valid;
    bool  rain_valid;

    unsigned long timestamp_ms;
};

// Actuator Tracker State
struct ActuatorState {
    int current_pan;
    int current_tilt;
    int target_pan;
    int target_tilt;
    bool moving;
};

// Subsystem Health Tracking
struct SubsystemHealth {
    bool dht_ok;
    bool bh1750_ok;
    bool bmp280_ok;
    bool rain_ok;
    bool pan_servo_ok;
    bool tilt_servo_ok;
    bool wifi_connected;
    bool backend_reachable;
    bool camera_reachable;
    int  error_count;
    int  overall_score; // 0 - 100
};

// Inbound Command Definition
struct CommandPayload {
    char command_id[36];
    char command[24]; // OBSERVE, PARK, SCAN, SET_SERVO, SET_STATE, REBOOT, CALIBRATE
    int  pan;
    int  tilt;
    int  speed;
    char target_state[16];
    bool valid;
};

// Command Execution Result
struct CommandResultPayload {
    char command_id[36];
    char status[24]; // SUCCESS, REJECTED_SAFETY, INVALID_PARAMS, EXECUTION_ERROR
    char message[64];
    int  current_pan;
    int  current_tilt;
    char current_state[16];
};
