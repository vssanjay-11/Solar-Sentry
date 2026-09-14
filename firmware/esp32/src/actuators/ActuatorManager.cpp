#include "ActuatorManager.h"

ActuatorManager::ActuatorManager()
    : _currentPanFloat(PAN_SAFE_DEG),
      _currentTiltFloat(TILT_SAFE_DEG),
      _stepPan(1.0f),
      _stepTilt(1.0f),
      _lastServoStepMs(0),
      _greenMode(LedMode::OFF),
      _yellowMode(LedMode::OFF),
      _redMode(LedMode::OFF),
      _lastLedUpdateMs(0),
      _blinkSlowState(false),
      _blinkFastState(false),
      _lastBlinkSlowMs(0),
      _lastBlinkFastMs(0) {
    _state.current_pan = PAN_SAFE_DEG;
    _state.current_tilt = TILT_SAFE_DEG;
    _state.target_pan = PAN_SAFE_DEG;
    _state.target_tilt = TILT_SAFE_DEG;
    _state.moving = false;
}

bool ActuatorManager::begin() {
    Serial.println("[Actuators] Initializing LED GPIOs...");
    pinMode(PIN_LED_GREEN, OUTPUT);
    pinMode(PIN_LED_YELLOW, OUTPUT);
    pinMode(PIN_LED_RED, OUTPUT);

    // Initial LED check sequence
    digitalWrite(PIN_LED_GREEN, HIGH);
    digitalWrite(PIN_LED_YELLOW, HIGH);
    digitalWrite(PIN_LED_RED, HIGH);
    delay(200);
    digitalWrite(PIN_LED_GREEN, LOW);
    digitalWrite(PIN_LED_YELLOW, LOW);
    digitalWrite(PIN_LED_RED, LOW);

    Serial.println("[Actuators] Initializing Servos on GPIO18 (Pan) and GPIO19 (Tilt)...");
    // Standard 50Hz PWM for hobby servos
    ESP32PWM::allocateTimer(0);
    ESP32PWM::allocateTimer(1);

    _servoPan.setPeriodHertz(50);
    _servoTilt.setPeriodHertz(50);

    // Standard min/max pulse widths: 500us to 2400us
    _servoPan.attach(PIN_SERVO_PAN, 500, 2400);
    _servoTilt.attach(PIN_SERVO_TILT, 500, 2400);

    // Command safe park position immediately
    parkToSafePosition();

    return true;
}

bool ActuatorManager::setTargetAngles(int pan, int tilt, int speedPercent) {
    // Enforce physical bounds
    if (pan < PAN_MIN_DEG || pan > PAN_MAX_DEG || tilt < TILT_MIN_DEG || tilt > TILT_MAX_DEG) {
        Serial.printf("[Actuators] ERROR: Requested angles out of bounds (Pan: %d, Tilt: %d)\n", pan, tilt);
        return false;
    }

    _state.target_pan = pan;
    _state.target_tilt = tilt;

    speedPercent = constrain(speedPercent, 10, 100);
    float speedMultiplier = (float)speedPercent / 100.0f;
    _stepPan = max(0.5f, 2.0f * speedMultiplier);
    _stepTilt = max(0.5f, 2.0f * speedMultiplier);

    _state.moving = true;
    Serial.printf("[Actuators] Slew initiated -> Target Pan: %d°, Tilt: %d°\n", pan, tilt);
    return true;
}

void ActuatorManager::parkToSafePosition() {
    Serial.println("[Actuators] Commanding Park / Stow Safe Position (Pan: 90°, Tilt: 0°)");
    setTargetAngles(PAN_SAFE_DEG, TILT_SAFE_DEG, 100);
}

void ActuatorManager::update() {
    unsigned long now = millis();

    // Smooth servo step update
    if (now - _lastServoStepMs >= SERVO_STEP_INTERVAL_MS) {
        _lastServoStepMs = now;
        updateServos();
    }

    // Non-blocking LED update
    if (now - _lastLedUpdateMs >= INTERVAL_LED_UPDATE_MS) {
        _lastLedUpdateMs = now;
        updateLeds();
    }
}

