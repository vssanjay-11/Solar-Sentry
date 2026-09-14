# Solar Sentry — Multi-Agent Coordination Tracker

*Last Updated: 2026-09-13*

This document tracks module ownership, interface contracts, implementation status, and dependencies across all 10 specialized agents working on the **Solar Sentry** project.

---

## Agent Status Summary Matrix

| Agent | Module Domain | Status | Key Interfaces / Artifacts | Dependencies |
|---|---|---|---|---|
| **Agent 1** | Edge Device + ESP32 Integration | **COMPLETED** | `firmware/esp32/`, `firmware/esp32_cam/`, `firmware/mock_edge/`, `docs/hardware/hardware-contract.md` | None (Physical Foundation) |
| **Agent 2** | Backend API + Communication | PENDING | REST / WebSocket / Ingestion endpoints | Agent 1 Telemetry & Command contracts |
| **Agent 3** | Database + Data Layer | **COMPLETED** | `backend/database/`, `backend/database/migrations/`, `docs/contracts/DatabaseContracts.md` | Agent 1 & 2 Data models |
| **Agent 4** | Dashboard + Frontend | **COMPLETED** | `frontend/`, `docs/contracts/FRONTEND_API_DEPENDENCIES.md` | Agent 2 API, Agent 8/9 state |
| **Agent 5** | Computer Vision + Solar Intelligence | **COMPLETED** | `ai/vision/`, `docs/contracts/VisionResult.json`, `docs/vision/algorithms_and_limitations.md` | Agent 1/CAM image streams, Observatory feeds |
| **Agent 6** | Environment AI + Observation Prediction | **COMPLETED** | `ai/environment/`, `docs/contracts/ObservationQualityPrediction.json`, `ai/environment/README.md` | Agent 1 Telemetry & Database |
| **Agent 7** | Sensor Fusion + Health + Anomaly AI | **COMPLETED** | `ai/health/`, `docs/contracts/ObservatoryHealthReport.json` | Agent 1 Telemetry & Health status |
| **Agent 8** | Cognitive Decision Engine + Explainable AI | **COMPLETED** | `ai/decision/`, `docs/contracts/CognitiveDecision.json` | Agent 5, 6, 7 evaluations, Agent 1/2 Telemetry |
| **Agent 9** | Mission Planner + Active Perception | **COMPLETED** | `mission/`, `docs/contracts/MissionPlan.json`, `docs/contracts/MissionResult.json` | Agent 1 Commands, Agent 8 Decisions |
| **Agent 10** | Digital Twin + Learning + Integration | PENDING | What-if simulation, continual learning | All agents |

---

## Detailed Agent Status Reports


### Agent 1: Edge Device + ESP32 Integration
- **Agent**: Agent 1
- **Module**: Edge Device / ESP32 Firmware & Hardware Integration
- **Status**: `COMPLETED`
- **Implemented**:
  - Production-grade modular ESP32 firmware (`firmware/esp32/`) with PlatformIO configuration.
  - Sensor acquisition for DHT22 (GPIO4), BH1750 (I2C GPIO21/22), BMP280 (I2C GPIO21/22), Rain Sensor (GPIO34).
  - Sensor sanity and plausibility validation routines with status flags.
  - Pan/Tilt servo control subsystem (GPIO18 Pan, GPIO19 Tilt) with software limits (0–180 deg), velocity limiting, and stow/safe positioning.
  - 3-LED status indicator subsystem (Green GPIO25, Yellow GPIO26, Red GPIO27) with heartbeat and error blinking patterns.
  - Local safety state machine (`BOOT`, `SELF_CHECK`, `STANDBY`, `OBSERVE`, `WAIT`, `SUSPEND`, `SAFE`, `FAULT`, `DEGRADED`).
  - Emergency local fail-safe overrides (Rain detection -> immediate stow & `SUSPEND`; comms timeout -> `SAFE` position).
  - Non-blocking cooperative tasks with Hardware Watchdog Timer (ESP32 WDT) protection.
  - Wi-Fi manager with exponential backoff auto-reconnect.
  - Outbound telemetry formatting (JSON over HTTP REST POST).
  - Inbound command parser and executor (JSON commands: `OBSERVE`, `PARK`, `SCAN`, `SET_SERVO`, `REBOOT`, `CALIBRATE`, `SET_EMERGENCY`).
  - ESP32-CAM network abstraction and companion camera node (`firmware/esp32_cam/`).
  - Python-based Edge Device Simulator (`firmware/mock_edge/edge_simulator.py`) for offline hardware-in-the-loop simulation and automated testing.
- **Files Created**:
  - `firmware/esp32/platformio.ini`
  - `firmware/esp32/include/config.h`
  - `firmware/esp32/include/types.h`
  - `firmware/esp32/src/sensors/SensorManager.h` & `SensorManager.cpp`
  - `firmware/esp32/src/actuators/ActuatorManager.h` & `ActuatorManager.cpp`
  - `firmware/esp32/src/safety/SafetyMonitor.h` & `SafetyMonitor.cpp`
  - `firmware/esp32/src/comms/NetworkManager.h` & `NetworkManager.cpp`
  - `firmware/esp32/src/comms/BackendClient.h` & `BackendClient.cpp`
  - `firmware/esp32/src/comms/CameraBridge.h` & `CameraBridge.cpp`
  - `firmware/esp32/src/main.cpp`
  - `firmware/esp32_cam/platformio.ini`
  - `firmware/esp32_cam/src/main.cpp`
  - `firmware/mock_edge/edge_simulator.py`
  - `tests/unit/test_edge_firmware.py`
  - `docs/hardware/hardware-contract.md`
  - `docs/contracts/SensorTelemetry.json`
  - `docs/contracts/Command.json`
  - `docs/contracts/CommandResult.json`
  - `docs/contracts/system-state.md`
  - `docs/MASTER_ARCHITECTURE.md`
