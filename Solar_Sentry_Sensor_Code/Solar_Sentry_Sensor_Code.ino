/*
   ================================================================
                    SOLAR-SENTRY
   Autonomous Cognitive Solar Observatory
   ---------------------------------------------------------------
   ESP32 EDGE OBSERVATORY CONTROLLER

   Hardware:
   - ESP32 DevKit
   - DHT22
   - BH1750
   - BMP280
   - Rain Sensor
   - Pan Servo
   - Tilt Servo
   - Green / Yellow / Red LEDs

   Architecture:

   Sensors
      |
      v
   Edge Processing
      |
      +--> Sensor Health
      |
      +--> Sensor Confidence
      |
      +--> Local Observation Readiness
      |
      v
   Wi-Fi / HTTP
      |
      v
   AI Backend
      |
      +--> Vision AI
      +--> Solar AI
      +--> Predictive AI
      +--> Mission Planner
      +--> Digital Twin
      |
      v
   AI Command
      |
      v
   ESP32
      |
      +--> Servo
      +--> LEDs
      +--> Observation State

   ================================================================
*/

#include <Arduino.h>
#include <Wire.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <DHT.h>
#include <BH1750.h>
#include <Adafruit_BMP280.h>
#include <ESP32Servo.h>

// ================================================================
// 1. USER CONFIGURATION
// ================================================================

// ---------- Wi-Fi ----------
const char* WIFI_SSID     = "Rea";
const char* WIFI_PASSWORD = "vssanjay11";

// ---------- AI Backend ----------
// Example:
// http://192.168.1.100:8000/api/telemetry
//
// Replace this with your laptop/Raspberry Pi backend IP.
const char* TELEMETRY_URL =
    "http://192.168.1.100:8000/api/telemetry";

// Backend command endpoint
const char* COMMAND_URL =
    "http://192.168.1.100:8000/api/command";

// ---------- Device ----------
const char* DEVICE_ID = "SOLAR-SENTRY-EDGE-01";

// ================================================================
// 2. PIN DEFINITIONS
// ================================================================

// DHT22
#define DHT_PIN 4
#define DHT_TYPE DHT22

// I2C
#define SDA_PIN 21
#define SCL_PIN 22

// Rain sensor
#define RAIN_PIN 34

// Servos
#define PAN_SERVO_PIN 18
#define TILT_SERVO_PIN 19

// LEDs
#define GREEN_LED 25
#define YELLOW_LED 26
#define RED_LED 27

// ================================================================
// 3. OBJECTS
// ================================================================

DHT dht(DHT_PIN, DHT_TYPE);

BH1750 lightMeter;

Adafruit_BMP280 bmp;

Servo panServo;
Servo tiltServo;

// ================================================================
// 4. SYSTEM ENUMS
// ================================================================

enum ObservationState
{
  STATE_BOOT,
  STATE_SELF_CHECK,
  STATE_STANDBY,
  STATE_OBSERVE,
  STATE_WAIT,
  STATE_SUSPEND,
  STATE_FAULT,
  STATE_SAFE
};

ObservationState currentState = STATE_BOOT;

// ================================================================
// 5. SENSOR DATA STRUCTURE
// ================================================================

struct SensorData
{
  float temperature = NAN;
  float humidity = NAN;

  float pressure = NAN;
  float bmpTemperature = NAN;

  float lux = NAN;

  int rainRaw = 0;

  bool dhtOK = false;
  bool bmpOK = false;
  bool bh1750OK = false;
  bool rainOK = false;

  float dhtConfidence = 0;
  float bmpConfidence = 0;
  float bh1750Confidence = 0;
  float rainConfidence = 0;

  float overallHealth = 0;
};

SensorData sensors;

// ================================================================
// 6. SYSTEM VARIABLES
// ================================================================

unsigned long bootTime = 0;

unsigned long lastSensorRead = 0;
unsigned long lastTelemetry = 0;
unsigned long lastCommandPoll = 0;
unsigned long lastSerialReport = 0;
unsigned long lastWiFiCheck = 0;

