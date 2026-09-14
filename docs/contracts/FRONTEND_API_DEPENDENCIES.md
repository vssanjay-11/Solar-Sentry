# Solar Sentry — Frontend API & Integration Contract Dependencies

*Author: Agent 4 (Frontend & Observatory Dashboard)*  
*Target Subsystems: Agent 2 (Backend API), Agent 3 (Database), Agents 5–10 (Intelligence Services)*

---

## 1. Overview

The **Solar Sentry Observatory Dashboard** is a cognitive, mission-control grade interface. It strictly acts as a consumer and command dispatcher. It does **not** compute AI inference, state transitions, or hardware controls client-side.

This document details all upstream REST endpoints, WebSocket event channels, and data schemas required by Agent 4.

---

## 2. Real-Time Streaming (WebSocket)

### Endpoint: `ws://{HOST}/ws/telemetry`

The dashboard establishes a persistent bidirectional WebSocket connection for millisecond-latency telemetry streaming and instantaneous alert propagation.

#### Outbound Client Messages (Subscriptions)
```json
{
  "action": "subscribe",
  "channels": ["telemetry", "ai_state", "alerts", "vision"]
}
```

#### Inbound Stream Payloads

##### A. `telemetry` (1 Hz - 5 Hz)
Adheres strictly to `docs/contracts/SensorTelemetry.json`:
```json
{
  "channel": "telemetry",
  "data": {
    "device_id": "esp32-sentry-01",
    "timestamp": "2026-09-13T11:20:00Z",
    "uptime_seconds": 3600,
    "temperature": 27.4,
    "humidity": 45.2,
    "pressure": 1013.25,
    "lux": 48200.0,
    "rain_raw": 3850,
    "rain_detected": false,
    "pan": 90,
    "tilt": 45,
    "state": "OBSERVE",
    "health": 100,
    "wifi_rssi": -62,
    "camera_online": true,
    "camera_ip": "192.168.1.120",
    "sensor_status": {
      "dht22": true,
      "bh1750": true,
      "bmp280": true,
      "rain": true
    },
    "firmware_version": "1.0.0"
  }
}
```

##### B. `ai_state` (Cognitive Decision & Explainability)
Provided by Agent 8 (Cognitive Decision Engine), Agent 6 (Environment AI), and Agent 7 (Sensor Fusion & Health):
```json
{
  "channel": "ai_state",
  "data": {
    "decision": "OBSERVE",
    "confidence": 0.94,
    "ors_score": 88,
    "ors_factors": {
      "solar_elevation": 92,
      "atmospheric_seeing": 85,
      "cloud_transparency": 90,
      "sensor_health": 100,
      "tracking_stability": 95
    },
    "reasoning_trace": [
      "Solar disk clearly resolved with 0% cloud occlusion",
      "Ambient humidity (45.2%) stable within optical safety envelope (<75%)",
      "Illuminance (48,200 Lux) confirms direct line-of-sight solar irradiance",
      "All sensor plausibility tests passing at 100% confidence"
    ],
    "predictions": {
      "horizon_15m": { "score": 86, "trend": "STABLE", "confidence_lower": 81, "confidence_upper": 91 },
      "horizon_30m": { "score": 82, "trend": "SLIGHT_DECLINE", "confidence_lower": 74, "confidence_upper": 88 },
      "horizon_60m": { "score": 75, "trend": "UNCERTAIN", "confidence_lower": 62, "confidence_upper": 85 }
    },
    "health_breakdown": {
      "overall": 98,
      "edge": 100,
      "optical": 95,
      "comms": 99,
      "anomaly_score": 0.04
    }
  }
}
```

##### C. `vision` (Solar Disk & Feature Analysis)
Provided by Agent 5 (Computer Vision & Solar Intelligence):
```json
{
  "channel": "vision",
  "data": {
    "timestamp": "2026-09-13T11:20:00Z",
    "image_url": "/api/v1/vision/latest.jpg",
    "disk_detected": true,
    "center_x": 320,
    "center_y": 240,
    "radius_px": 142,
    "limb_darkening_coeff": 0.58,
    "sunspots": [
      { "id": "AR3664-A", "x": 310, "y": 225, "area_px": 48, "intensity_ratio": 0.72 },
      { "id": "AR3664-B", "x": 340, "y": 255, "area_px": 32, "intensity_ratio": 0.78 }
    ],
    "cloud_occlusion_percent": 0.0,
    "sharpness_score": 88.5,
    "contrast_score": 92.1
  }
}
```

##### D. `alerts` (Anomaly & Safety Events)
```json
{
  "channel": "alerts",
  "data": {
    "alert_id": "alt-20260913-042",
    "severity": "CRITICAL",
    "type": "RAIN_EMERGENCY_OVERRIDE",
    "message": "Precipitation sensor triggered (ADC 1420). Hardware auto-stowed to (90, 0). State forced to SUSPEND.",
    "timestamp": "2026-09-13T11:21:04Z",
    "acknowledged": false
  }
}
```

---

## 3. REST API Endpoints

### Base URL: `/api/v1`

| Method | Endpoint | Description | Consumed Schema |
|---|---|---|---|
| `GET` | `/api/v1/system/status` | Current aggregate system and observatory state | Aggregated state object |
| `GET` | `/api/v1/telemetry/live` | Latest single telemetry snapshot | `SensorTelemetry.json` |
| `GET` | `/api/v1/telemetry/history` | Historical time series (`?range=15m\|1h\|6h\|24h`) | Array of `SensorTelemetry` |
| `GET` | `/api/v1/vision/latest` | Latest processed solar image metadata & URL | Solar vision metadata |
| `GET` | `/api/v1/intelligence/decision` | Current AI decision, confidence & reasoning trace | AI state object |
| `GET` | `/api/v1/intelligence/prediction` | Multi-horizon 15/30/60m prediction envelope | Prediction object |
| `GET` | `/api/v1/mission/active` | Active mission plan, target & schedule timeline | Mission status |
| `GET` | `/api/v1/replay/sessions` | List of recorded mission sessions available for replay | Session index |
| `GET` | `/api/v1/replay/{session_id}` | Full recorded stream for session replay scrubber | Time-indexed replay frame array |
| `POST` | `/api/v1/device/command` | Dispatch command to ESP32 Edge | `Command.json` $\to$ `CommandResult.json` |
| `POST` | `/api/v1/alerts/{alert_id}/ack`| Acknowledge an anomaly alert | `{ "status": "ACKNOWLEDGED" }` |

---

## 4. Command Dispatch Interface

Commands dispatched by the dashboard adhere strictly to `docs/contracts/Command.json`.

```json
{
  "command_id": "cmd-20260913-001",
  "command": "OBSERVE",
  "pan": 90,
  "tilt": 82,
  "speed": 100,
  "timestamp": "2026-09-13T11:20:00Z"
}
```

Backend responses return immediately with `docs/contracts/CommandResult.json`:
```json
{
  "command_id": "cmd-20260913-001",
  "status": "SUCCESS",
  "message": "Slew completed to (90, 82). State changed to OBSERVE.",
  "current_pan": 90,
  "current_tilt": 82,
  "current_state": "OBSERVE",
  "timestamp": "2026-09-13T11:20:01Z"
}
```
