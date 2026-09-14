# Solar Sentry

**Autonomous Cognitive Solar Observatory & Edge AI Discovery Platform**

---

## 1. Overview

**Solar Sentry** is an autonomous cognitive solar observatory designed for continuous solar disk tracking, multimodal microclimate monitoring, safety-critical edge interlocks, and computer-vision-driven solar feature extraction.

The system embodies the closed-loop cognitive paradigm:
```
PERCEIVE → UNDERSTAND → PREDICT → PLAN → ACT → VERIFY → LEARN
```

- **Perceive**: Multimodal sensor matrix (DHT22, BMP280, BH1750, Rain ADC) + optical camera feed.
- **Understand**: Real-time solar disk detection, limb darkening evaluation, and sunspot segmentation.
- **Predict**: 15/30/60-minute Observation Readiness Score (ORS) forecast and atmospheric seeing estimation.
- **Plan**: Target survey scheduling, solar trajectory planning, and energy-conscious dwell times.
- **Act**: Dual-axis Azimuth/Elevation mechanical tracking with hardware safety overrides.
- **Verify**: Digital twin kinematics cross-validation and optical alignment telemetry.
- **Learn**: Physics-informed degradation models and adaptive image enhancement calibration.

---

## 2. Multi-Agent Architecture

Solar Sentry is structured across 10 coordinated engineering subsystems:

1. **Agent 1: Firmware & Edge Integration** (`firmware/esp32/`, `firmware/esp32_cam/`, `firmware/mock_edge/`)
2. **Agent 2: Backend API & Telemetry Infrastructure** (`backend/`)
3. **Agent 3: Database & Persistence Layer** (`backend/database/`)
4. **Agent 4: Mission Control Dashboard** (`frontend/`)
5. **Agent 5: Computer Vision & Solar Intelligence** (`ai/vision/`)
6. **Agent 6: Microclimate AI & Quality Prediction** (`ai/environment/`)
7. **Agent 7: Sensor Health & Fusion AI** (`ai/fusion/`, `ai/anomaly/`)
8. **Agent 8: Cognitive Decision Engine & Explainable AI** (`ai/decision/`)
9. **Agent 9: Autonomous Mission Planner** (`ai/mission/`)
10. **Agent 10: Digital Twin & Continuous Learning** (`twin/`, `integration/`)

Full integration audit details are maintained in [`docs/FINAL_SYSTEM_AUDIT.md`](file:///d:/Personal%20Projects/Solar%20Sentry/docs/FINAL_SYSTEM_AUDIT.md).

---

## 3. Quick Start & Launch Instructions

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm
- PlatformIO (optional, for flashing physical ESP32)

### A. Start the Backend API & Telemetry Broadcaster
```bash
# From workspace root
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```
- REST API Documentation: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- WebSocket Telemetry Stream: `ws://127.0.0.1:8000/ws/telemetry`

### B. Start the Mission Control Frontend Dashboard
```bash
cd frontend
npm install
npm run dev
```
- Dashboard URL: [http://localhost:5173/](http://localhost:5173/)

---

## 4. Operating Modes: DEMO vs. LIVE HARDWARE

Solar Sentry features a high-visibility, bi-directional mode toggle switch in the dashboard header:

### DEMO MODE (Simulation & Validation)
- Fully functional without physical hardware connected.
- Runs 10 canonical astronomical and environmental scenarios:
  1. *Clear Sky Optimal Tracking*
  2. *Cloud Transit & Quality Dip*
  3. *Sudden Precipitation Alarm (Auto-stow)*
  4. *Sensor Disagreement & Drift (DEGRADED mode)*
  5. *Communication Loss Failsafe (SAFE mode)*
  6. *Rapid Solar Flare Optical Spike*
  7. *High Wind Gust & Safety Stow*
  8. *Enclosure Thermal Overheat Throttle*
  9. *Optical Deck Soiling & Dust Drift*
  10. *Solar Eclipse Transit Tracking*
- Generates synthetic solar images with limb darkening and realistic cloud occlusion.

### LIVE HARDWARE MODE (Physical Prototype)
- Connects directly to physical ESP32 controller and ESP32-CAM node over the local network.
- **Integrity Rule**: If physical hardware is disconnected or unreachable, the system displays `LIVE HARDWARE MODE — ESP32 DEVICE OFFLINE` and strictly suppresses fabricated data.

---

## 5. Optical Sentry & Vision Deck

Navigate to the **OPTICAL & VISION** tab on the dashboard to access the optical observation and calibration station:

- **Live Capture**: Acquire high-resolution frames from ESP32-CAM or solar generator.
- **Interactive Calibration Controls**:
  - Brightness ($\pm 60$)
  - Contrast ($0.5\times$ to $2.5\times$)
  - Gamma ($0.4$ to $2.0$)
  - Sharpness / Unsharp Mask ($0 - 100\%$)
  - CLAHE (Contrast Limited Adaptive Histogram Equalization)
  - Color Inversion (Solar Negative)
  - 90° Incremental Rotation
- **Astronomical Presets**: One-click *Auto Enhance* and *Sunspot High Contrast*.
- **Objective Quality Scorecard**:
  - Composite Quality Score ($0 - 100$)
  - Tenengrad Sharpness Index
  - RMS Contrast
  - Exposure Fidelity & Dynamic Range
  - Noise Level
  - Detected Sunspot Count & Bounding Boxes
- **Diagnostic Access**: Direct *Open Camera Device* link to inspect the native ESP32-CAM web portal.

---

## 6. Physical Hardware & Pinout Contract

| Component | Pin / Interface | Specification |
| :--- | :--- | :--- |
| **DHT22 Sensor** | `GPIO 4` | 3.3V, 10kΩ pull-up resistor |
| **BMP280 Sensor** | `SDA: GPIO 21, SCL: GPIO 22` | I2C Address `0x76` |
| **BH1750 Sensor** | `SDA: GPIO 21, SCL: GPIO 22` | I2C Address `0x23` |
| **Rain Detection Plate** | `GPIO 34` | ADC1 Analog Input ($< 2000$ indicates wet) |
| **Azimuth (Pan) Servo** | `GPIO 18` | PWM 50 Hz ($0^\circ - 180^\circ$), external 5V power |
| **Elevation (Tilt) Servo** | `GPIO 19` | PWM 50 Hz ($0^\circ - 90^\circ$), external 5V power |
| **Status LEDs** | `GPIO 25` (Green), `GPIO 26` (Yellow), `GPIO 27` (Red) | Current limiting 330Ω resistors |
| **ESP32-CAM** | Independent Wi-Fi Node | Configured via `ESP32_CAM_URL=http://192.168.1.120` |

---

## 7. Testing & Verification

### Run All Backend, AI, & Integration Tests (112 Tests)
```bash
python -m pytest tests/
```

### Run Frontend Contract & Simulator Tests (9 Tests)
```bash
cd frontend
npm test
```

### Build Production Dashboard Bundle
```bash
cd frontend
npm run build
```

---

## 8. Environment Configuration

Copy `.env.example` to `.env` and customize as needed:
```bash
cp .env.example .env
```
Key configuration parameters:
- `SOLAR_SENTRY_DEFAULT_MODE`: `DEMO` or `HARDWARE`
- `ESP32_CAM_URL`: IP address of ESP32-CAM (default `http://192.168.1.120`)
- `SOLAR_SENTRY_DB_URL`: SQLite or PostgreSQL connection string