- **Interfaces Exposed**:
  - Telemetry payload: POST `/api/v1/telemetry` (schema: `docs/contracts/SensorTelemetry.json`)
  - Command execution endpoint: POST `/api/v1/device/command` (schema: `docs/contracts/Command.json`)
  - ESP32 local HTTP status/command server: `GET /status`, `POST /command`
  - ESP32-CAM HTTP endpoints: `GET /capture`, `GET /status`
- **Dependencies**:
  - Consumed by Agent 2 (Backend API), Agent 3 (Database storage), Agent 7 (Sensor Fusion & Health), Agent 9 (Mission Planner).
- **Known Limitations**:
  - Physical servo movement delay requires a minimum settling time (500 ms) before triggering precision optical captures.
  - Rain sensor on GPIO34 is an analog-only input pin (ADC1) without internal pullup; calibrated threshold is set in `config.h`.
- **Tests**:
  - `pytest tests/unit/test_edge_firmware.py` validates telemetry serialization, state transitions, rain emergency triggers, command execution, and simulator protocol compatibility.

---

### Agent 3: Database + Data Persistence Layer
- **Agent**: Agent 3
- **Module**: Database & Persistence Layer (`backend/database/`)
- **Status**: `COMPLETED`
- **Implemented**:
  - Dual-engine database architecture: PostgreSQL for production; SQLite with automatic WAL mode and foreign-key enforcement for local/testing.
  - Declarative SQLAlchemy 2.0 ORM base with custom portable decorators: `PortableJSON` (PostgreSQL `JSONB` / SQLite JSON) and `UTCDateTime`.
  - Normalized schema across 17 tables representing all 21 system domains:
    - `devices`: Hardware controller & camera registry, heartbeat timestamps, and configuration JSON.
    - `sensors`: Physical sensor attachments (DHT22, BMP280, BH1750, RAIN, CAM), bus types, pins, and calibration parameters.
    - `telemetry_records`: High-throughput time-series sensor telemetry, compound indexes `(device_id, timestamp)` and `(timestamp, state)`.
    - `image_metadata`: Optical solar disk frames, dimensions, formats, exposure times, pan/tilt angles, and SHA-256 checksums.
    - `observations`: Scientific pointing sessions, solar elevation/azimuth, ambient lux, cloud cover, and quality scores.
    - `vision_analyses`: Solar disk detection, center/radius, sunspot counts, limb darkening, and cloud obstruction.
    - `environment_predictions`: Multi-horizon (15/30/60m) observation quality forecasts, rain probability, confidence, and risk factors.
    - `health_records`: Subsystem diagnostic health evaluations (power, thermal, actuator, comms, sensor breakdown).
    - `anomaly_events`: Isolation Forest & statistical anomalies, subsystem sources, severity tiers, and resolution status.
    - `decision_records`: Authoritative cognitive decisions, confidence, risk levels, and explainable AI (XAI) reasoning traces.
    - `missions`: High-level active perception campaigns, priorities, target coordinates, and execution states.
    - `mission_actions`: Discrete action sequence steps (SLEW, CAPTURE, CALIBRATE, DWELL, VERIFY), pan/tilt targets, and execution status.
    - `mission_memories`: Episodic and continual learning memory records tagged by context (e.g. SOLAR_CYCLE, CLOUD_DYNAMICS).
    - `commands`: Dispatched edge control verbs adhering to `docs/contracts/Command.json`.
    - `command_results`: Edge execution confirmations adhering to `docs/contracts/CommandResult.json`.
    - `verification_records`: Closed-loop verification records tracking pointing errors, optical confirmation, delta quality, and convergence.
    - `model_versions`: Registry of AI models (vision, forecasting, anomaly, decision), version tags, weights paths, and metrics.
  - Clean Repository/Data-Access Layer (`backend/database/repositories/`) providing domain-specific queries without duplicating business logic:
    - High-performance range queries and time-window aggregations (`TelemetryRepository.get_aggregate_summary()`).
    - Device heartbeat and status tracking (`DeviceRepository.update_last_seen()`).
    - Unconfirmed command tracking and execution verification (`CommandRepository.list_unconfirmed()`).
    - Anomaly lifecycle tracking (`AnomalyRepository.resolve_anomaly()`).
    - Atomic model version switching (`ModelVersionRepository.set_active_version()`).
  - Deterministic migration system (`backend/database/migrations/runner.py`) executing ANSI/PostgreSQL/SQLite compatible SQL DDL (`001_initial_schema.sql`) and tracking checksums in `schema_migrations`.
