#include <Arduino.h>
#include <esp_task_wdt.h>
#include "config.h"
#include "types.h"
#include "sensors/SensorManager.h"
#include "actuators/ActuatorManager.h"
#include "safety/SafetyMonitor.h"
#include "comms/NetworkManager.h"
#include "comms/CameraBridge.h"
#include "comms/BackendClient.h"

/**
 * ============================================================
 * SOLAR SENTRY — ESP32 DEV-KIT MAIN FIRMWARE
 * Autonomous Cognitive Solar Observatory & Scientific Discovery Platform
 * Module: Edge Device + ESP32 Integration (Agent 1)
 * ============================================================
 */

// Subsystem singletons
SensorManager   sensors;
ActuatorManager actuators;
SafetyMonitor   safety(actuators);
NetworkManager  network;
CameraBridge    cameraBridge;
BackendClient   backend(actuators, safety);

// Cooperative task scheduling timers
unsigned long lastSensorReadTimeMs = 0;
unsigned long lastTelemetryTimeMs = 0;
unsigned long lastSafetyCheckTimeMs = 0;
unsigned long lastCommandPollTimeMs = 0;
unsigned long lastHeartbeatLogTimeMs = 0;

void printSystemBanner() {
    Serial.println("\n============================================================");
    Serial.println("  SOLAR SENTRY — EDGE CONTROLLER FIRMWARE");
    Serial.printf ("  Device ID: %s | Firmware Version: %s\n", DEVICE_ID, FIRMWARE_VERSION);
    Serial.println("  Hardware: ESP32 DevKit + DHT22 + BH1750 + BMP280 + Servos");
    Serial.println("============================================================\n");
}

void setup() {
    Serial.begin(115200);
    delay(1000);
    printSystemBanner();

    // 1. Initialize Actuators & Indicators first so hardware enters safe pose
    Serial.println("[Boot] Initializing Actuators and LEDs...");
    actuators.begin();

    // 2. Initialize Sensors
    Serial.println("[Boot] Initializing Environmental Sensors...");
    sensors.begin();

    // 3. Initialize Safety Monitor
    Serial.println("[Boot] Initializing Safety Monitor...");
    safety.begin();

    // 4. Initial Self-Check & Health Evaluation
    sensors.update();
    const SensorReadings& initialReadings = sensors.getReadings();
    safety.update(initialReadings, false);

    if (safety.isSafeToObserve()) {
        safety.requestStateChange(DeviceState::STANDBY);
    } else {
        safety.requestStateChange(DeviceState::DEGRADED);
    }

    // 5. Initialize Network & Communications
    Serial.println("[Boot] Initializing Wi-Fi Network Manager...");
    network.begin();

    Serial.println("[Boot] Initializing Backend Client & Camera Bridge...");
    cameraBridge.begin();
    backend.begin();

    // 6. Initialize Hardware Watchdog (10s timeout)
    Serial.println("[Boot] Configuring ESP32 Hardware Task Watchdog (10s)...");
#if ESP_IDF_VERSION_MAJOR >= 5
    esp_task_wdt_config_t wdt_config = {
        .timeout_ms = WATCHDOG_TIMEOUT_SEC * 1000,
        .idle_core_mask = (1 << portNUM_PROCESSORS) - 1,
        .trigger_panic = true
    };
    esp_task_wdt_init(&wdt_config);
#else
    esp_task_wdt_init(WATCHDOG_TIMEOUT_SEC, true);
#endif
    esp_task_wdt_add(NULL); // Add current loop task to watchdog

    Serial.println("[Boot] Initialization complete. Entering operational loop.\n");
}

void loop() {
    // 1. Feed the hardware watchdog every iteration
    esp_task_wdt_reset();

    unsigned long now = millis();

    // 2. High-rate actuator & LED update (Smooth 50 Hz motion and animations)
    actuators.update();

    // 3. Network state machine update
    network.update();

    // 4. Safety Interlock evaluation (5 Hz rate)
    if (now - lastSafetyCheckTimeMs >= INTERVAL_SAFETY_CHECK_MS) {
        lastSafetyCheckTimeMs = now;
        safety.update(sensors.getReadings(), backend.isBackendReachable());
    }

    // 5. Sensor acquisition task (1 Hz rate)
    if (now - lastSensorReadTimeMs >= INTERVAL_SENSOR_READ_MS) {
        lastSensorReadTimeMs = now;
        sensors.update();
    }

    // 6. Camera health ping
    cameraBridge.update();

    // 7. Command polling from central backend (every 2 seconds)
    if (now - lastCommandPollTimeMs >= 2000) {
        lastCommandPollTimeMs = now;
        backend.pollCommands();
    }

    // 8. Telemetry dispatch (every 3 seconds)
    if (now - lastTelemetryTimeMs >= INTERVAL_TELEMETRY_SEND_MS) {
        lastTelemetryTimeMs = now;

        const SensorReadings& r = sensors.getReadings();
        const ActuatorState& a = actuators.getState();
        const SubsystemHealth& h = safety.getHealth();

        backend.sendTelemetry(
            r,
            a,
            safety.getState(),
            h.overall_score,
            network.getRSSI(),
            cameraBridge.isCameraOnline(),
            cameraBridge.getCameraIP()
        );
    }

    // 9. Periodic Heartbeat Serial Log (every 5 seconds)
    if (now - lastHeartbeatLogTimeMs >= INTERVAL_HEARTBEAT_MS) {
        lastHeartbeatLogTimeMs = now;
        const SensorReadings& r = sensors.getReadings();
        const ActuatorState& a = actuators.getState();
        const SubsystemHealth& h = safety.getHealth();

        Serial.printf("[Heartbeat] State: %-8s | Health: %3d | Pan: %3d° | Tilt: %3d° | Temp: %4.1f°C | Hum: %4.1f%% | Lux: %6.1f | Rain: %4d (%s) | Wi-Fi: %d dBm\n",
                      deviceStateToString(safety.getState()),
                      h.overall_score,
                      a.current_pan,
                      a.current_tilt,
                      r.temperature,
                      r.humidity,
                      r.lux,
                      r.rain_raw,
                      r.rain_detected ? "WET" : "DRY",
                      network.getRSSI());
    }

    // Yield to FreeRTOS scheduler
    yield();
}
