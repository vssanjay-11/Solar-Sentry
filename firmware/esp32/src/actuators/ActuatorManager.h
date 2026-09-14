#pragma once

#include <Arduino.h>
#include <ESP32Servo.h>
#include "config.h"
#include "types.h"

enum class LedMode {
    OFF,
    SOLID,
    BLINK_SLOW,   // ~1 Hz (500ms on, 500ms off)
    BLINK_FAST,   // ~5 Hz (100ms on, 100ms off)
    STROBE        // Quick pulse
};

class ActuatorManager {
public:
    ActuatorManager();
    bool begin();
    void update(); // Called regularly for smooth servo stepping and LED animations

    // Servo commands
    bool setTargetAngles(int pan, int tilt, int speedPercent = 100);
    void parkToSafePosition();
    const ActuatorState& getState() const { return _state; }

    // LED indicators
    void setLedModes(LedMode green, LedMode yellow, LedMode red);
    void syncWithState(DeviceState state);

    void evaluateHealth(SubsystemHealth& health) const;

private:
    Servo _servoPan;
    Servo _servoTilt;

    ActuatorState _state;

    float _currentPanFloat;
    float _currentTiltFloat;
    float _stepPan;
    float _stepTilt;

    unsigned long _lastServoStepMs;

    // LED state tracking
    LedMode _greenMode;
    LedMode _yellowMode;
    LedMode _redMode;

    unsigned long _lastLedUpdateMs;
    bool _blinkSlowState;
    bool _blinkFastState;
    unsigned long _lastBlinkSlowMs;
    unsigned long _lastBlinkFastMs;

    void updateServos();
    void updateLeds();
    void applyLedPin(int pin, LedMode mode, bool slowState, bool fastState);
};
