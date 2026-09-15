# Solar Sentry

**Autonomous Cognitive Solar Observatory & Cyber-Physical Edge Platform**

---

## 1. Overview

**Solar Sentry** is an integrated autonomous cyber-physical solar observatory designed for continuous solar disk tracking, multimodal microclimate monitoring, safety-critical edge interlocks, and computer-vision-driven solar feature extraction.

The system embodies the closed-loop cyber-physical paradigm:
```
REAL ESP32 SENSORS ──► EDGE TELEMETRY ──► FASTAPI BACKEND ──► SQLITE DB ──► SENSOR FUSION AI
                                                                                  │
                                                                                  ▼
NEW TELEMETRY ◄── SERVO ACTUATION ◄── ESP32 COMMAND ◄── MISSION PLANNER ◄── COGNITIVE DECISION
```
AND IN PARALLEL:
```
ESP32-CAM ──► DYNAMIC mDNS DISCOVERY ──► CAMERA REGISTRY ──► MJPEG PROXY ──► V0 FRONTEND (10 PAGES)
                                                                                  │
                                                                                  ▼
                                                                           AI VISION PIPELINE
```

- **Perceive**: Multimodal sensor matrix (DHT22, BMP280, BH1750, Rain ADC) + ESP32-CAM optical feed.
- **Understand**: Real-time solar disk detection, limb darkening evaluation, and sunspot segmentation.
- **Predict**: 15/30/60-minute Observation Readiness Score (ORS) forecast and atmospheric seeing estimation.
- **Plan**: Target survey scheduling, solar trajectory planning, and energy-conscious dwell times.
- **Act**: Dual-axis Azimuth/Elevation mechanical tracking with hardware safety overrides.
- **Verify**: Digital twin kinematics cross-validation and optical alignment telemetry.
- **Learn**: Physics-informed degradation models and adaptive image enhancement calibration.

---

## 2. The 10 Observatory Dashboard Pages (V0 Source of Truth)

Solar Sentry features a responsive mission-control dashboard with 10 distinct pages, each enhanced with dedicated high-resolution 16:9 astronomical backdrops and zero extraneous floating figures:

1. **Home** (`/space/home.jpg`): Earth from orbit with sunrise; live camera feed, real microclimate telemetry, AI decision dials, and quick mission controls.
2. **Live Camera** (`/space/live-camera.jpg`): Solar corona and prominences; live MJPEG stream, dynamic mDNS discovery controls, real-time optical quality scorecards, calibration sliders (brightness, contrast, sharpness, gamma, CLAHE), and recent captures gallery.
3. **Solar Analysis** (`/space/solar-analysis.jpg`): Photosphere and sunspots; computer vision feature detection (sunspots, active regions, C/M-class flares, prominences), 24h solar activity index, and AI analysis reports.
4. **Observatory** (`/space/observatory.jpg`): Research observatory dome under the Milky Way; observatory instrument registry, live observation feed, persisted observation log, and celestial tracking stats.
5. **Missions** (`/space/missions.jpg`): Orbital trajectories and solar research satellites; active mission manifest, real-time satellite trajectory tracking, mission parameters, and actuator dispatch controls.
6. **Digital Twin** (`/space/digital-twin.jpg`): 3D solar system and magnetic field lines; 1:1 dual-axis servo kinematics synchronization (Pan/Tilt), manual servo jog controls, layer toggles, and live physical solar parameters.
7. **AI Insights** (`/space/ai-insights.jpg`): Holographic neural cosmic nexus; interactive Solar Sentry AI Assistant with natural language queries, Agent 8 cognitive reasoning traces, and activity forecasts.
8. **System Health** (`/space/system-health.jpg`): Earth magnetosphere and solar wind plasma; calculated operational health ring, hardware subsystem registry, and anomaly alert safety interlocks with operator acknowledgment.
9. **Data Logs** (`/space/data-logs.jpg`): Galactic core and interstellar dust lanes; data ingestion trends, type distribution rings, categorized log filters, and complete telemetry/event export in JSON format.
10. **Settings** (`/space/settings.jpg`): Relativistic pulsar accretion disk; hardware configuration, dynamic mDNS camera discovery scan, manual IP fallback, operational mode toggles (DEMO vs HARDWARE), notification channels, and platform metadata.

---

## 3. Dynamic ESP32-CAM Discovery & Live Streaming

### Dynamic IP Handling (No Manual Entry Required)
> **CRITICAL FEATURE**: The user does **NOT** need to manually enter the ESP32-CAM IP address every time it boots or renews its DHCP lease.

- The ESP32-CAM firmware advertises its presence on the local network via **mDNS** under the hostname:
  ```
  solar-sentry-cam.local
  ```
- The backend `CameraRegistry` continuously resolves `solar-sentry-cam.local` to its current dynamically assigned DHCP IP address (e.g. `192.168.1.50` ➔ `192.168.1.73` on reboot).
- The discovery pipeline:
  1. Resolves `solar-sentry-cam.local` via mDNS multicast.
  2. Verifies the camera HTTP endpoint responds with status 200.
  3. Updates the central `CameraRegistry` with current IP, response latency, and timestamp.
  4. Automatically reconnects when DHCP reassigns IP without requiring manual intervention or code changes.

