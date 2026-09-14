#pragma once

#include <Arduino.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include "config.h"
#include "types.h"
#include "actuators/ActuatorManager.h"
#include "safety/SafetyMonitor.h"

class BackendClient {
public:
    BackendClient(ActuatorManager& actuators, SafetyMonitor& safety);
    void begin();

    // Outbound Telemetry
    bool sendTelemetry(const SensorReadings& sensors,
                       const ActuatorState& actuators,
                       DeviceState state,
                       int healthScore,
                       int wifiRssi,
                       bool camOnline,
                       const String& camIP);

    // Inbound Command Processing
    bool pollCommands();
    bool processCommandJson(const String& jsonPayload, CommandResultPayload& resultOut);

    bool isBackendReachable() const { return _backendReachable; }

private:
    ActuatorManager& _actuators;
    SafetyMonitor& _safety;
    bool _backendReachable;
    int _consecutiveFailures;

    bool executeCommand(const CommandPayload& cmd, CommandResultPayload& resultOut);
};
