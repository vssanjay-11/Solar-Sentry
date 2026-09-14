#pragma once

#include <Arduino.h>
#include <Wire.h>
#include <DHT.h>
#include <BH1750.h>
#include <Adafruit_BMP280.h>
#include "config.h"
#include "types.h"

/**
 * ============================================================
 * SENSOR MANAGER
 * Responsible for acquiring and validating all environmental
 * and physical edge telemetry.
 * ============================================================
 */
class SensorManager {
public:
    SensorManager();
    bool begin();
    void update();
    const SensorReadings& getReadings() const { return _readings; }
    void evaluateHealth(SubsystemHealth& health) const;

private:
    DHT _dht;
    BH1750 _lightMeter;
    Adafruit_BMP280 _bmp;

    bool _dhtInitialized;
    bool _bh1750Initialized;
    bool _bmpInitialized;

    SensorReadings _readings;

    int _rainDebounceCounter;

    void readDHT();
    void readBH1750();
    void readBMP280();
    void readRain();
};