const unsigned long SENSOR_INTERVAL = 2000;
const unsigned long TELEMETRY_INTERVAL = 5000;
const unsigned long COMMAND_INTERVAL = 3000;
const unsigned long SERIAL_INTERVAL = 3000;
const unsigned long WIFI_CHECK_INTERVAL = 10000;

// ================================================================
// 7. OBSERVATION VARIABLES
// ================================================================

float environmentScore = 0;
float sensorHealthScore = 0;
float localReadinessScore = 0;

float visionScore = 100;       // supplied by AI backend
float solarDataScore = 100;    // supplied by AI backend
float predictedScore = 100;    // supplied by AI backend

float observationConfidence = 0;

bool backendAvailable = false;

String aiDecision = "LOCAL_FALLBACK";

// ================================================================
// 8. SERVO LIMITS
// ================================================================

const int PAN_MIN = 20;
const int PAN_MAX = 160;

const int TILT_MIN = 30;
const int TILT_MAX = 150;

int panPosition = 90;
int tiltPosition = 90;

// ================================================================
// 9. RAIN THRESHOLD
// ================================================================
//
// IMPORTANT:
// Calibrate this value experimentally.
//
// First check your Serial Monitor while:
// DRY -> note value
// WET -> note value
//
// Change this threshold accordingly.
//
const int RAIN_THRESHOLD = 1500;

// ================================================================
// 10. FUNCTION DECLARATIONS
// ================================================================

void connectWiFi();

void readAllSensors();

void calculateSensorHealth();

void calculateEnvironmentScore();

void calculateLocalReadiness();

void updateObservationState();

void updateLEDs();

void printSystemReport();

void sendTelemetry();

void pollAICommand();

void executeAICommand(String command);

void movePan(int angle);

void moveTilt(int angle);

void performActiveScan();

void safePosition();

String stateToString();

bool validateDHT();

bool validateBMP();

bool validateBH1750();

bool validateRain();

void selfCheck();

float clampScore(float value);

// ================================================================
// SETUP
// ================================================================

void setup()
{
  Serial.begin(115200);

  delay(1000);

  bootTime = millis();

  Serial.println();
  Serial.println();
  Serial.println("================================================");
  Serial.println("             SOLAR-SENTRY   ");
  Serial.println(" AUTONOMOUS COGNITIVE SOLAR OBSERVATORY");
  Serial.println("          EDGE CONTROLLER v1.0");
  Serial.println("================================================");
  Serial.println();

  // ------------------------------------------------
  // GPIO
  // ------------------------------------------------

  pinMode(GREEN_LED, OUTPUT);
  pinMode(YELLOW_LED, OUTPUT);
  pinMode(RED_LED, OUTPUT);

  pinMode(RAIN_PIN, INPUT);

  digitalWrite(GREEN_LED, LOW);
  digitalWrite(YELLOW_LED, LOW);
  digitalWrite(RED_LED, LOW);

  // ------------------------------------------------
  // I2C
  // ------------------------------------------------

  Wire.begin(SDA_PIN, SCL_PIN);

  Serial.println("[SYSTEM] I2C initialized.");

  // ------------------------------------------------
  // DHT22
  // ------------------------------------------------

  dht.begin();

  Serial.println("[SYSTEM] DHT22 initialized.");

  // ------------------------------------------------
  // BH1750
  // ------------------------------------------------

  if (lightMeter.begin(BH1750::CONTINUOUS_HIGH_RES_MODE))
  {
    sensors.bh1750OK = true;
    Serial.println("[OK] BH1750 detected.");
  }
  else
  {
    sensors.bh1750OK = false;
    Serial.println("[ERROR] BH1750 not detected.");
  }

  // ------------------------------------------------
  // BMP280
  // ------------------------------------------------

  if (bmp.begin(0x76))
  {
    sensors.bmpOK = true;
    Serial.println("[OK] BMP280 detected at 0x76.");
  }
  else if (bmp.begin(0x77))
  {
    sensors.bmpOK = true;
    Serial.println("[OK] BMP280 detected at 0x77.");
  }
  else
  {
    sensors.bmpOK = false;
    Serial.println("[ERROR] BMP280 not detected.");
  }

  // ------------------------------------------------
  // Servo
  // ------------------------------------------------

  panServo.attach(PAN_SERVO_PIN);
  tiltServo.attach(TILT_SERVO_PIN);

  panServo.write(panPosition);
  tiltServo.write(tiltPosition);

  Serial.println("[OK] Pan servo initialized.");
  Serial.println("[OK] Tilt servo initialized.");

  // ------------------------------------------------
  // Wi-Fi
  // ------------------------------------------------

  connectWiFi();

  // ------------------------------------------------
  // Self Check
  // ------------------------------------------------

  currentState = STATE_SELF_CHECK;

  selfCheck();

  currentState = STATE_STANDBY;

  updateLEDs();

  Serial.println();
  Serial.println("================================================");
  Serial.println("          SOLAR-SENTRY ΩX READY");
  Serial.println("================================================");
  Serial.println();
}