- **Files Created**:
  - `backend/__init__.py`
  - `backend/database/__init__.py`
  - `backend/database/config.py`
  - `backend/database/core.py`
  - `backend/database/models/__init__.py`
  - `backend/database/models/device.py`
  - `backend/database/models/telemetry.py`
  - `backend/database/models/image.py`
  - `backend/database/models/observation.py`
  - `backend/database/models/vision.py`
  - `backend/database/models/prediction.py`
  - `backend/database/models/health.py`
  - `backend/database/models/decision.py`
  - `backend/database/models/mission.py`
  - `backend/database/models/command.py`
  - `backend/database/models/verification.py`
  - `backend/database/models/model_version.py`
  - `backend/database/repositories/__init__.py`
  - `backend/database/repositories/base.py`
  - `backend/database/repositories/device_repo.py`
  - `backend/database/repositories/telemetry_repo.py`
  - `backend/database/repositories/observation_repo.py`
  - `backend/database/repositories/vision_repo.py`
  - `backend/database/repositories/prediction_repo.py`
  - `backend/database/repositories/health_repo.py`
  - `backend/database/repositories/decision_repo.py`
  - `backend/database/repositories/mission_repo.py`
  - `backend/database/repositories/command_repo.py`
  - `backend/database/repositories/verification_repo.py`
  - `backend/database/repositories/model_repo.py`
  - `backend/database/migrations/__init__.py`
  - `backend/database/migrations/runner.py`
  - `backend/database/migrations/versions/001_initial_schema.sql`
  - `docs/contracts/DatabaseContracts.md`
  - `tests/unit/test_database_config.py`
  - `tests/unit/test_models.py`
  - `tests/unit/test_repositories.py`
  - `tests/unit/test_migrations.py`
- **Interfaces Exposed**:
  - Engine & Session dependency: `get_db()`, `get_db_session()`, `get_engine()`, `init_db()`
  - Repository classes: `DeviceRepository`, `SensorRepository`, `TelemetryRepository`, `ObservationRepository`, `ImageRepository`, `VisionAnalysisRepository`, `EnvironmentPredictionRepository`, `HealthRepository`, `AnomalyRepository`, `DecisionRepository`, `MissionRepository`, `MissionActionRepository`, `MissionMemoryRepository`, `CommandRepository`, `VerificationRepository`, `ModelVersionRepository`
  - Migration CLI & API: `python -m backend.database.migrations.runner`, `apply_migrations()`, `get_migration_status()`
- **Dependencies**:
  - Consumed by: Agent 2 (FastAPI routes & WebSocket streaming), Agent 4 (Observatory Dashboard persistence queries), Agent 5 (Solar image analysis storage), Agent 6 (Forecasting history and predictions), Agent 7 (Health and anomaly event persistence), Agent 8 (Decision reasoning traces), Agent 9 (Mission planner sequences & verification records), Agent 10 (Episodic mission memory & simulation models).
  - Depends on: Agent 1 hardware telemetry contracts (`SensorTelemetry.json`, `Command.json`, `CommandResult.json`).
- **Tests**:
  - 16 comprehensive unit tests in `tests/unit/test_database_config.py`, `tests/unit/test_models.py`, `tests/unit/test_repositories.py`, and `tests/unit/test_migrations.py` validating configuration, connection pooling, SQLite PRAGMA enforcement, model relationships, time-series querying, aggregations, migration tracking, and idempotency.


---

