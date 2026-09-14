# Solar Sentry — Master Architecture Document

**Autonomous Cognitive Solar Observatory & Scientific Discovery Platform**

---

## 1. Executive Summary

**Solar Sentry** is an autonomous cognitive solar observatory testbed demonstrating how future distributed solar research platforms can achieve self-monitoring, predictive environmental adaptation, closed-loop active perception, explainable reasoning, and continual learning.

The physical prototype pairs a low-cost edge system (ESP32 DevKit, multi-modal environmental sensors, pan/tilt dual-axis tracker, and an ESP32-CAM prototype environmental vision node) with a centralized AI and Mission Control Platform.

### The Cognitive Architecture Loop
```
PERCEIVE  (Sensors + Vision Ingestion)
    ↓
UNDERSTAND (Sensor Fusion, Anomaly AI, Solar Disk Analysis)
    ↓
PREDICT   (Multi-Horizon 15/30/60 min Observation Quality Forecast)
    ↓
PLAN      (Autonomous Mission Scheduler & Active Perception)
    ↓
ACT       (Physical Command Dispatch to ESP32 Edge)
    ↓
VERIFY    (Post-action Visual & Environmental Quality Verification)
    ↓
LEARN     (Mission Memory, Drift Tracking & Model Feedback)
```

---

## 2. Hardware Contract (Agent 1 Ownership)

### Controller: ESP32 DevKit
- **DHT22** (Temperature & Humidity): `GPIO4` (3.3V, 10k pullup)
- **BH1750** (Ambient Illuminance / Lux): I2C `SDA -> GPIO21`, `SCL -> GPIO22` (Shared I2C bus @ 100kHz)
- **BMP280** (Barometric Pressure & Temp): I2C `SDA -> GPIO21`, `SCL -> GPIO22` (Shared I2C bus @ 100kHz, Address `0x76`)
- **Rain Sensor**: Analog Output `AO -> GPIO34` (ADC1 Channel 6, input-only pin)
- **Pan Servo**: PWM `Signal -> GPIO18`, External Regulated 5V, Common Ground
- **Tilt Servo**: PWM `Signal -> GPIO19`, External Regulated 5V, Common Ground
- **Status LEDs**:
  - Green LED: `GPIO25 -> Resistor -> GND`
  - Yellow LED: `GPIO26 -> Resistor -> GND`
  - Red LED: `GPIO27 -> Resistor -> GND`

### Environmental Vision Node: ESP32-CAM
- Completely isolated from sensor GPIOs.
- Operates on dedicated Wi-Fi network interface.
- Exposes snapshot HTTP endpoints (`/capture`, `/status`).
- Classified strictly as an **environmental vision prototype**, not a diffraction-limited scientific CCD.

---

## 3. Subsystem Boundaries (10-Agent Multi-Agent Model)

- **Agent 1 (Edge Device & ESP32 Firmware)**: Sensor acquisition, hardware validation, pan/tilt servo actuator control, 3-LED status signalling, local safety interlocks, heartbeat, watchdog management, JSON telemetry and command handling.
- **Agent 2 (Backend API & Communication)**: Ingestion REST endpoints, WebSocket streaming, device registration, command dispatch.
- **Agent 3 (Database & Data Layer)**: PostgreSQL schemas, telemetry storage, historical observations, migrations.
- **Agent 4 (Dashboard & Frontend)**: Real-time UI, telemetry displays, solar visualization, mission control panel.
- **Agent 5 (Computer Vision & Solar Intelligence)**: Solar disk localization, sunspot counting, limb-darkening analysis, obstruction/cloud detection.
- **Agent 6 (Environment AI & Quality Prediction)**: 15/30/60-minute readiness forecasting, microclimate analysis.
- **Agent 7 (Sensor Fusion & Health Anomaly AI)**: Sensor consistency validation, Isolation Forest anomaly scoring, health classification.
- **Agent 8 (Cognitive Decision Engine & XAI)**: Multimodal state evaluation, explainable reasoning traces, decision outputs (`OBSERVE`, `WAIT`, `SUSPEND`, `SAFE`, `SCAN`).
- **Agent 9 (Mission Planner & Active Perception)**: Closed-loop mission planning, optimal region search, verification step.
- **Agent 10 (Digital Twin, Simulation & Learning)**: Predictive state simulation, replay engine, what-if scenario testing.

---

## 4. Safety Hierarchy

Safety takes absolute priority over observation optimization:
$$\text{SAFETY} > \text{HARDWARE HEALTH} > \text{DATA QUALITY} > \text{OBSERVATION OBJECTIVE} > \text{OPTIMIZATION}$$

Local edge safety rules:
1. **Rain Detected**: Instant transition to `SUSPEND` state, stow servos to protected position (`Pan: 90`, `Tilt: 0`), Red LED lit.
2. **Communication Loss**: If backend heartbeat drops $> 30\,\text{s}$, edge enters `SAFE` state and parks.
3. **Sensor Disagreement / Failure**: Faulty sensor flagged `UNHEALTHY`, system enters `DEGRADED` state.