// ================================================================
// MAIN LOOP
// ================================================================

void loop()
{
  unsigned long now = millis();

  // ------------------------------------------------
  // Wi-Fi health
  // ------------------------------------------------

  if (now - lastWiFiCheck >= WIFI_CHECK_INTERVAL)
  {
    lastWiFiCheck = now;

    if (WiFi.status() != WL_CONNECTED)
    {
      backendAvailable = false;

      Serial.println("[NETWORK] Wi-Fi disconnected.");

      connectWiFi();
    }
  }

  // ------------------------------------------------
  // SENSOR UPDATE
  // ------------------------------------------------

  if (now - lastSensorRead >= SENSOR_INTERVAL)
  {
    lastSensorRead = now;

    readAllSensors();

    calculateSensorHealth();

    calculateEnvironmentScore();

    calculateLocalReadiness();

    updateObservationState();

    updateLEDs();
  }

  // ------------------------------------------------
  // TELEMETRY
  // ------------------------------------------------

  if (now - lastTelemetry >= TELEMETRY_INTERVAL)
  {
    lastTelemetry = now;

    sendTelemetry();
  }

  // ------------------------------------------------
  // AI COMMAND
  // ------------------------------------------------

  if (now - lastCommandPoll >= COMMAND_INTERVAL)
  {
    lastCommandPoll = now;

    pollAICommand();
  }

  // ------------------------------------------------
  // SERIAL REPORT
  // ------------------------------------------------

  if (now - lastSerialReport >= SERIAL_INTERVAL)
  {
    lastSerialReport = now;

    printSystemReport();
  }

  delay(10);
}

// ================================================================
// WIFI
// ================================================================

void connectWiFi()
{
  if (WiFi.status() == WL_CONNECTED)
  {
    backendAvailable = true;
    return;
  }

  Serial.println();
  Serial.print("[NETWORK] Connecting to Wi-Fi: ");
  Serial.println(WIFI_SSID);

  WiFi.mode(WIFI_STA);

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long start = millis();

  while (WiFi.status() != WL_CONNECTED &&
         millis() - start < 15000)
  {
    delay(500);

    Serial.print(".");
  }

  Serial.println();

  if (WiFi.status() == WL_CONNECTED)
  {
    backendAvailable = true;

    Serial.println("[NETWORK] Wi-Fi connected.");

    Serial.print("[NETWORK] ESP32 IP: ");
    Serial.println(WiFi.localIP());

    Serial.print("[NETWORK] RSSI: ");
    Serial.println(WiFi.RSSI());
  }
  else
  {
    backendAvailable = false;

    Serial.println("[NETWORK] Wi-Fi connection failed.");
    Serial.println("[NETWORK] Local autonomous mode active.");
  }
}

// ================================================================
// SENSOR READING
// ================================================================

