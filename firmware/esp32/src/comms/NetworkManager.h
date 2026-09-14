#pragma once

#include <Arduino.h>
#include <WiFi.h>
#include "config.h"

class NetworkManager {
public:
    NetworkManager();
    void begin();
    void update(); // Non-blocking reconnection loop

    bool isConnected() const;
    int getRSSI() const;
    String getIP() const;

private:
    unsigned long _lastReconnectAttemptMs;
    unsigned long _reconnectIntervalMs;
    int _consecutiveFailures;

    void attemptConnection();
};
