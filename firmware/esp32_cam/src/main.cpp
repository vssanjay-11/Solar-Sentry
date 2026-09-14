#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include "esp_camera.h"

/**
 * ============================================================
 * SOLAR SENTRY — ESP32-CAM PROTOTYPE VISION NODE
 * Module: Edge Device + Vision Node Integration (Agent 1)
 *
 * NOTE: Environmental & prototype camera node. NOT intended to
 * replace observatory-grade scientific solar cameras.
 * ============================================================
 */

// AI-Thinker ESP32-CAM Pin Mapping
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

// Network configuration
#ifndef WIFI_SSID
#define WIFI_SSID         "SolarSentry_Net"
#endif

#ifndef WIFI_PASSWORD
#define WIFI_PASSWORD     "SolarSentryPass2026"
#endif

WebServer server(80);
bool cameraInitialized = false;
unsigned long captureCount = 0;

void handleStatus() {
    String json = "{\n";
    json += "  \"node_type\": \"ESP32-CAM\",\n";
    json += "  \"camera_healthy\": " + String(cameraInitialized ? "true" : "false") + ",\n";
    json += "  \"resolution\": \"SVGA_800x600\",\n";
    json += "  \"captures_served\": " + String(captureCount) + ",\n";
    json += "  \"uptime_seconds\": " + String(millis() / 1000) + ",\n";
    json += "  \"wifi_rssi\": " + String(WiFi.RSSI()) + "\n";
    json += "}";
    server.send(200, "application/json", json);
}

void handleCapture() {
    if (!cameraInitialized) {
        server.send(503, "application/json", "{\"error\":\"Camera sensor not initialized\"}");
        return;
    }

    camera_fb_t* fb = esp_camera_fb_get();
    if (!fb) {
        Serial.println("[Cam] Camera capture failed!");
        server.send(500, "application/json", "{\"error\":\"Frame capture failed\"}");
        return;
    }

    captureCount++;
    server.sendHeader("Content-Disposition", "inline; filename=solar_obs.jpg");
    server.send_P(200, "image/jpeg", (const char*)fb->buf, fb->len);
    esp_camera_fb_return(fb);
}

void setup() {
    Serial.begin(115200);
    delay(500);
    Serial.println("\n[Cam] Solar Sentry ESP32-CAM Node Booting...");

    camera_config_t config;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer = LEDC_TIMER_0;
    config.pin_d0 = Y2_GPIO_NUM;
    config.pin_d1 = Y3_GPIO_NUM;
    config.pin_d2 = Y4_GPIO_NUM;
    config.pin_d3 = Y5_GPIO_NUM;
    config.pin_d4 = Y6_GPIO_NUM;
    config.pin_d5 = Y7_GPIO_NUM;
    config.pin_d6 = Y8_GPIO_NUM;
    config.pin_d7 = Y9_GPIO_NUM;
    config.pin_xclk = XCLK_GPIO_NUM;
    config.pin_pclk = PCLK_GPIO_NUM;
    config.pin_vsync = VSYNC_GPIO_NUM;
    config.pin_href = HREF_GPIO_NUM;
    config.pin_sccb_sda = SIOD_GPIO_NUM;
    config.pin_sccb_scl = SIOC_GPIO_NUM;
    config.pin_pwdn = PWDN_GPIO_NUM;
    config.pin_reset = RESET_GPIO_NUM;
    config.xclk_freq_hz = 20000000;
    config.pixel_format = PIXFORMAT_JPEG;
    config.frame_size = FRAMESIZE_SVGA; // 800x600
    config.jpeg_quality = 12;            // 0-63, lower means higher quality
    config.fb_count = 1;

    // Check PSRAM
    if (psramFound()) {
        config.jpeg_quality = 10;
        config.fb_count = 2;
    }

    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
        Serial.printf("[Cam] ERROR: Camera init failed with error 0x%x\n", err);
        cameraInitialized = false;
    } else {
        Serial.println("[Cam] OV2640 camera initialized successfully.");
        cameraInitialized = true;
    }

    // Connect to Wi-Fi
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    Serial.printf("[Cam] Connecting to Wi-Fi '%s' ...\n", WIFI_SSID);

    int timeout = 0;
    while (WiFi.status() != WL_CONNECTED && timeout < 20) {
        delay(500);
        Serial.print(".");
        timeout++;
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.printf("\n[Cam] Wi-Fi connected! IP: %s\n", WiFi.localIP().toString().c_str());
    } else {
        Serial.println("\n[Cam] Wi-Fi connection timed out. Retrying in loop.");
    }

    // Register HTTP endpoints
    server.on("/status", HTTP_GET, handleStatus);
    server.on("/capture", HTTP_GET, handleCapture);
    server.begin();
    Serial.println("[Cam] HTTP server listening on port 80.");
}

void loop() {
    server.handleClient();
    yield();
}
