#include "BackendClient.h"
#include <WiFi.h>

BackendClient::BackendClient(ActuatorManager& actuators, SafetyMonitor& safety)
    : _actuators(actuators),
      _safety(safety),
      _backendReachable(false),
      _consecutiveFailures(0) {}

void BackendClient::begin() {
    Serial.printf("[Backend] Client initialized targeting http://%s:%d\n", BACKEND_HOST, BACKEND_PORT);
}

bool BackendClient::sendTelemetry(const SensorReadings& sensors,
                                  const ActuatorState& actuators,
                                  DeviceState state,
                                  int healthScore,
                                  int wifiRssi,
                                  bool camOnline,
                                  const String& camIP) {
    if (WiFi.status() != WL_CONNECTED) {
        _backendReachable = false;
        return false;
    }

    // Build JSON payload adhering to contracts/SensorTelemetry.json
    JsonDocument doc;
    doc["device_id"] = DEVICE_ID;

    // ISO timestamp approximation or uptime if NTP not synced
    char timeBuffer[32];
    snprintf(timeBuffer, sizeof(timeBuffer), "UPTIME_%luS", millis() / 1000);
    doc["timestamp"] = timeBuffer;
    doc["uptime_seconds"] = millis() / 1000;

    doc["temperature"] = serialized(String(sensors.temperature, 2));
    doc["humidity"] = serialized(String(sensors.humidity, 1));
    doc["pressure"] = serialized(String(sensors.pressure, 2));
    doc["lux"] = serialized(String(sensors.lux, 1));
    doc["rain_raw"] = sensors.rain_raw;
    doc["rain_detected"] = sensors.rain_detected;

    doc["pan"] = actuators.current_pan;
    doc["tilt"] = actuators.current_tilt;
    doc["state"] = deviceStateToString(state);
    doc["health"] = healthScore;
    doc["wifi_rssi"] = wifiRssi;

    doc["camera_online"] = camOnline;
    doc["camera_ip"] = camIP;

    JsonObject sensorStatus = doc["sensor_status"].to<JsonObject>();
    sensorStatus["dht22"] = sensors.dht_valid;
    sensorStatus["bh1750"] = sensors.bh1750_valid;
    sensorStatus["bmp280"] = sensors.bmp_valid;
    sensorStatus["rain"] = sensors.rain_valid;

    doc["firmware_version"] = FIRMWARE_VERSION;

    String jsonString;
    serializeJson(doc, jsonString);

    HTTPClient http;
    String endpointUrl = "http://" + String(BACKEND_HOST) + ":" + String(BACKEND_PORT) + String(TELEMETRY_ENDPOINT);
    http.begin(endpointUrl);
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(2000);

    int httpResponseCode = http.POST(jsonString);

    if (httpResponseCode == HTTP_CODE_OK || httpResponseCode == HTTP_CODE_CREATED) {
        _backendReachable = true;
        _consecutiveFailures = 0;
        _safety.notifyBackendActivity();

        // Check if server returned a piggybacked command
        String responseBody = http.getString();
        if (responseBody.length() > 5) {
            CommandResultPayload cmdResult;
            processCommandJson(responseBody, cmdResult);
        }
        http.end();
        return true;
    } else {
        _consecutiveFailures++;
        if (_consecutiveFailures >= 3) {
            _backendReachable = false;
        }
        http.end();
        return false;
    }
}

bool BackendClient::pollCommands() {
    if (WiFi.status() != WL_CONNECTED) return false;

    HTTPClient http;
    String endpointUrl = "http://" + String(BACKEND_HOST) + ":" + String(BACKEND_PORT) +
                         String(COMMAND_POLL_ENDPOINT) + "?device_id=" + String(DEVICE_ID);
    http.begin(endpointUrl);
    http.setTimeout(1500);

    int httpCode = http.GET();
    if (httpCode == HTTP_CODE_OK) {
        String payload = http.getString();
        if (payload.length() > 10) {
            CommandResultPayload result;
            processCommandJson(payload, result);
        }
        _safety.notifyBackendActivity();
        http.end();
        return true;
    }

    http.end();
    return false;
}

bool BackendClient::processCommandJson(const String& jsonPayload, CommandResultPayload& resultOut) {
    JsonDocument doc;
    DeserializationError error = deserializeJson(doc, jsonPayload);
    if (error) {
        Serial.printf("[Command] JSON deserialization failed: %s\n", error.c_str());
        return false;
    }

    CommandPayload cmd;
    memset(&cmd, 0, sizeof(CommandPayload));

    const char* cid = doc["command_id"] | "unknown-id";
    const char* verb = doc["command"] | "";
    strncpy(cmd.command_id, cid, sizeof(cmd.command_id) - 1);
    strncpy(cmd.command, verb, sizeof(cmd.command) - 1);

    cmd.pan = doc["pan"] | -1;
    cmd.tilt = doc["tilt"] | -1;
    cmd.speed = doc["speed"] | 100;
    const char* targetStateStr = doc["target_state"] | "";
    strncpy(cmd.target_state, targetStateStr, sizeof(cmd.target_state) - 1);
    cmd.valid = (strlen(cmd.command) > 0);

    return executeCommand(cmd, resultOut);
}