### Agent 4: Observatory Dashboard + Frontend (Mission Control)
- **Agent**: Agent 4
- **Module**: Mission-Control Observatory Dashboard & Frontend Interface (`frontend/`)
- **Status**: `COMPLETED`
- **Implemented**:
  - Production-grade mission-control web application built with **React 19 + TypeScript + Vite** and pure **Vanilla CSS** design system (zero bloated framework dependencies).
  - High-density dark scientific visual aesthetic: JetBrains Mono and Inter typography, subtle gridlines, HUD corner brackets, glowing vector accents, and multi-monitor responsive dock layouts.
  - All 24 core capabilities fully operational:
    1. **Main Observatory Dashboard**: Multi-tier ops deck dividing operations into Mission Ops, Health & Diagnostics, Cognitive AI & Predictions, and Session Replay & Audit Log.
    2. **Live System State Panel**: Real-time state machine displaying all 10 authoritative states (`BOOT`, `SELF_CHECK`, `STANDBY`, `OBSERVE`, `WAIT`, `SCAN`, `SUSPEND`, `FAULT`, `SAFE`, `DEGRADED`).
    3. **Observation Readiness Score (ORS)**: Circular SVG gauge (0–100%) with color thresholds and 5-factor radar breakdown (Solar Elevation, Atmospheric Seeing, Cloud Transparency, Sensor Health, Tracking Stability).
    4. **Microclimate Environment Panel**: Precision readouts for Temperature (°C), Relative Humidity (%), Barometric Pressure (hPa), Illuminance (Lux), and Rain Sensor 12-bit ADC raw levels (0–4095).
    5. **Sensor Bus Health Matrix**: Status matrix for DHT22 (GPIO4), BH1750 (I2C 21/22), BMP280 (I2C 0x76), Rain Sensor (GPIO34 ADC1), and ESP32-CAM HTTP bridge with Wi-Fi RSSI indicator.
    6. **Observatory Health Panel**: Subsystem composite scores (Hardware, Optics, Network) and Isolation Forest anomaly score readout (0.00–1.00).
    7. **Anomaly & Safety Alerts**: Real-time alert notifications with severity categorization (`CRITICAL`, `WARNING`, `INFO`), source attribution (`EDGE`, `AI_FUSION`, `VISION`, `COMMS`), and interactive acknowledgment actions.
    8. **Solar Optical Viewport**: Live ESP32-CAM camera frame canvas with sub-pixel solar disk crosshairs, limb darkening profile, NOAA active sunspot region bounding boxes (`AR3664-A/B`), and optical telemetry (sharpness, contrast, exposure).
    9. **Solar Analysis Panel**: Photometric extraction reporting disk center $(x, y)$, normalized radius $r$, limb darkening index $\mu = 0.62$, active region area, and cloud occlusion %.
    10. **Multi-Horizon Predictive Forecast**: 15m, 30m, and 60m observation quality forecasting with probabilistic confidence interval envelopes and trend vector icons.
    11. **Cognitive Decision Engine Panel**: Authoritative state recommendations (`OBSERVE`, `WAIT`, `SUSPEND`, `SAFE`, `SCAN`), epistemic uncertainty visualization, and concise "WHY" explainability bullet points.
    12. **Mission Control Panel**: Active mission target ephemeris (Azimuth, Elevation), tracking error angle, and direct command triggers (`OBSERVE SUN`, `RASTER SCAN`, `PARK / STOW`).
    13. **Mission Timeline Panel**: Gantt-style chronological mission pipeline tracking Calibration, Slew, Tracking, Verification, and Stow phases with execution state tags.
    14. **Digital Twin Visualization**: Interactive 3D Canvas rendering of the dual-axis tracker gimbal showing turntable pan ($0-180^\circ$), fork elevation tilt ($0-180^\circ$), optical tube boresight ray, and sun vector alignment.
    15. **Historical Telemetry Graphs**: Multi-stream SVG time-series charts with metric selection (ORS, Temp, Humidity, Lux, Pan) and horizon filters (15m, 1h, 6h, 24h).
    16. **Session Replay Engine**: Scrubbable historical timeline player with Play/Pause, speed multipliers (1x, 2x, 5x, 10x), and synchronized frame playback across telemetry, twin pose, camera viewport, and AI decisions.
    17. **Observatory Event Stream**: Filterable terminal audit log supporting `ALL`, `INFO`, `WARN`, `ERROR`, `SAFETY`, `AI` filters and full search text query.
    18. **Manual Actuator Flight Deck**: Precision jog D-pad, dual-slider pan/tilt angle slewing with software limits ($0-180^\circ$), and `CommandResult.json` status confirmation.
    19. **Simulation Mode & Scenario Engine**: Offline simulation engine with 5 realistic operational scenarios:
       - *Scenario 1: Clear Sky Optimal Tracking* (Nominal high-ORS tracking)
       - *Scenario 2: Cloud Transit & Quality Dip* (Fluctuating lux, state moves to `WAIT` with explainability)
       - *Scenario 3: Sudden Precipitation Alarm* (Rain ADC trips <2000, auto-stows to (90, 0), emergency `SUSPEND` state, critical banner)
       - *Scenario 4: Sensor Disagreement & Anomaly* (BMP280 vs DHT22 divergence, `DEGRADED` state)
       - *Scenario 5: Communication Loss Failsafe* (30s heartbeat timeout, auto-parks to `SAFE`)
    20. **Responsive Layout**: Fluid CSS Grid and Flexbox dashboard scaling across 4K displays, 1080p workstations, and tablets.
    21. **Dark Scientific/Mission-Control Visual Language**: Curated deep space palette (`#05080e`, `#090e18`), laser green `#00ff9d`, cyan `#00e5ff`, solar gold `#ffaa00`, warning amber `#ffb700`, crimson `#ff2a5f`.
    22. **Status LED Mimicry**: Edge LED mimics (Green GPIO25, Yellow GPIO26, Red GPIO27) reflecting actual hardware GPIO states.
    23. **Confidence Indicators**: Probabilistic error bars and explicit epistemic uncertainty displays.
    24. **Deep-Dive Explainable AI Modal**: Modal showing SHAP/saliency feature weights and operational safety threshold deltas.