void readAllSensors()
{
  // ------------------------------------------------
  // DHT22
  // ------------------------------------------------

  float h = dht.readHumidity();
  float t = dht.readTemperature();

  if (!isnan(h) && !isnan(t))
  {
    sensors.humidity = h;
    sensors.temperature = t;
    sensors.dhtOK = validateDHT();
  }
  else
  {
    sensors.dhtOK = false;
  }

  // ------------------------------------------------
  // BMP280
  // ------------------------------------------------

  if (sensors.bmpOK)
  {
    sensors.bmpTemperature = bmp.readTemperature();

    sensors.pressure = bmp.readPressure() / 100.0F;

    sensors.bmpOK = validateBMP();
  }

  // ------------------------------------------------
  // BH1750
  // ------------------------------------------------

  if (sensors.bh1750OK)
  {
    sensors.lux = lightMeter.readLightLevel();

    sensors.bh1750OK = validateBH1750();
  }

  // ------------------------------------------------
  // RAIN SENSOR
  // ------------------------------------------------

  sensors.rainRaw = analogRead(RAIN_PIN);

  sensors.rainOK = validateRain();
}

// ================================================================
// SENSOR VALIDATION
// ================================================================

bool validateDHT()
{
  if (isnan(sensors.temperature) ||
      isnan(sensors.humidity))
  {
    return false;
  }

  if (sensors.temperature < -20 ||
      sensors.temperature > 80)
  {
    return false;
  }

  if (sensors.humidity < 0 ||
      sensors.humidity > 100)
  {
    return false;
  }

  return true;
}

// ================================================================

bool validateBMP()
{
  if (isnan(sensors.pressure))
  {
    return false;
  }

  if (sensors.pressure < 300 ||
      sensors.pressure > 1200)
  {
    return false;
  }

  return true;
}

// ================================================================

bool validateBH1750()
{
  if (isnan(sensors.lux))
  {
    return false;
  }

  if (sensors.lux < 0)
  {
    return false;
  }

  return true;
}

// ================================================================

bool validateRain()
{
  if (sensors.rainRaw < 0 ||
      sensors.rainRaw > 4095)
  {
    return false;
  }

  return true;
}

// ================================================================
// SENSOR HEALTH
// ================================================================

void calculateSensorHealth()
{
  float total = 0;

  sensors.dhtConfidence =
      sensors.dhtOK ? 100.0 : 0.0;

  sensors.bmpConfidence =
      sensors.bmpOK ? 100.0 : 0.0;

  sensors.bh1750Confidence =
      sensors.bh1750OK ? 100.0 : 0.0;

  sensors.rainConfidence =
      sensors.rainOK ? 100.0 : 0.0;

  total =
      sensors.dhtConfidence +
      sensors.bmpConfidence +
      sensors.bh1750Confidence +
      sensors.rainConfidence;

  sensorHealthScore = total / 4.0;

  sensors.overallHealth = sensorHealthScore;
}

// ================================================================
// ENVIRONMENT SCORE
// ================================================================

void calculateEnvironmentScore()
{
  float score = 100.0;

  // ------------------------------------------------
  // Humidity
  // ------------------------------------------------

  if (sensors.dhtOK)
  {
    if (sensors.humidity > 85)
    {
      score -= 35;
    }
    else if (sensors.humidity > 75)
    {
      score -= 20;
    }
    else if (sensors.humidity > 65)
    {
      score -= 10;
    }
  }
  else
  {
    score -= 15;
  }

  // ------------------------------------------------
  // Rain
  // ------------------------------------------------

  if (sensors.rainOK)
  {
    if (sensors.rainRaw < RAIN_THRESHOLD)
    {
      score -= 60;
    }
  }
  else
  {
    score -= 10;
  }

  // ------------------------------------------------
  // Light
  // ------------------------------------------------

  if (sensors.bh1750OK)
  {
    if (sensors.lux < 5)
    {
      score -= 15;
    }
  }
  else
  {
    score -= 10;
  }

  // ------------------------------------------------
  // Pressure sanity
  // ------------------------------------------------

  if (!sensors.bmpOK)
  {
    score -= 10;
  }

  environmentScore = clampScore(score);
}