bool BackendClient::executeCommand(const CommandPayload& cmd, CommandResultPayload& resultOut) {
    strncpy(resultOut.command_id, cmd.command_id, sizeof(resultOut.command_id) - 1);
    const ActuatorState& actState = _actuators.getState();
    DeviceState currentState = _safety.getState();

    Serial.printf("[Command] Executing command: %s (ID: %s)\n", cmd.command, cmd.command_id);

    // 1. SAFETY OVERRIDE VERIFICATION
    if (!_safety.isSafeToObserve() && (strcmp(cmd.command, "OBSERVE") == 0 || strcmp(cmd.command, "SCAN") == 0)) {
        strncpy(resultOut.status, "REJECTED_SAFETY", sizeof(resultOut.status) - 1);
        strncpy(resultOut.message, "Rejected by local safety interlock (Rain or Unsafe condition)", sizeof(resultOut.message) - 1);
        resultOut.current_pan = actState.current_pan;
        resultOut.current_tilt = actState.current_tilt;
        strncpy(resultOut.current_state, deviceStateToString(currentState), sizeof(resultOut.current_state) - 1);
        Serial.println("[Command] REJECTED: Unsafe conditions for observation!");
        return false;
    }

    // 2. PARSE COMMAND VERB
    if (strcmp(cmd.command, "OBSERVE") == 0) {
        _safety.requestStateChange(DeviceState::OBSERVE);
        if (cmd.pan >= 0 && cmd.tilt >= 0) {
            _actuators.setTargetAngles(cmd.pan, cmd.tilt, cmd.speed);
        }
        strncpy(resultOut.status, "SUCCESS", sizeof(resultOut.status) - 1);
        strncpy(resultOut.message, "Entered OBSERVE mode", sizeof(resultOut.message) - 1);
    } else if (strcmp(cmd.command, "PARK") == 0 || strcmp(cmd.command, "SAFE") == 0) {
        _safety.requestStateChange(DeviceState::STANDBY);
        _actuators.parkToSafePosition();
        strncpy(resultOut.status, "SUCCESS", sizeof(resultOut.status) - 1);
        strncpy(resultOut.message, "Parked at safe position", sizeof(resultOut.message) - 1);
    } else if (strcmp(cmd.command, "SCAN") == 0) {
        _safety.requestStateChange(DeviceState::SCAN);
        if (cmd.pan >= 0 && cmd.tilt >= 0) {
            _actuators.setTargetAngles(cmd.pan, cmd.tilt, cmd.speed);
        }
        strncpy(resultOut.status, "SUCCESS", sizeof(resultOut.status) - 1);
        strncpy(resultOut.message, "Executing scan angle", sizeof(resultOut.message) - 1);
    } else if (strcmp(cmd.command, "SET_SERVO") == 0) {
        if (cmd.pan >= 0 && cmd.tilt >= 0) {
            bool ok = _actuators.setTargetAngles(cmd.pan, cmd.tilt, cmd.speed);
            if (ok) {
                strncpy(resultOut.status, "SUCCESS", sizeof(resultOut.status) - 1);
                strncpy(resultOut.message, "Servo angles updated", sizeof(resultOut.message) - 1);
            } else {
                strncpy(resultOut.status, "INVALID_PARAMS", sizeof(resultOut.status) - 1);
                strncpy(resultOut.message, "Angle coordinates out of bounds", sizeof(resultOut.message) - 1);
            }
        }
    } else if (strcmp(cmd.command, "SET_STATE") == 0) {
        DeviceState reqState = stringToDeviceState(cmd.target_state);
        _safety.requestStateChange(reqState);
        strncpy(resultOut.status, "SUCCESS", sizeof(resultOut.status) - 1);
        strncpy(resultOut.message, "State transition processed", sizeof(resultOut.message) - 1);
    } else if (strcmp(cmd.command, "EMERGENCY_STOP") == 0) {
        _safety.requestStateChange(DeviceState::SAFE);
        _actuators.parkToSafePosition();
        strncpy(resultOut.status, "SUCCESS", sizeof(resultOut.status) - 1);
        strncpy(resultOut.message, "Emergency stop triggered", sizeof(resultOut.message) - 1);
    } else if (strcmp(cmd.command, "REBOOT") == 0) {
        Serial.println("[Command] Reboot command received! Restarting ESP32 in 1 second...");
        strncpy(resultOut.status, "SUCCESS", sizeof(resultOut.status) - 1);
        strncpy(resultOut.message, "Rebooting system", sizeof(resultOut.message) - 1);
        delay(1000);
        ESP.restart();
    } else {
        strncpy(resultOut.status, "INVALID_PARAMS", sizeof(resultOut.status) - 1);
        strncpy(resultOut.message, "Unrecognized command verb", sizeof(resultOut.message) - 1);
    }

    const ActuatorState& endState = _actuators.getState();
    resultOut.current_pan = endState.current_pan;
    resultOut.current_tilt = endState.current_tilt;
    strncpy(resultOut.current_state, deviceStateToString(_safety.getState()), sizeof(resultOut.current_state) - 1);

    return true;
}