- **Files Created**:
  - `frontend/index.html`
  - `frontend/package.json`
  - `frontend/tsconfig.json` & `frontend/tsconfig.app.json`
  - `frontend/vite.config.ts`
  - `frontend/public/favicon.svg`
  - `frontend/src/main.tsx`
  - `frontend/src/App.tsx`
  - `frontend/src/styles/design-tokens.css`
  - `frontend/src/styles/app.css`
  - `frontend/src/types/telemetry.ts`
  - `frontend/src/types/command.ts`
  - `frontend/src/types/intelligence.ts`
  - `frontend/src/types/mission.ts`
  - `frontend/src/types/alerts.ts`
  - `frontend/src/services/api.ts`
  - `frontend/src/services/websocket.ts`
  - `frontend/src/services/simulator.ts`
  - `frontend/src/context/ObservatoryContext.tsx`
  - `frontend/src/components/header/Header.tsx`
  - `frontend/src/components/panels/SystemStatePanel.tsx`
  - `frontend/src/components/panels/ReadinessGaugePanel.tsx`
  - `frontend/src/components/panels/EnvironmentPanel.tsx`
  - `frontend/src/components/panels/SensorHealthPanel.tsx`
  - `frontend/src/components/panels/ObservatoryHealthPanel.tsx`
  - `frontend/src/components/panels/AnomalyAlertsPanel.tsx`
  - `frontend/src/components/panels/SolarVisionPanel.tsx`
  - `frontend/src/components/panels/SolarAnalysisPanel.tsx`
  - `frontend/src/components/panels/PredictionPanel.tsx`
  - `frontend/src/components/panels/AIDecisionPanel.tsx`
  - `frontend/src/components/panels/MissionControlPanel.tsx`
  - `frontend/src/components/panels/MissionTimelinePanel.tsx`
  - `frontend/src/components/panels/DigitalTwinPanel.tsx`
  - `frontend/src/components/panels/TelemetryGraphPanel.tsx`
  - `frontend/src/components/panels/MissionReplayPanel.tsx`
  - `frontend/src/components/panels/EventLogPanel.tsx`
  - `frontend/src/components/panels/CommandControlPanel.tsx`
  - `frontend/src/components/panels/ExplainableAIModal.tsx`
  - `frontend/src/tests/simulator.test.ts`
  - `frontend/src/tests/contracts.test.ts`
  - `docs/contracts/FRONTEND_API_DEPENDENCIES.md`
- **Interfaces Exposed**:
  - Web UI: Available on port 5173 (`http://localhost:5173/`)
  - Integration Contract: `docs/contracts/FRONTEND_API_DEPENDENCIES.md` documenting all required REST endpoints, WebSocket streaming channels, and JSON payload schemas.
- **Dependencies**:
  - Consumes: Agent 1 edge telemetry schemas, Agent 2 REST & WebSocket endpoints, Agent 3 telemetry history, Agent 5 vision analysis, Agent 6 environmental quality predictions, Agent 7 health evaluations, Agent 8 cognitive decisions, Agent 9 mission schedules.
- **Tests**:
  - `npm test`: 9 automated Vitest unit tests in `frontend/src/tests/simulator.test.ts` and `frontend/src/tests/contracts.test.ts` passing with 100% success rate.
  - Production build: `npm run build` compiling with 0 errors.
  - Interactive Browser Automation: Verified end-to-end via `browser_subagent` recording all screens, scenario switches, modal workflows, canvas twin, and replay scrubbers.

---

### Agent 5: Computer Vision + Solar Image Intelligence
- **Agent**: Agent 5
- **Module**: Computer Vision + Solar Image Intelligence (`ai/vision/`)
- **Status**: `COMPLETED`
- **Implemented**:
  - Image ingestion abstraction supporting heterogeneous sources: `ESP32_CAM` (OV2640 environmental prototype), `UPLOAD`, `HISTORICAL`, `OBSERVATORY`, `SIMULATION`, with support for NumPy arrays, bytes, file paths, and base64 strings.
  - Image preprocessing: Bilateral edge-preserving smoothing, CLAHE contrast enhancement, and radial vignetting compensation tailored for low-cost CMOS lenses.
  - Optical quality assessment: Sharpness via Modified Laplacian variance and Tenengrad gradient energy density; exposure analysis with black and white saturation clipping; RMS luminance contrast; high-frequency noise estimation via Donoho-Johnstone Median Absolute Deviation (MAD); composite quality index (0.0–1.0) and categorical ratings (`EXCELLENT`, `USABLE`, `DEGRADED`, `UNUSABLE`).
  - Solar disk localization: Multi-threshold contour morphology, enclosing circle fitting, circularity index ($\mathcal{C} = 4\pi A / P^2$), frame margin clipping detection, and Eddington-Barbier astrophysical limb darkening profile verification ($I(r)/I(0) \approx 1 - u(1 - \sqrt{1 - (r/R)^2})$).
  - Solar region extraction: Cropped circular masked ROI generation for quiet photosphere analysis.
  - Sunspot detection and solar feature segmentation: Quiet photosphere background gradient modeling, relative contrast thresholding ($\ge 12\%$), Umbra (core $\ge 35\%$) and Penumbra (halo) decomposition, disk-relative polar coordinates ($r \in [0, 1], \theta \in [0, 360^\circ]$), pixel footprint area, and sensor dust/fiber rejection.
  - Cloud and visual obstruction detection: Solar perimeter limb integrity profiling, off-disk sky scattering entropy and gradient variance, glare bloom detection, and visual obstruction index (0.0=clear, 1.0=fully obstructed) with categorical classification (`CLEAR`, `PARTIAL_CLOUD`, `HEAVY_CLOUD`, `OVEREXPOSURE_GLARE`, `OFF_TARGET`).
  - Temporal image comparison: Sub-pixel Fourier phase correlation registration compensating for mechanical pan/tilt tracking jitter, masked differential photometry change scoring, and transient feature emergence tracking.
  - Batch and historical sequence processing: Iterative processing with consecutive frame linking for temporal change tracking.
  - Test mode & synthetic solar image generator: Photorealistic synthetic solar image generator supporting 8 operational presets (`clear_with_sunspots`, `quiet_sun`, `cloudy`, `overexposed`, `underexposed`, `blurry`, `esp32_cam_noisy`, `off_target`).
  - Comprehensive documentation of mathematical algorithms, hardware trade-offs (ESP32-CAM OV2640 vs observatory instruments), and optical limitations (`docs/vision/algorithms_and_limitations.md`).
  - Formal JSON schema contract (`docs/contracts/VisionResult.json`) with Pydantic serialization (`VisionResult.to_json()`, `VisionResult.to_dict()`).
  - Mandatory scientific disclaimer: Explicitly disclaims solar flare prediction to uphold astrophysical scientific integrity.