// ================================================================
// LOCAL READINESS
// ================================================================

void calculateLocalReadiness()
{
  /*
     Local fallback intelligence.

     The advanced AI backend can later override this
     decision using:

     Vision AI
     Solar AI
     Predictive model
     Mission planner
     Historical data
     Digital twin
     etc.

     ESP32 always retains a basic safety decision.
  */

  localReadinessScore =
      (environmentScore * 0.60) +
      (sensorHealthScore * 0.40);

  observationConfidence =
      (sensorHealthScore * 0.5) +
      (environmentScore * 0.5);

  localReadinessScore =
      clampScore(localReadinessScore);
}

// ================================================================
// OBSERVATION STATE
// ================================================================

void updateObservationState()
{
  // ------------------------------------------------
  // SAFETY FIRST
  // ------------------------------------------------

  if (sensors.rainOK &&
      sensors.rainRaw < RAIN_THRESHOLD)
  {
    currentState = STATE_SUSPEND;

    safePosition();

    return;
  }

  // ------------------------------------------------
  // SENSOR FAILURE
  // ------------------------------------------------

  if (sensorHealthScore < 40)
  {
    currentState = STATE_FAULT;

    safePosition();

    return;
  }

  // ------------------------------------------------
  // LOCAL DECISION
  // ------------------------------------------------

  if (localReadinessScore >= 80)
  {
    currentState = STATE_OBSERVE;
  }
  else if (localReadinessScore >= 50)
  {
    currentState = STATE_WAIT;
  }
  else
  {
    currentState = STATE_SUSPEND;
  }
}

// ================================================================
// LED STATUS
// ================================================================

void updateLEDs()
{
  digitalWrite(GREEN_LED, LOW);
  digitalWrite(YELLOW_LED, LOW);
  digitalWrite(RED_LED, LOW);

  switch (currentState)
  {
    case STATE_OBSERVE:
      digitalWrite(GREEN_LED, HIGH);
      break;

    case STATE_WAIT:
    case STATE_STANDBY:
      digitalWrite(YELLOW_LED, HIGH);
      break;

    case STATE_SUSPEND:
    case STATE_FAULT:
    case STATE_SAFE:
      digitalWrite(RED_LED, HIGH);
      break;

    default:
      digitalWrite(YELLOW_LED, HIGH);
      break;
  }
}

// ================================================================
// STATE STRING
// ================================================================

String stateToString()
{
  switch (currentState)
  {
    case STATE_BOOT:
      return "BOOT";

    case STATE_SELF_CHECK:
      return "SELF_CHECK";

    case STATE_STANDBY:
      return "STANDBY";

    case STATE_OBSERVE:
      return "OBSERVE";

    case STATE_WAIT:
      return "WAIT";

    case STATE_SUSPEND:
      return "SUSPEND";

    case STATE_FAULT:
      return "FAULT";

    case STATE_SAFE:
      return "SAFE";

    default:
      return "UNKNOWN";
  }
}

// ================================================================
// SAFE POSITION
// ================================================================

void safePosition()
{
  panPosition = 90;
  tiltPosition = 90;

  panServo.write(panPosition);
  tiltServo.write(tiltPosition);
}

// ================================================================
// PAN CONTROL
// ================================================================

void movePan(int angle)
{
  angle = constrain(angle, PAN_MIN, PAN_MAX);

  panPosition = angle;

  panServo.write(panPosition);

  Serial.print("[ACTUATOR] PAN -> ");
  Serial.print(panPosition);
  Serial.println("°");
}

// ================================================================
// TILT CONTROL
// ================================================================

void moveTilt(int angle)
{
  angle = constrain(angle, TILT_MIN, TILT_MAX);

  tiltPosition = angle;

  tiltServo.write(tiltPosition);

  Serial.print("[ACTUATOR] TILT -> ");
  Serial.print(tiltPosition);
  Serial.println("°");
}