void ActuatorManager::updateServos() {
    bool panMoving = false;
    bool tiltMoving = false;

    // Incremental pan slew
    if (abs(_currentPanFloat - _state.target_pan) > 0.5f) {
        if (_currentPanFloat < _state.target_pan) {
            _currentPanFloat = min(_currentPanFloat + _stepPan, (float)_state.target_pan);
        } else {
            _currentPanFloat = max(_currentPanFloat - _stepPan, (float)_state.target_pan);
        }
        _servoPan.write((int)round(_currentPanFloat));
        panMoving = true;
    } else {
        _currentPanFloat = _state.target_pan;
    }

    // Incremental tilt slew
    if (abs(_currentTiltFloat - _state.target_tilt) > 0.5f) {
        if (_currentTiltFloat < _state.target_tilt) {
            _currentTiltFloat = min(_currentTiltFloat + _stepTilt, (float)_state.target_tilt);
        } else {
            _currentTiltFloat = max(_currentTiltFloat - _stepTilt, (float)_state.target_tilt);
        }
        _servoTilt.write((int)round(_currentTiltFloat));
        tiltMoving = true;
    } else {
        _currentTiltFloat = _state.target_tilt;
    }

    _state.current_pan = (int)round(_currentPanFloat);
    _state.current_tilt = (int)round(_currentTiltFloat);
    _state.moving = (panMoving || tiltMoving);
}

void ActuatorManager::setLedModes(LedMode green, LedMode yellow, LedMode red) {
    _greenMode = green;
    _yellowMode = yellow;
    _redMode = red;
}

void ActuatorManager::syncWithState(DeviceState state) {
    switch (state) {
        case DeviceState::BOOT:
        case DeviceState::SELF_CHECK:
            setLedModes(LedMode::OFF, LedMode::BLINK_FAST, LedMode::OFF);
            break;
        case DeviceState::STANDBY:
            setLedModes(LedMode::BLINK_SLOW, LedMode::OFF, LedMode::OFF);
            break;
        case DeviceState::OBSERVE:
            setLedModes(LedMode::SOLID, LedMode::OFF, LedMode::OFF);
            break;
        case DeviceState::WAIT:
            setLedModes(LedMode::OFF, LedMode::SOLID, LedMode::OFF);
            break;
        case DeviceState::SCAN:
            setLedModes(LedMode::BLINK_FAST, LedMode::BLINK_FAST, LedMode::OFF);
            break;
        case DeviceState::SUSPEND:
            setLedModes(LedMode::OFF, LedMode::OFF, LedMode::SOLID);
            break;
        case DeviceState::FAULT:
            setLedModes(LedMode::OFF, LedMode::OFF, LedMode::BLINK_FAST);
            break;
        case DeviceState::SAFE:
            setLedModes(LedMode::OFF, LedMode::OFF, LedMode::BLINK_SLOW);
            break;
        case DeviceState::DEGRADED:
            setLedModes(LedMode::OFF, LedMode::BLINK_FAST, LedMode::OFF);
            break;
        default:
            setLedModes(LedMode::OFF, LedMode::OFF, LedMode::OFF);
            break;
    }
}

void ActuatorManager::updateLeds() {
    unsigned long now = millis();

    // 1 Hz slow blink (500ms toggle)
    if (now - _lastBlinkSlowMs >= 500) {
        _lastBlinkSlowMs = now;
        _blinkSlowState = !_blinkSlowState;
    }

    // 5 Hz fast blink (100ms toggle)
    if (now - _lastBlinkFastMs >= 100) {
        _lastBlinkFastMs = now;
        _blinkFastState = !_blinkFastState;
    }

    applyLedPin(PIN_LED_GREEN, _greenMode, _blinkSlowState, _blinkFastState);
    applyLedPin(PIN_LED_YELLOW, _yellowMode, _blinkSlowState, _blinkFastState);
    applyLedPin(PIN_LED_RED, _redMode, _blinkSlowState, _blinkFastState);
}

void ActuatorManager::applyLedPin(int pin, LedMode mode, bool slowState, bool fastState) {
    switch (mode) {
        case LedMode::OFF:
            digitalWrite(pin, LOW);
            break;
        case LedMode::SOLID:
            digitalWrite(pin, HIGH);
            break;
        case LedMode::BLINK_SLOW:
            digitalWrite(pin, slowState ? HIGH : LOW);
            break;
        case LedMode::BLINK_FAST:
            digitalWrite(pin, fastState ? HIGH : LOW);
            break;
        case LedMode::STROBE:
            digitalWrite(pin, fastState ? HIGH : LOW);
            break;
    }
}

void ActuatorManager::evaluateHealth(SubsystemHealth& health) const {
    health.pan_servo_ok = _servoPan.attached();
    health.tilt_servo_ok = _servoTilt.attached();

    if (!health.pan_servo_ok) health.overall_score = max(0, health.overall_score - 15);
    if (!health.tilt_servo_ok) health.overall_score = max(0, health.overall_score - 15);
}
