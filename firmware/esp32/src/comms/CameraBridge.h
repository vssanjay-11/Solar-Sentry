#pragma once

#include <Arduino.h>
#include <HTTPClient.h>
#include "config.h"

class CameraBridge {
public:
    CameraBridge();
    void begin();
    void update(); // Periodic health ping to camera node

    bool isCameraOnline() const { return _cameraOnline; }
    String getCameraIP() const { return _cameraIP; }
    void setCameraIP(const String& ip) { _cameraIP = ip; }

private:
    String _cameraIP;
    bool _cameraOnline;
    unsigned long _lastPingMs;

    void pingCameraNode();
};
