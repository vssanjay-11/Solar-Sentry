# Agent 6: Environment Intelligence & Observation Quality Prediction

**Module Ownership**: Agent 6 (`ai/environment/`)  
**Domain**: Meteorological Feature Engineering, Microclimate Stability, Environmental Risk Classification, and Multi-Horizon Solar Observation Quality Forecasting (15m, 30m, 60m).

---

## 1. Architectural Scope & Boundaries

Agent 6 strictly owns environmental feature extraction and quality prediction. It interfaces with:
- **Agent 1 / Backend**: Ingests `SensorTelemetry` (`temperature`, `humidity`, `pressure`, `lux`, `rain_raw`, `rain_detected`, `sensor_status`).
- **Agent 5 (Computer Vision)**: Ingests optional visual optical hints (`image_quality`, `cloud_cover`, `solar_disk_visible`) when camera captures are available.
- **Agent 8 (Cognitive Decision Engine)**: Consumes structured `ObservationQualityAssessment` outputs to make final system decisions (`OBSERVE`, `WAIT`, `SUSPEND`, `SAFE`).

---

## 2. Scientific & Meteorological Modeling

### 2.1 Astronomical Solar Geometry & Clear-Sky Model
Solar elevation $\theta_{\text{elev}}$ and zenith $\theta_{\text{zenith}}$ angles are computed using standard NOAA solar coordinates:
$$\cos(\theta_{\text{zenith}}) = \sin(\phi)\sin(\delta) + \cos(\phi)\cos(\delta)\cos(\omega)$$
The benchmark theoretical clear-sky illuminance is modeled via Kasten-Young airmass extinction:
$$I_{\text{clear}} = I_{\text{zenith}} \cdot \sin(\theta_{\text{elev}}) \cdot \exp\left(-0.14 \cdot \text{airmass}(\theta_{\text{elev}})\right)$$
The **Clearness Index ($k_t$)** is:
$$k_t = \frac{\text{lux}_{\text{measured}}}{I_{\text{clear}}}$$
- $k_t \approx 1.0$: Clean clear-sky direct solar disk observation.
- $k_t \in [0.4, 0.7]$: Thin cirrus or passing cumulus clouds.
- $k_t < 0.25$: Overcast cloud cover; solar disk obscured.

### 2.2 Psychrometric Condensation Threat
Dew point $T_{\text{dew}}$ is derived via the Magnus-Tetens formula ($a=17.27, b=237.7^\circ\text{C}$):
$$\alpha = \frac{a \cdot T}{b + T} + \ln\left(\frac{RH}{100}\right), \quad T_{\text{dew}} = \frac{b \cdot \alpha}{a - \alpha}$$
The **Dew Point Depression** $\Delta T = T_{\text{ambient}} - T_{\text{dew}}$:
- $\Delta T \le 1.5^\circ\text{C}$: `CRITICAL` lens fogging / condensation risk.
- $\Delta T \le 3.0^\circ\text{C}$: `HIGH` condensation warning.

### 2.3 Atmospheric Seeing & Thermal Turbulence
Solar surface heating generates convective turbulent plumes ("boiling"):
$$S_{\text{seeing}} = 1.0 - \left(0.25 \cdot \max(0, \frac{\theta_{\text{elev}} - 30^\circ}{60^\circ}) + 0.20 \cdot \max(0, \frac{T - 28^\circ\text{C}}{15^\circ\text{C}})\right)$$

### 2.4 Precipitation Imminence Index
Pre-rain indicator before physical sensor contact:
Combines relative humidity $RH > 85\%$, pressure drops $\Delta P / \Delta t < -1.5\text{ hPa/hr}$, and sudden daylight dimming.

---

## 3. Multi-Horizon Forecasting Models

### Model 1: Physics-Informed Rule-Based Baseline (`1.0.0-physics-baseline`)
- Operates out-of-the-box with **zero** prior training data.
- Directly propagates solar elevation trajectories forward $t + 15\text{m}, t + 30\text{m}, t + 60\text{m}$.
- Extrapolates pressure gradients, dew point convergence, and clearness persistence with exponential damping.

### Model 2: Gradient Boosting Regressor (`1.1.0-gb-predictor`)
- Implements scikit-learn `HistGradientBoostingRegressor` per horizon ($+15\text{m}, +30\text{m}, +60\text{m}$).
- Trained on multi-scenario synthetic simulation runs with automatic fallback to `1.0.0-physics-baseline` if uninitialized.

---

## 4. Public API

```python
from ai.environment import predict_observation_quality

result = predict_observation_quality(
    state={
        "temperature": 27.4,
        "humidity": 45.2,
        "pressure": 1013.25,
        "lux": 48200.0,
        "rain_detected": False,
        "timestamp": "2026-09-13T11:20:00Z"
    }
)
```

Output:
```json
{
  "current_quality": 0.86,
  "predictions": {
    "15m": 0.82,
    "30m": 0.74,
    "60m": 0.51
  },
  "confidence": 0.88,
  "risk": "MEDIUM",
  "risk_factors": ["ATMOSPHERIC_TURBULENCE"],
  "model_version": "1.0.0-physics-baseline"
}
```

---

## 5. Model Assumptions and Limitations

1. **Aerosol Optical Depth (AOD)**: Clean atmosphere extinction is assumed ($\tau \approx 0.14$). In heavy dust, haze, or industrial smog regions, clear-sky lux benchmarks should be recalibrated.
2. **Local Horizon Obstructions**: Assumes an unobstructed astronomical horizon ($0^\circ$). Physical trees or buildings must be accounted for in the observatory mask.
3. **Sensor Co-location**: Assumes ambient DHT22, BH1750, and BMP280 are situated adjacent to the optical tube assembly.