### Secure Streaming Proxy (No Mixed-Content Issues)
- If the frontend is accessed over HTTPS or across separate network origins, browsers block direct HTTP access to LAN camera endpoints (`http://192.168.x.x`).
- The Solar Sentry backend provides a high-efficiency MJPEG streaming proxy:
  ```
  GET /api/v1/camera/stream
  ```
- The proxy streams frames cleanly to the browser, prevents mixed-content errors, isolates LAN endpoints, and enforces SSRF protection (only verified camera devices registered in `CameraRegistry` are proxied).

---

## 4. Operating Modes: DEMO vs. LIVE HARDWARE

The top header bar provides an instant, bi-directional mode switch:

### DEMO MODE (Autonomous Simulation)
- Zero physical hardware required.
- Simulated microclimate telemetry with realistic atmospheric physics.
- High-fidelity simulated optical camera feed with limb darkening and cloud occlusion.
- Autonomous simulated AI decisions, mission tracking, and digital twin kinematics.
- Clearly watermarked and labelled: `SIMULATION FEED` / `DEMO MODE`.

### LIVE HARDWARE MODE (Physical Cyber-Physical Prototype)
- Binds directly to the physical ESP32 DevKit and ESP32-CAM node over the local network.
- Displays genuine sensor readings: DHT22 (temp/humidity), BMP280 (barometric pressure), BH1750 (light lux), and Rain ADC.
- Displays real actuator pan/tilt servo angles and physical status LEDs.
- **Strict Zero-Fabrication Rule**: If physical hardware is offline or disconnected, the system displays:
  ```
  LIVE HARDWARE MODE — ESP32 DEVICE OFFLINE
  ```
  Missing sensors or disconnected camera are never replaced with fake "online" values.

---

## 5. Quick Start & Launch Instructions

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm
- PlatformIO (optional, for physical ESP32 flashing)

### A. Start the Backend API Server
```bash
# From workspace root
python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload
```
- Interactive API Swagger Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Live Camera Stream Proxy: [http://localhost:8000/api/v1/camera/stream](http://localhost:8000/api/v1/camera/stream)
- Dynamic Camera Discovery: [http://localhost:8000/api/v1/camera/discover](http://localhost:8000/api/v1/camera/discover)
- WebSocket Telemetry Channel: `ws://localhost:8000/ws/telemetry`

### B. Start the Mission Control Frontend Dashboard
```bash
cd frontend
npm install
npm run dev
```
- Dashboard URL: [http://localhost:5173/](http://localhost:5173/)

---

## 6. Physical Hardware & Pinout Specifications

| Peripheral | Controller Pin | Electrical / Protocol Specification |
| :--- | :--- | :--- |
| **DHT22 Sensor** | `GPIO 4` | 3.3V, 1-Wire with 10kΩ pull-up |
| **BMP280 Barometer** | `SDA: GPIO 21, SCL: GPIO 22` | I2C Address `0x76` |
| **BH1750 Ambient Light** | `SDA: GPIO 21, SCL: GPIO 22` | I2C Address `0x23` |
| **Rain Sensor Plate** | `GPIO 34` | ADC1 Analog Channel 6 ($< 1500$ indicates wet) |
| **Azimuth (Pan) Servo** | `GPIO 18` | PWM 50 Hz ($0^\circ - 180^\circ$), external 5V |
| **Elevation (Tilt) Servo**| `GPIO 19` | PWM 50 Hz ($0^\circ - 90^\circ$), external 5V |
| **Status LEDs** | `GPIO 25` (Green), `GPIO 26` (Yellow), `GPIO 27` (Red) | 330Ω current-limiting resistors |
| **ESP32-CAM Node** | Independent Wi-Fi Node | mDNS `solar-sentry-cam.local`, Port 80 |

---

## 7. Automated Test Suite

### Run All Backend Unit Tests (103 Tests)
```bash
python -m pytest tests/unit/
```
Validates:
- `test_camera_discovery.py`: mDNS dynamic resolution, dynamic DHCP IP changes, health checks, and fallback configuration.
- `test_cognitive_decision_engine.py`: Agent 8 XAI reasoning and decision thresholds.
- `test_database_config.py`, `test_models.py`, `test_repositories.py`: SQLite persistence and telemetry records.
- `test_edge_firmware.py`: ESP32 sensor parsing and servo command serialization.
- `test_environment_ai.py`: Atmospheric seeing and microclimate predictions.
- `test_mission_planner.py`: Autonomous solar survey scheduling.
- `test_sensor_fusion_health.py`: Isolation Forest anomaly detection and ORS scoring.
- `test_vision_pipeline.py`: Solar disk edge detection, limb darkening, and CLAHE calibration.

### Run Frontend Unit Tests (9 Tests)
```bash
cd frontend
npm test
```
Validates simulator scenarios, contract schemas, and telemetry state machines.

### Build Production Dashboard Bundle
```bash
cd frontend
npm run build
```
Compiles a production bundle with Vite and TypeScript (0 type errors).

---

## 8. Git Safety & Branching Model

- **Active Development & Releases**: `main`
- **Protected Branch**: `old` (Never checked out, modified, rebased, or pushed to)
- **Zero Force-Push Policy**: All releases to `origin/main` are clean, forward-only commits.