// ================================================================
// ACTIVE PERCEPTION SCAN
// ================================================================

void performActiveScan()
{
  /*
     Demonstration of closed-loop active sensing.

     The ESP32 moves through several positions.

     The AI backend can later evaluate the images
     produced at each position and choose the
     highest-quality region.
  */

  Serial.println();
  Serial.println("[ACTIVE PERCEPTION]");
  Serial.println("Starting environmental scan...");

  int scanPositions[] =
  {
    45,
    90,
    135
  };

  for (int i = 0; i < 3; i++)
  {
    movePan(scanPositions[i]);

    delay(1500);

    Serial.print("[SCAN] Position ");
    Serial.print(i + 1);
    Serial.print(" = ");
    Serial.print(scanPositions[i]);
    Serial.println("°");

    // Sensor state is re-evaluated
    readAllSensors();

    calculateSensorHealth();

    calculateEnvironmentScore();

    calculateLocalReadiness();

    if (sensors.rainRaw < RAIN_THRESHOLD)
    {
      Serial.println("[SCAN] Rain detected.");
      safePosition();
      return;
    }
  }

  movePan(90);

  Serial.println("[ACTIVE PERCEPTION] Scan complete.");
}

// ================================================================
// SERIAL REPORT
// ================================================================

void printSystemReport()
{
  Serial.println();
  Serial.println("================================================");
  Serial.println("          SOLAR-SENTRY ΩX TELEMETRY");
  Serial.println("================================================");

  Serial.print("Device ID          : ");
  Serial.println(DEVICE_ID);

  Serial.print("Uptime             : ");
  Serial.print((millis() - bootTime) / 1000);
  Serial.println(" sec");

  Serial.println();

  Serial.println("---- ENVIRONMENT ----");

  Serial.print("Temperature        : ");
  Serial.print(sensors.temperature);
  Serial.println(" °C");

  Serial.print("Humidity           : ");
  Serial.print(sensors.humidity);
  Serial.println(" %");

  Serial.print("Pressure           : ");
  Serial.print(sensors.pressure);
  Serial.println(" hPa");

  Serial.print("Light              : ");
  Serial.print(sensors.lux);
  Serial.println(" lux");

  Serial.print("Rain ADC           : ");
  Serial.println(sensors.rainRaw);

  Serial.println();

  Serial.println("---- SENSOR HEALTH ----");

  Serial.print("DHT22              : ");
  Serial.print(sensors.dhtConfidence);
  Serial.println("%");

  Serial.print("BMP280             : ");
  Serial.print(sensors.bmpConfidence);
  Serial.println("%");

  Serial.print("BH1750             : ");
  Serial.print(sensors.bh1750Confidence);
  Serial.println("%");

  Serial.print("Rain Sensor        : ");
  Serial.print(sensors.rainConfidence);
  Serial.println("%");

  Serial.print("Overall Health     : ");
  Serial.print(sensorHealthScore);
  Serial.println("%");

  Serial.println();

  Serial.println("---- INTELLIGENCE ----");

  Serial.print("Environment Score  : ");
  Serial.print(environmentScore);
  Serial.println("%");

  Serial.print("Local Readiness    : ");
  Serial.print(localReadinessScore);
  Serial.println("%");

  Serial.print("Vision Score       : ");
  Serial.print(visionScore);
  Serial.println("%");

  Serial.print("Solar Data Score   : ");
  Serial.print(solarDataScore);
  Serial.println("%");

  Serial.print("Predicted Score    : ");
  Serial.print(predictedScore);
  Serial.println("%");

  Serial.print("Confidence         : ");
  Serial.print(observationConfidence);
  Serial.println("%");

  Serial.print("AI Decision        : ");
  Serial.println(aiDecision);

  Serial.print("Current State      : ");
  Serial.println(stateToString());

  Serial.println();

  Serial.println("---- ACTUATORS ----");

  Serial.print("Pan                : ");
  Serial.print(panPosition);
  Serial.println("°");

  Serial.print("Tilt               : ");
  Serial.print(tiltPosition);
  Serial.println("°");

  Serial.println();

  Serial.print("Wi-Fi              : ");

  if (WiFi.status() == WL_CONNECTED)
    Serial.println("CONNECTED");
  else
    Serial.println("OFFLINE");

  Serial.println("================================================");
}

