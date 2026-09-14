#include "NetworkManager.h"

NetworkManager::NetworkManager()
    : _lastReconnectAttemptMs(0),
      _reconnectIntervalMs(3000),
      _consecutiveFailures(0) {}

void NetworkManager::begin() {
    Serial.println("[Network] Initializing Wi-Fi station mode...");
    WiFi.mode(WIFI_STA);
    WiFi.setAutoReconnect(true);
    attemptConnection();
}

void NetworkManager::attemptConnection() {
    Serial.printf("[Network] Connecting to Wi-Fi SSID: %s ...\n", WIFI_SSID);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    _lastReconnectAttemptMs = millis();
}

void NetworkManager::update() {
    if (WiFi.status() == WL_CONNECTED) {
        if (_consecutiveFailures > 0) {
            Serial.printf("[Network] Wi-Fi connected! IP Address: %s, RSSI: %d dBm\n",
                          WiFi.localIP().toString().c_str(), WiFi.RSSI());
            _consecutiveFailures = 0;
            _reconnectIntervalMs = 3000;
        }
        return;
    }

    unsigned long now = millis();
    if (now - _lastReconnectAttemptMs >= _reconnectIntervalMs) {
        _consecutiveFailures++;
        Serial.printf("[Network] Wi-Fi disconnected. Reconnect attempt #%d...\n", _consecutiveFailures);

        // Exponential backoff up to 30 seconds
        _reconnectIntervalMs = min((unsigned long)30000, 3000UL * (1UL << min(_consecutiveFailures, 4)));
        attemptConnection();
    }
}

bool NetworkManager::isConnected() const {
    return WiFi.status() == WL_CONNECTED;
}

int NetworkManager::getRSSI() const {
    return isConnected() ? WiFi.RSSI() : 0;
}

String NetworkManager::getIP() const {
    return isConnected() ? WiFi.localIP().toString() : "0.0.0.0";
}