- **Files Created**:
  - `ai/vision/__init__.py`
  - `ai/vision/models.py`
  - `ai/vision/ingestion.py`
  - `ai/vision/preprocessor.py`
  - `ai/vision/quality.py`
  - `ai/vision/solar_disk.py`
  - `ai/vision/sunspot.py`
  - `ai/vision/obstruction.py`
  - `ai/vision/temporal.py`
  - `ai/vision/pipeline.py`
  - `docs/contracts/VisionResult.json`
  - `docs/vision/algorithms_and_limitations.md`
  - `tests/unit/test_vision_pipeline.py`
- **Interfaces Exposed**:
  - `analyze_image(image_input, source_type=..., reference_image=..., ...) -> VisionResult`
  - `batch_analyze(images, source_type=...) -> List[VisionResult]`
  - `analyze_sequence(sequence, source_type=...) -> List[VisionResult]`
  - `generate_synthetic_solar_image(...) -> np.ndarray`
- **Dependencies**:
  - Consumes: ESP32-CAM prototype snapshot (`firmware/esp32_cam/`), uploaded image buffers, observatory feeds, historical archives.
  - Consumed by: Agent 8 (`ai/decision/` cognitive decision engine), Agent 9 (`mission/` active perception & closed-loop verification), Agent 4 (`frontend/` solar disk & sunspot visualization), Agent 2/3 (storage/API).
  - Explicit non-ownership: Observation readiness prediction (Agent 6); Hardware servo control (Agent 1); Solar flare prediction (strictly disclaimed).
- **Tests**:
  - `pytest tests/unit/test_vision_pipeline.py -v` (22 test cases covering synthetic generator, ingestion variants, blur/exposure/noise quality metrics, solar disk detection, sunspot detection/segmentation, obstruction analysis, temporal phase correlation registration, batch/sequence processing, contract compliance, and mandatory disclaimer enforcement).

---

