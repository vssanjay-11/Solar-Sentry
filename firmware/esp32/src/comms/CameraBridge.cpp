#include "CameraBridge.h"
#include <WiFi.h>

CameraBridge::CameraBridge()
    : _cameraIP(CAMERA_DEFAULT_IP),
      _cameraOnline(false),
      _lastPingMs(0) {}

void CameraBridge::begin() {
    Serial.printf("[CameraBridge] Initialized with target IP: %s\n", _cameraIP.c_str());
}

void CameraBridge::update() {
    if (WiFi.status() != WL_CONNECTED) {
        _cameraOnline = false;
        return;
    }

    unsigned long now = millis();
    if (now - _lastPingMs >= INTERVAL_CAM_PING_MS) {
        _lastPingMs = now;
        pingCameraNode();
    }
}

void CameraBridge::pingCameraNode() {
    HTTPClient http;
    String url = "http://" + _cameraIP + "/status";

    http.begin(url);
    http.setTimeout(1500); // 1.5s non-blocking timeout

    int httpCode = http.GET();
    if (httpCode == HTTP_CODE_OK) {
        if (!_cameraOnline) {
            Serial.printf("[CameraBridge] ESP32-CAM node connected and healthy at %s\n", _cameraIP.c_str());
        }
        _cameraOnline = true;
    } else {
        if (_cameraOnline) {
            Serial.printf("[CameraBridge] ESP32-CAM node ping failed (HTTP %d)\n", httpCode);
        }
        _cameraOnline = false;
    }

    http.end();
}