// ================================================================
// TELEMETRY JSON
// ================================================================

String createTelemetryJSON()
{
  String json = "{";

  json += "\"device_id\":\"";
  json += DEVICE_ID;
  json += "\",";

  json += "\"uptime_ms\":";
  json += String(millis());
  json += ",";

  // ---------------- ENVIRONMENT ----------------

  json += "\"temperature\":";
  json += String(sensors.temperature, 2);
  json += ",";

  json += "\"humidity\":";
  json += String(sensors.humidity, 2);
  json += ",";

  json += "\"pressure\":";
  json += String(sensors.pressure, 2);
  json += ",";

  json += "\"bmp_temperature\":";
  json += String(sensors.bmpTemperature, 2);
  json += ",";

  json += "\"lux\":";
  json += String(sensors.lux, 2);
  json += ",";

  json += "\"rain_raw\":";
  json += String(sensors.rainRaw);
  json += ",";

  // ---------------- HEALTH ----------------

  json += "\"dht_ok\":";
  json += sensors.dhtOK ? "true" : "false";
  json += ",";

  json += "\"bmp_ok\":";
  json += sensors.bmpOK ? "true" : "false";
  json += ",";

  json += "\"bh1750_ok\":";
  json += sensors.bh1750OK ? "true" : "false";
  json += ",";

  json += "\"rain_ok\":";
  json += sensors.rainOK ? "true" : "false";
  json += ",";

  json += "\"sensor_health\":";
  json += String(sensorHealthScore, 2);
  json += ",";

  // ---------------- AI ----------------

  json += "\"environment_score\":";
  json += String(environmentScore, 2);
  json += ",";

  json += "\"local_readiness\":";
  json += String(localReadinessScore, 2);
  json += ",";

  json += "\"vision_score\":";
  json += String(visionScore, 2);
  json += ",";

  json += "\"solar_score\":";
  json += String(solarDataScore, 2);
  json += ",";

  json += "\"predicted_score\":";
  json += String(predictedScore, 2);
  json += ",";

  json += "\"confidence\":";
  json += String(observationConfidence, 2);
  json += ",";

  // ---------------- STATE ----------------

  json += "\"state\":\"";
  json += stateToString();
  json += "\",";

  json += "\"ai_decision\":\"";
  json += aiDecision;
  json += "\",";

  // ---------------- ACTUATORS ----------------

  json += "\"pan\":";
  json += String(panPosition);
  json += ",";

  json += "\"tilt\":";
  json += String(tiltPosition);
  json += ",";

  // ---------------- NETWORK ----------------

  json += "\"wifi_rssi\":";
  json += String(WiFi.RSSI());

  json += "}";

  return json;
}

// ================================================================
// SEND TELEMETRY
// ================================================================

void sendTelemetry()
{
  if (WiFi.status() != WL_CONNECTED)
  {
    backendAvailable = false;

    return;
  }

  HTTPClient http;

  http.begin(TELEMETRY_URL);

  http.addHeader("Content-Type", "application/json");

  String payload = createTelemetryJSON();

  int responseCode =
      http.POST(payload);

  if (responseCode > 0)
  {
    backendAvailable = true;

    Serial.print("[AI] Telemetry sent. HTTP = ");
    Serial.println(responseCode);
  }
  else
  {
    backendAvailable = false;

    Serial.print("[AI] Telemetry failed: ");
    Serial.println(http.errorToString(responseCode));
  }

  http.end();
}

// ================================================================
// POLL AI COMMAND
// ================================================================

