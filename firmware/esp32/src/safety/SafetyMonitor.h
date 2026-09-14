#pragma once

#include <Arduino.h>
#include "config.h"
#include "types.h"
#include "sensors/SensorManager.h"
#include "actuators/ActuatorManager.h"

class SafetyMonitor {
public:
    SafetyMonitor(ActuatorManager& actuators);
    void begin();
    void update(const SensorReadings& sensors, bool backendReachable);

    DeviceState getState() const { return _currentState; }
    void requestStateChange(DeviceState newState);

    const SubsystemHealth& getHealth() const { return _health; }
    void notifyBackendActivity();

    bool isSafeToObserve() const;

private:
    ActuatorManager& _actuators;
    DeviceState _currentState;
    DeviceState _previousState;
    SubsystemHealth _health;

    unsigned long _lastBackendContactMs;
    bool _rainInterlockActive;

    void evaluateSafetyRules(const SensorReadings& sensors, bool backendReachable);
    void computeHealthScore(const SensorReadings& sensors, bool backendReachable);
};
