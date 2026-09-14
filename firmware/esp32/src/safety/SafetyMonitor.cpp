#include "SafetyMonitor.h"

SafetyMonitor::SafetyMonitor(ActuatorManager& actuators)
    : _actuators(actuators),
      _currentState(DeviceState::BOOT),
      _previousState(DeviceState::BOOT),
      _lastBackendContactMs(0),
      _rainInterlockActive(false) {
    memset(&_health, 0, sizeof(SubsystemHealth));
    _health.overall_score = 100;
}

void SafetyMonitor::begin() {
    _lastBackendContactMs = millis();
    requestStateChange(DeviceState::SELF_CHECK);
}

void SafetyMonitor::notifyBackendActivity() {
    _lastBackendContactMs = millis();
}

void SafetyMonitor::requestStateChange(DeviceState newState) {
    if (_currentState == newState) return;

    // Strict safety locks: Cannot exit SUSPEND while rain is detected
    if (_rainInterlockActive && newState != DeviceState::SUSPEND && newState != DeviceState::SAFE && newState != DeviceState::FAULT) {
        Serial.println("[Safety] State change REJECTED: Rain interlock active!");
        return;
    }

    _previousState = _currentState;
    _currentState = newState;
    Serial.printf("[Safety] State transition: %s -> %s\n",
                  deviceStateToString(_previousState),
                  deviceStateToString(_currentState));

    // Handle actuator poses and LED modes on state transition
    _actuators.syncWithState(_currentState);

    if (_currentState == DeviceState::SUSPEND ||
        _currentState == DeviceState::SAFE ||
        _currentState == DeviceState::FAULT) {
        _actuators.parkToSafePosition();
    }
}

void SafetyMonitor::update(const SensorReadings& sensors, bool backendReachable) {
    evaluateSafetyRules(sensors, backendReachable);
    computeHealthScore(sensors, backendReachable);
    _actuators.syncWithState(_currentState);
}

void SafetyMonitor::evaluateSafetyRules(const SensorReadings& sensors, bool backendReachable) {
    unsigned long now = millis();

    // 1. RAIN SAFETY INTERLOCK (Highest Local Hardware Priority)
    if (sensors.rain_detected) {
        if (!_rainInterlockActive) {
            Serial.println("[Safety] EMERGENCY OVERRIDE: Rain detected! Suspending operations.");
            _rainInterlockActive = true;
        }
        if (_currentState != DeviceState::SUSPEND && _currentState != DeviceState::FAULT) {
            requestStateChange(DeviceState::SUSPEND);
        }
        return;
    } else {
        if (_rainInterlockActive) {
            Serial.println("[Safety] Rain cleared. Ready for state recovery.");
            _rainInterlockActive = false;
            if (_currentState == DeviceState::SUSPEND) {
                requestStateChange(DeviceState::STANDBY);
            }
        }
    }

    // 2. THERMAL OVERHEAT PROTECTION
    if (sensors.temperature > OVERHEAT_SHUTDOWN_C) {
        Serial.printf("[Safety] THERMAL ALERT: Temperature %.1f°C exceeds threshold %.1f°C\n",
                      sensors.temperature, OVERHEAT_SHUTDOWN_C);
        requestStateChange(DeviceState::SAFE);
        return;
    }

    // 3. COMMUNICATION LOSS FAIL-SAFE
    if ((now - _lastBackendContactMs > COMMS_TIMEOUT_MS) &&
        (_currentState == DeviceState::OBSERVE || _currentState == DeviceState::SCAN)) {
        Serial.println("[Safety] WARNING: Central backend communication timeout. Entering SAFE state.");
        requestStateChange(DeviceState::SAFE);
        return;
    }

    // 4. SENSOR FAULT DEGRADATION
    bool criticalSensorsFailed = (!sensors.dht_valid && !sensors.bmp_valid);
    if (criticalSensorsFailed && _currentState == DeviceState::OBSERVE) {
        Serial.println("[Safety] Critical environmental sensing lost. Entering DEGRADED mode.");
        requestStateChange(DeviceState::DEGRADED);
    }
}

void SafetyMonitor::computeHealthScore(const SensorReadings& sensors, bool backendReachable) {
    int score = 0;

    // Environmental sensors health (40 points)
    if (sensors.dht_valid) score += 10;
    if (sensors.bmp_valid) score += 10;
    if (sensors.bh1750_valid) score += 10;
    if (sensors.rain_valid) score += 10;

    // Actuators health (30 points)
    const ActuatorState& act = _actuators.getState();
    if (act.current_pan >= 0 && act.current_pan <= 180) score += 15;
    if (act.current_tilt >= 0 && act.current_tilt <= 180) score += 15;

    // Communication health (20 points)
    if (backendReachable) score += 20;

    // Operational safety status (10 points)
    if (!_rainInterlockActive && sensors.temperature < OVERHEAT_SHUTDOWN_C) score += 10;

    _health.overall_score = constrain(score, 0, 100);
    _health.backend_reachable = backendReachable;
}

bool SafetyMonitor::isSafeToObserve() const {
    return (_currentState == DeviceState::STANDBY ||
            _currentState == DeviceState::OBSERVE ||
            _currentState == DeviceState::SCAN) &&
           !_rainInterlockActive;
}
