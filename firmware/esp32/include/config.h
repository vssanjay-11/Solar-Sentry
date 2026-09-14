#pragma once

#include <Arduino.h>

/**
 * ============================================================
 * SOLAR SENTRY — HARDWARE & RUNTIME CONFIGURATION
 * Module: Edge Device + ESP32 Integration (Agent 1)
 * ============================================================
 */

// --- IDENTIFICATION ---
#define DEVICE_ID             "esp32-sentry-01"
#define FIRMWARE_VERSION      "1.0.0"

// --- HARDWARE PIN CONTRACT ---
// DHT22 (Temperature & Humidity)
#define PIN_DHT               4

// I2C Bus (Shared between BH1750 and BMP280)
#define PIN_I2C_SDA           21
#define PIN_I2C_SCL           22
#define I2C_CLOCK_SPEED       100000 // 100 kHz standard mode

// I2C Addresses
#define ADDR_BH1750           0x23
#define ADDR_BMP280           0x76 // Or 0x77 depending on SDO pin tie

// Rain Sensor (Analog on ADC1)
#define PIN_RAIN_ANALOG       34

// Servos (Dual-Axis Pan & Tilt Tracker)
#define PIN_SERVO_PAN         18
#define PIN_SERVO_TILT        19

// Status Indicator LEDs
#define PIN_LED_GREEN         25
#define PIN_LED_YELLOW        26
#define PIN_LED_RED           27

// --- ACTUATOR LIMITS & DEFAULTS ---
#define PAN_MIN_DEG           0
#define PAN_MAX_DEG           180
#define TILT_MIN_DEG          0
#define TILT_MAX_DEG          180

// Safe / Stow Position (Protective downward tilt, centered pan)
#define PAN_SAFE_DEG          90
#define TILT_SAFE_DEG         0

// Servo Motion Smoothing
#define SERVO_STEP_INTERVAL_MS 20 // Step interval for smooth slewing
#define SERVO_DEFAULT_SPEED_DEG_PER_SEC 45

// --- SENSOR THRESHOLDS & VALIDATION ---
// Rain threshold: 12-bit ADC reading below this triggers rain event (active low moisture)
#define RAIN_THRESHOLD_ADC    2000
#define RAIN_DEBOUNCE_SAMPLES 3

// Environmental sanity ranges
#define TEMP_MIN_PLAUSIBLE_C  -20.0f
#define TEMP_MAX_PLAUSIBLE_C  70.0f
#define HUMID_MIN_PLAUSIBLE   0.0f
#define HUMID_MAX_PLAUSIBLE   100.0f
#define PRESS_MIN_PLAUSIBLE   800.0f  // hPa
#define PRESS_MAX_PLAUSIBLE   1150.0f // hPa
#define LUX_MIN_PLAUSIBLE     0.0f
#define LUX_MAX_PLAUSIBLE     65535.0f

// --- SAFETY & WATCHDOG ---
#define WATCHDOG_TIMEOUT_SEC  10
#define COMMS_TIMEOUT_MS      30000 // 30s communication loss triggers SAFE state
#define OVERHEAT_SHUTDOWN_C   65.0f

// --- TIMING INTERVALS (Cooperative Tasks) ---
#define INTERVAL_SENSOR_READ_MS     1000 // 1 Hz sensor acquisition
#define INTERVAL_TELEMETRY_SEND_MS  3000 // 3-second telemetry transmission
#define INTERVAL_SAFETY_CHECK_MS    200  // 5 Hz safety interlock evaluation
#define INTERVAL_HEARTBEAT_MS       5000 // 5-second local heartbeat
#define INTERVAL_LED_UPDATE_MS      50   // 20 Hz LED animation loop
#define INTERVAL_CAM_PING_MS        10000 // 10-second camera status ping

// --- NETWORK & BACKEND DEFAULT SETTINGS ---
#ifndef WIFI_SSID
#define WIFI_SSID             "SolarSentry_Net"
#endif

#ifndef WIFI_PASSWORD
#define WIFI_PASSWORD         "SolarSentryPass2026"
#endif

#define BACKEND_HOST          "192.168.1.100"
#define BACKEND_PORT          8000
#define TELEMETRY_ENDPOINT    "/api/v1/telemetry"
#define COMMAND_POLL_ENDPOINT "/api/v1/device/command/poll"
#define CAMERA_DEFAULT_IP     "192.168.1.120"
#define CAMERA_PORT           80