void pollAICommand()
{
  if (WiFi.status() != WL_CONNECTED)
    return;

  HTTPClient http;

  http.begin(COMMAND_URL);

  http.addHeader("Content-Type", "application/json");

  String request =
      "{\"device_id\":\"" +
      String(DEVICE_ID) +
      "\"}";

  int responseCode =
      http.POST(request);

  if (responseCode == 200)
  {
    String response = http.getString();

    Serial.print("[AI] Command received: ");
    Serial.println(response);

    // ------------------------------------------------
    // Simple command parsing
    // ------------------------------------------------

    if (response.indexOf("OBSERVE") >= 0)
    {
      executeAICommand("OBSERVE");
    }

    else if (response.indexOf("WAIT") >= 0)
    {
      executeAICommand("WAIT");
    }

    else if (response.indexOf("SUSPEND") >= 0)
    {
      executeAICommand("SUSPEND");
    }

    else if (response.indexOf("SCAN") >= 0)
    {
      executeAICommand("SCAN");
    }

    else if (response.indexOf("SAFE") >= 0)
    {
      executeAICommand("SAFE");
    }

    // Optional direct pan command
    if (response.indexOf("PAN_LEFT") >= 0)
    {
      movePan(panPosition - 15);
    }

    if (response.indexOf("PAN_RIGHT") >= 0)
    {
      movePan(panPosition + 15);
    }
  }

  http.end();
}

// ================================================================
// EXECUTE AI COMMAND
// ================================================================

void executeAICommand(String command)
{
  command.trim();

  Serial.print("[AI COMMAND] ");
  Serial.println(command);

  aiDecision = command;

  if (command == "OBSERVE")
  {
    currentState = STATE_OBSERVE;

    updateLEDs();
  }

  else if (command == "WAIT")
  {
    currentState = STATE_WAIT;

    updateLEDs();
  }

  else if (command == "SUSPEND")
  {
    currentState = STATE_SUSPEND;

    safePosition();

    updateLEDs();
  }

  else if (command == "SCAN")
  {
    performActiveScan();
  }

  else if (command == "SAFE")
  {
    currentState = STATE_SAFE;

    safePosition();

    updateLEDs();
  }
}

// ================================================================
// SELF CHECK
// ================================================================

void selfCheck()
{
  Serial.println();
  Serial.println("[SELF CHECK] Starting...");
  Serial.println();

  bool systemOK = true;

  // DHT test
  float h = dht.readHumidity();
  float t = dht.readTemperature();

  if (isnan(h) || isnan(t))
  {
    Serial.println("[FAIL] DHT22");
    systemOK = false;
  }
  else
  {
    Serial.println("[PASS] DHT22");
  }

  // BMP
  if (sensors.bmpOK)
  {
    Serial.println("[PASS] BMP280");
  }
  else
  {
    Serial.println("[FAIL] BMP280");
    systemOK = false;
  }

  // BH1750
  if (sensors.bh1750OK)
  {
    Serial.println("[PASS] BH1750");
  }
  else
  {
    Serial.println("[FAIL] BH1750");
    systemOK = false;
  }

  // Rain
  int rain = analogRead(RAIN_PIN);

  if (rain >= 0 && rain <= 4095)
  {
    Serial.println("[PASS] Rain Sensor");
  }
  else
  {
    Serial.println("[FAIL] Rain Sensor");
    systemOK = false;
  }

  // Servos
  movePan(90);
  moveTilt(90);

  Serial.println("[PASS] Pan Servo");
  Serial.println("[PASS] Tilt Servo");

  Serial.println();

  if (systemOK)
  {
    Serial.println("[SELF CHECK] SYSTEM READY.");
  }
  else
  {
    Serial.println("[SELF CHECK] WARNING: SENSOR FAULT.");
  }

  delay(1000);
}

// ================================================================
// SCORE LIMITER
// ================================================================

float clampScore(float value)
{
  if (value < 0)
    return 0;

  if (value > 100)
    return 100;

  return value;
}