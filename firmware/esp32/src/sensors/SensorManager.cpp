#include "SensorManager.h"

SensorManager::SensorManager()
    : _dht(PIN_DHT, DHT22),
      _dhtInitialized(false),
      _bh1750Initialized(false),
      _bmpInitialized(false),
      _rainDebounceCounter(0) {
    memset(&_readings, 0, sizeof(SensorReadings));
}

bool SensorManager::begin() {
    Serial.println("[Sensors] Initializing I2C bus on GPIO21 (SDA) and GPIO22 (SCL)...");
    Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL, (uint32_t)I2C_CLOCK_SPEED);

    // 1. Initialize DHT22
    Serial.println("[Sensors] Initializing DHT22 on GPIO4...");
    _dht.begin();
    _dhtInitialized = true;

    // 2. Initialize BH1750
    Serial.printf("[Sensors] Probing BH1750 at 0x%02X...\n", ADDR_BH1750);
    if (_lightMeter.begin(BH1750::CONTINUOUS_HIGH_RES_MODE, ADDR_BH1750, &Wire)) {
        Serial.println("[Sensors] BH1750 initialized successfully.");
        _bh1750Initialized = true;
    } else {
        Serial.println("[Sensors] WARNING: BH1750 initialization failed!");
        _bh1750Initialized = false;
    }

    // 3. Initialize BMP280
    Serial.printf("[Sensors] Probing BMP280 at 0x%02X...\n", ADDR_BMP280);
    if (_bmp.begin(ADDR_BMP280)) {
        Serial.println("[Sensors] BMP280 initialized successfully.");
        _bmpInitialized = true;
        // Default sampling parameters for weather monitoring
        _bmp.setSampling(Adafruit_BMP280::MODE_NORMAL,
                         Adafruit_BMP280::SAMPLING_X2,
                         Adafruit_BMP280::SAMPLING_X16,
                         Adafruit_BMP280::FILTER_X16,
                         Adafruit_BMP280::STANDBY_MS_500);
    } else {
        Serial.println("[Sensors] WARNING: BMP280 initialization failed on primary address, trying 0x77...");
        if (_bmp.begin(0x77)) {
            Serial.println("[Sensors] BMP280 initialized on 0x77.");
            _bmpInitialized = true;
        } else {
            Serial.println("[Sensors] WARNING: BMP280 initialization failed completely!");
            _bmpInitialized = false;
        }
    }

    // 4. Configure Rain sensor analog pin
    pinMode(PIN_RAIN_ANALOG, INPUT);
    analogSetPinAttenuation(PIN_RAIN_ANALOG, ADC_11db); // 0 - 3.3V full range

    update();
    return true;
}

void SensorManager::update() {
    _readings.timestamp_ms = millis();
    readDHT();
    readBMP280();
    readBH1750();
    readRain();
}

void SensorManager::readDHT() {
    float t = _dht.readTemperature();
    float h = _dht.readHumidity();

    if (isnan(t) || isnan(h) ||
        t < TEMP_MIN_PLAUSIBLE_C || t > TEMP_MAX_PLAUSIBLE_C ||
        h < HUMID_MIN_PLAUSIBLE || h > HUMID_MAX_PLAUSIBLE) {
        _readings.dht_valid = false;
    } else {
        _readings.temperature = t;
        _readings.humidity = h;
        _readings.dht_valid = true;
    }
}

void SensorManager::readBMP280() {
    if (!_bmpInitialized) {
        _readings.bmp_valid = false;
        return;
    }

    float p = _bmp.readPressure() / 100.0f; // Pa to hPa
    float t = _bmp.readTemperature();

    if (isnan(p) || p < PRESS_MIN_PLAUSIBLE || p > PRESS_MAX_PLAUSIBLE) {
        _readings.bmp_valid = false;
    } else {
        _readings.pressure = p;
        _readings.bmp_valid = true;

        // If DHT temperature failed, fallback to BMP280 temperature
        if (!_readings.dht_valid && !isnan(t) && t >= TEMP_MIN_PLAUSIBLE_C && t <= TEMP_MAX_PLAUSIBLE_C) {
            _readings.temperature = t;
        }
    }
}

void SensorManager::readBH1750() {
    if (!_bh1750Initialized) {
        _readings.bh1750_valid = false;
        return;
    }

    float lux = _lightMeter.readLightLevel();
    if (lux < LUX_MIN_PLAUSIBLE || lux > LUX_MAX_PLAUSIBLE || lux < 0) {
        _readings.bh1750_valid = false;
    } else {
        _readings.lux = lux;
        _readings.bh1750_valid = true;
    }
}

void SensorManager::readRain() {
    // 12-bit ADC reading (0 - 4095)
    int raw = analogRead(PIN_RAIN_ANALOG);
    _readings.rain_raw = raw;
    _readings.rain_valid = (raw >= 0 && raw <= 4095);

    // Active-low moisture threshold debounce
    if (raw < RAIN_THRESHOLD_ADC) {
        _rainDebounceCounter++;
        if (_rainDebounceCounter >= RAIN_DEBOUNCE_SAMPLES) {
            _readings.rain_detected = true;
            _rainDebounceCounter = RAIN_DEBOUNCE_SAMPLES;
        }
    } else {
        if (_rainDebounceCounter > 0) {
            _rainDebounceCounter--;
        }
        if (_rainDebounceCounter == 0) {
            _readings.rain_detected = false;
        }
    }
}

void SensorManager::evaluateHealth(SubsystemHealth& health) const {
    health.dht_ok = _readings.dht_valid;
    health.bmp280_ok = _readings.bmp_valid;
    health.bh1750_ok = _readings.bh1750_valid;
    health.rain_ok = _readings.rain_valid;

    int validCount = 0;
    if (health.dht_ok) validCount++;
    if (health.bmp280_ok) validCount++;
    if (health.bh1750_ok) validCount++;
    if (health.rain_ok) validCount++;

    // Sensor contribution to health score (up to 40 points)
    // Other points contributed by comms and actuators
    int sensorScore = (validCount * 10);
    health.overall_score = constrain(health.overall_score - (40 - sensorScore), 0, 100);
}