### Agent 6: Environment AI + Observation Prediction
- **Agent**: Agent 6
- **Module**: Environment Intelligence & Observation Quality Prediction (`ai/environment/`)
- **Status**: `COMPLETED`
- **Implemented**:
  - Domain-specific meteorological and solar physical feature engineering (`ai/environment/features.py`):
    - NOAA astronomical solar position calculation (solar elevation and zenith angles).
    - Theoretical clear-sky illuminance benchmark ($I_{\text{clear}}$) with Kasten-Young atmospheric airmass extinction.
    - Clearness index ($k_t$) scaling relative to theoretical clear-sky irradiance.
    - Magnus-Tetens psychrometric dew point calculation and dew point depression ($\Delta T = T - T_{\text{dew}}$) for optical lens condensation hazard warning.
    - Thermal seeing / atmospheric turbulence index estimating solar surface heating convection ("boiling").
    - Multi-factor precipitation imminence index predicting pre-rain conditions from rapid pressure drops, humidity saturation, and daylight attenuation before physical sensor wetting.
  - Multi-horizon observation quality forecasting (Current, 15-minute, 30-minute, 60-minute):
    - Model abstraction interface (`ObservationQualityModel`) supporting model versioning and standardized evaluation metrics.
    - **Physics-Informed Rule-Based Baseline Model (`1.0.0-physics-baseline`)**: Operates cold-start with zero historical training data, extrapolating solar elevation progression, pressure trends, and condensation dynamics.
    - **Scikit-Learn Machine Learning Regressor (`1.1.0-gb-predictor`)**: Multi-target `HistGradientBoostingRegressor` trained on synthetic simulation datasets with serialization and automatic fallback to physics baseline.
  - Environmental threat and risk level classification (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`) with explicit risk factor tagging (`RAIN_DETECTED`, `PRECIPITATION_IMMINENT`, `CONDENSATION_RISK`, `HIGH_HUMIDITY`, `RAPID_CLOUD_DEVELOPMENT`, `ATMOSPHERIC_TURBULENCE`, `LOW_SOLAR_ALTITUDE`, `NIGHT_TIME`, `SENSOR_DEGRADED`).
  - Prediction confidence scoring ($C \in [0.0, 1.0]$) accounting for sensor degradation, microclimate volatility, history depth, and forecast horizon uncertainty.
  - Historical trend analysis with rolling buffer (`TelemetryHistoryBuffer`) computing rates of change ($d(\text{lux})/dt$, $dP/dt$, $d(RH)/dt$, $dT/dt$) and qualitative trend labels (`RISING`, `FALLING`, `STEADY`, `VOLATILE`).
  - Synthetic Environmental Simulator (`EnvironmentalSimulator`) generating multi-scenario meteorological streams (`CLEAR_DAY`, `AFTERNOON_CLOUDS`, `THUNDERSTORM_SQUALL`, `MORNING_CONDENSATION`, `THERMAL_TURBULENCE`).
  - Automated evaluation harness computing MAE, RMSE, Pearson Correlation, and Directional Trend Accuracy across all forecast horizons.
  - Clean public interface `predict_observation_quality(state, history, vision_hints, horizons)` returning strict JSON contract payload.
- **Files Created**:
  - `ai/environment/__init__.py`
  - `ai/environment/config.py`
  - `ai/environment/schemas.py`
  - `ai/environment/features.py`
  - `ai/environment/trends.py`
  - `ai/environment/assessor.py`
  - `ai/environment/predictor.py`
  - `ai/environment/simulator.py`
  - `ai/environment/evaluation.py`
  - `ai/environment/models/__init__.py`
  - `ai/environment/models/base.py`
  - `ai/environment/models/physics_baseline.py`
  - `ai/environment/models/ml_model.py`
  - `ai/environment/README.md`
  - `docs/contracts/ObservationQualityPrediction.json`
  - `tests/unit/test_environment_ai.py`
- **Interfaces Exposed**:
  - Python API: `predict_observation_quality(state, history=None, vision_hints=None, horizons=(15, 30, 60), use_ml=False) -> Dict[str, Any]`
  - Schema Contract: `docs/contracts/ObservationQualityPrediction.json`
- **Dependencies**:
  - Consumes: Agent 1 / Agent 2 Telemetry (`SensorTelemetry.json`), Agent 5 Optional Vision Hints (`VisionHints`).
  - Consumed by: Agent 8 (`ai/decision/` Cognitive Decision Engine), Agent 9 (`mission/` Mission Planner), Agent 4 (`frontend/` Dashboard).
  - Explicit non-ownership: Image intelligence (Agent 5); Sensor hardware anomaly detection (Agent 7); Final cognitive decision (Agent 8); Mission planning (Agent 9).
- **Tests**:
  - `pytest tests/unit/test_environment_ai.py -v` (13 comprehensive tests validating solar geometry, psychrometrics, pre-rain index, trend analysis, quality scoring, rain emergency clamps, condensation risk, baseline & ML predictions, contract compliance, vision hint blending, sensor degradation impact, simulator, and serialization).

---

### Agent 8: Cognitive Decision Engine + Explainable AI (XAI)
- **Agent**: Agent 8
- **Module**: Cognitive Decision Engine & Explainable AI (`ai/decision/`)
- **Status**: `COMPLETED`
- **Implemented**:
  - Observatory cognitive state management (`NORMAL`, `DEGRADED`, `UNCERTAIN`, `SAFE_MODE`) with state history tracking and consecutive observation counting.
  - Multimodal decision fusion across Agent 5 (Vision Intelligence), Agent 6 (Environmental Forecasting), Agent 7 (Sensor Fusion & Health), and Agent 1/2 (Edge Telemetry).
  - Multi-Attribute Utility Theory (MAUT) + Bayesian Evidence fusion engine with trend sensitivity and adaptive weight re-normalization.
  - Hierarchical safety gating ($\text{SAFETY} > \text{HEALTH} > \text{DATA QUALITY} > \text{OBSERVATION QUALITY} > \text{MISSION OBJECTIVE}$).
  - Authoritative decisions: `OBSERVE`, `WAIT`, `SCAN`, `SUSPEND`, `SAFE`.
  - Calibrated confidence calculation ($C \in [0.0, 1.0]$) based on margin over threshold, model agreement, and inverse uncertainty.
  - Risk assessment categorization (`LOW`, `MODERATE`, `HIGH`, `CRITICAL`).
  - Epistemic and discordance uncertainty handling with threshold gating triggering conservative `UNCERTAIN` mode.
  - Degraded-mode support with non-critical sensor fault isolation (e.g. BMP280 offline) allowing continued guarded observation without system halt.
  - Explainable AI (XAI) engine generating clean, human-readable reasons (e.g. `["environment suitable", "sensor health normal", "image quality acceptable", "future conditions declining"]`).
  - Linear-additive feature attributions (positive drivers vs negative inhibitors) and actionable counterfactual scenario generation.
  - Step-by-step decision traces (`DecisionTrace`) auditing all evaluated rules, thresholds, and intermediate utility scores.
  - Structured output schema (`CognitiveDecision`) consumed by Agent 9 (Mission Planner) and Agent 4 (Observatory Dashboard).
- **Files Created**:
  - `ai/decision/__init__.py`
  - `ai/decision/types.py`
  - `ai/decision/engine.py`
  - `ai/decision/xai.py`
  - `docs/contracts/CognitiveDecision.json`
  - `tests/unit/test_cognitive_decision_engine.py`
  - `pytest.ini`
- **Interfaces Exposed**:
  - Python API: `CognitiveDecisionEngine.evaluate(input_data)` -> `CognitiveDecision`
  - Schema Contract: `docs/contracts/CognitiveDecision.json`
- **Dependencies**:
  - Consumes: Agent 5 (`VisionEvaluation`), Agent 6 (`EnvironmentPrediction`), Agent 7 (`HealthFusionEvaluation`), Agent 1/2 (`EdgeTelemetryState`).
  - Consumed by: Agent 9 (`Mission Planner`), Agent 4 (`Observatory Dashboard`).
- **Tests**:
  - `pytest tests/unit/test_cognitive_decision_engine.py -v` (12 test cases covering rain emergency override, comms timeout, critical sensor failure, degraded mode, conflicting sensors, high uncertainty, poor image cloud transit, optimal conditions, active solar search/scan recommendation, XAI explanations/counterfactuals, and memory reset).

---

### Agent 9: Autonomous Mission Planner + Active Perception
- **Agent**: Agent 9
- **Module**: Autonomous Mission Planner & Active Perception (`mission/`)
- **Status**: `COMPLETED`
- **Implemented**:
  - Mission definition and lifecycle state machine (`PENDING`, `PLANNING`, `EXECUTING`, `VERIFYING`, `COMPLETED`, `FAILED`, `ABORTED`, `SUSPENDED`).
  - Structured mission objectives with targets, thresholds, and success criteria (`MissionObjective`).
  - Priority-based mission queue and preemptive scheduler (`MissionScheduler`) supporting preemption of routine observations by emergency/safety directives.
  - Autonomous mission planning translating Agent 8 cognitive decisions (`OBSERVE`, `SCAN`, `WAIT`, `SUSPEND`, `SAFE`) into executable action sequences (`AutonomousMissionPlanner`).
  - Candidate region evaluation and multi-criteria ranking (`CandidateEvaluator`) balancing observation quality, epistemic certainty, and actuator displacement costs (e.g. `LEFT=0.61`, `CENTER=0.82`, `RIGHT=0.73` -> `SELECT CENTER` -> `pan=90, tilt=82`).
  - Active perception engine (`ActivePerceptionEvaluator`): selects exploratory scan actions to resolve elevated visual/forecast ambiguity rather than blindly following static scripts; measures epistemic information gain post-probe.
  - Spatial and parameter scan trajectory generator (`ScanPlanner`) for 3-point azimuth brackets (`LEFT`, `CENTER`, `RIGHT`), elevation sweeps, and raster grids.
  - Hardware command generation strictly conforming to `docs/contracts/Command.json` (`OBSERVE`, `PARK`, `SCAN`, `SET_SERVO`, `SET_STATE`, `EMERGENCY_STOP`).
  - Command dispatch abstraction layer (`CommandDispatcherInterface`) with production HTTP dispatch (`HttpCommandDispatcher`) and high-fidelity mock emulator integration (`SimulatedCommandDispatcher`).
  - Per-action watchdog timeouts preventing hang conditions.
  - Closed-loop action and mission verification (`ActionVerifier`): confirms physical actuator convergence ($\pm 2^\circ$) and measures pre- vs post-action quality delta (e.g. $0.71 \rightarrow 0.86$, $\Delta=+0.15 \rightarrow \text{SUCCESS}$).
  - Retry policy engine with automatic retries on transient edge glitches.
  - Comprehensive failure classification (`TIMEOUT`, `ACTUATOR_ERROR`, `QUALITY_DEGRADATION`, `SAFETY_INTERLOCK`, `RAIN_OVERRIDE`).
  - Safe recovery manager (`SafeRecoveryManager`): enforces absolute safety override (rain, thermal, comms loss immediately aborts mission and commands safe park `pan=90, tilt=0`), and verifies recovery checklist before transitioning back to `STANDBY`.
  - Rich audit-grade post-execution mission report generation (`MissionResult`) adhering to schema.
- **Files Created**:
  - `mission/__init__.py`
  - `mission/types.py`
  - `mission/candidate_evaluator.py`
  - `mission/active_perception.py`
  - `mission/scan_planner.py`
  - `mission/dispatcher.py`
  - `mission/verifier.py`
  - `mission/recovery.py`
  - `mission/planner.py`
  - `mission/executor.py`
  - `mission/scheduler.py`
  - `docs/contracts/MissionPlan.json`
  - `docs/contracts/MissionResult.json`
  - `tests/unit/test_mission_planner.py`
- **Interfaces Exposed**:
  - Python API: `AutonomousMissionPlanner`, `MissionExecutor`, `MissionScheduler`, `CandidateEvaluator`, `ActivePerceptionEvaluator`, `ActionVerifier`, `SafeRecoveryManager`
  - Schema Contracts: `docs/contracts/MissionPlan.json`, `docs/contracts/MissionResult.json`, `docs/contracts/Command.json`, `docs/contracts/CommandResult.json`
- **Dependencies**:
  - Consumes: Agent 8 decisions (`ai/decision/`), Agent 1 command contracts & mock edge emulator (`firmware/mock_edge/edge_simulator.py`).
  - Consumed by: Agent 2 (Backend API mission endpoints), Agent 4 (Observatory Dashboard mission view), Agent 10 (Digital Twin & Simulation replay).
- **Tests**:
  - `pytest tests/unit/test_mission_planner.py -v` (13 comprehensive tests validating candidate evaluation, successful mission execution, action timeout, action retry, degraded environment, emergency rain suspension, pre-execution safety trip, safe recovery flow, active perception uncertainty trigger & information gain, scheduler priority preemption, schema compliance, and Agent 8 decision integration).

