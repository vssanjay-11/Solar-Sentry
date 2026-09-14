# Solar Sentry Computer Vision Subsystem: Algorithms and Limitations

*Agent 5: Computer Vision + Solar Image Intelligence*  
*Module Path: `ai/vision/`*  
*Contract Schema: `docs/contracts/VisionResult.json`*

---

## 1. System Overview & Module Boundaries

Agent 5 has exclusive ownership over **Computer Vision and Solar Image Intelligence** within the Solar Sentry autonomous observatory architecture.

### Architectural Responsibilities:
- Receive raw visual frames from heterogeneous capture sources (ESP32-CAM prototype, uploaded files, historical archives, direct observatory feeds, synthetic simulations).
- Execute deterministic, scientifically-grounded computer vision algorithms to evaluate optical quality, detect solar morphology, identify active regions (sunspots), and detect atmospheric occlusions.
- Provide structured, serialized outputs (`VisionResult`) for downstream cognitive engines (Agent 8) and mission planning (Agent 9).

### Explicit Out-of-Scope Boundaries:
- **Observation Readiness Forecasting**: Agent 5 evaluates the *instantaneous visual state* in the received frame. Multi-horizon predictive observation-quality modeling (15/30/60-minute forecasts) is owned exclusively by **Agent 6 (Environment AI)**.
- **Solar Flare Prediction**: Agent 5 **explicitly does not claim solar flare prediction**. Reliable flare prediction requires calibrated vector magnetograms (such as SDO/HMI), EUV/X-ray flux sensors, and validated neural architectures.
- **Physical Hardware Control**: Servos and camera trigger lines are controlled by **Agent 1 (Edge Firmware)** and scheduled by **Agent 9 (Mission Planner)**.

---

## 2. Mathematical Formulations & Algorithms

### 2.1 Optical Quality Assessment (`ai/vision/quality.py`)

#### A. Blur Estimation: Modified Laplacian Variance & Tenengrad
1. **Laplacian Variance**:
   $$\text{Blur}_{\text{Lap}} = \mathrm{Var}(\nabla^2 I) = \frac{1}{N} \sum_{x,y} \left( \nabla^2 I(x,y) - \overline{\nabla^2 I} \right)^2$$
   Where $\nabla^2 I$ is computed using a $3 \times 3$ Laplacian kernel. Low variance indicates flat or defocused edges.
2. **Tenengrad Energy Density**:
   $$S_{\text{Tenengrad}} = \frac{1}{WH} \sum_{x,y} \left( G_x(x,y)^2 + G_y(x,y)^2 \right)$$
   Where $G_x$ and $G_y$ are Sobel gradients along the horizontal and vertical axes.

#### B. Exposure & Dynamic Range
Analyzes the cumulative 8-bit histogram:
- **Clipped Black Fraction**: $f_{\text{black}} = \frac{1}{N} \sum \mathbb{I}(I(x,y) \le 4)$
- **Clipped White Fraction**: $f_{\text{white}} = \frac{1}{N} \sum \mathbb{I}(I(x,y) \ge 251)$
- **Exposure Score**:
  $$\text{Score}_{\text{exposure}} = (1 - \min(1, 2.5 f_{\text{white}})) \cdot (1 - \max(0, 2 (f_{\text{black}} - 0.75))) \cdot \left(0.5 + 0.5 \frac{\sigma_I}{45}\right)$$
  Penalizes glare saturation blowouts heavily while tolerating dark sky backgrounds.

#### C. High-Frequency Noise Estimation (Donoho-Johnstone MAD)
Calculates noise standard deviation $\sigma_n$ on the high-frequency residual using the Median Absolute Deviation (MAD):
$$\sigma_n = \frac{\mathrm{median}(|R(x,y) - \mathrm{median}(R)|)}{0.6745}$$
Where $R$ is the residual extracted by convolving with a high-pass Laplacian filter.

---

### 2.2 Solar Disk Localization (`ai/vision/solar_disk.py`)

#### A. Morphological Segmentation & Enclosing Circle
- Thresholds the image using multi-stage Otsu with a fallback to the 75th percentile of non-zero pixels.
- Computes contour circularity:
  $$\mathcal{C} = \frac{4\pi \cdot \text{Area}}{\text{Perimeter}^2}$$
  Valid solar disks satisfy $\mathcal{C} \ge 0.75$ (or $\ge 0.60$ for margin-clipped disks).
- Identifies whether the disk is clipped at the sensor boundaries:
  $$(c_x - R \le 2) \lor (c_y - R \le 2) \lor (c_x + R \ge W - 3) \lor (c_y + R \ge H - 3)$$

#### B. Eddington-Barbier Limb Darkening Verification
To distinguish genuine stellar disks from artificial indoor light bulbs or specular reflections, the detector verifies radial limb darkening according to the standard optical approximation:
$$\frac{I(r)}{I(0)} \approx 1 - u \left( 1 - \sqrt{1 - \left(\frac{r}{R}\right)^2} \right)$$
With optical limb darkening coefficient $u \approx 0.55$. Concentric radial rings are sampled from $r = 0.10 R$ to $0.85 R$. Genuine solar disks exhibit monotonic decay with a limb-to-center ratio between $0.50$ and $0.96$.

---

### 2.3 Sunspot Detection & Segmentation (`ai/vision/sunspot.py`)

1. **Photosphere Normalization**:
   Applies large-scale Gaussian filtering ($k \sim 0.15 R$) to compute the background quiet photosphere profile $I_{\text{quiet}}(x,y)$, effectively removing large-scale limb darkening.
2. **Relative Darkness Contrast**:
   $$\Delta_{\text{rel}}(x,y) = \frac{I_{\text{quiet}}(x,y) - I(x,y)}{I_{\text{quiet}}(x,y)}$$
   Candidate sunspot pixels must exceed $\Delta_{\text{rel}} \ge 0.12$ (12% darker than local photosphere).
3. **Morphological Umbra/Penumbra Decomposition**:
   - **Umbra (core)**: $\Delta_{\text{rel}} \ge 0.35$ (intense absorption core).
   - **Penumbra (halo)**: $0.12 \le \Delta_{\text{rel}} < 0.35$.
4. **Heliographic Disk Coordinates**:
   - Disk-relative radius: $r_{\text{rel}} = \frac{\sqrt{(x - c_x)^2 + (y - c_y)^2}}{R} \in [0.0, 1.0]$.
   - Polar position angle: $\theta = \mathrm{atan2}(y - c_y, x - c_x) \pmod{360^\circ}$.
5. **Sensor Artifact & Dust Rejection**:
   - Rejects connected components smaller than 3 pixels.
   - Rejects elongated structures with aspect ratio $> 4.0$ (characteristic of camera lint or sensor scratches).

---

### 2.4 Cloud & Visual Obstruction Detection (`ai/vision/obstruction.py`)

- **Limb Profile Integrity**: Evaluates circular perimeter consistency across 72 radial samples. Passing cloud edges produce sharp localized bite-outs.
- **Sky Texture Variance**: Clear filtered skies have near-zero gradient variance. Clouds produce diffuse scattering gradients and high standard deviation in the off-disk sky region.
- **Classification Categories**:
  - `CLEAR`: Unobstructed disk and limb.
  - `PARTIAL_CLOUD`: Cirrus wisps, localized edge occlusions ($0.15 \le \text{obstruction} < 0.60$).
  - `HEAVY_CLOUD`: Thick cumulus or overcast layer obscuring disk ($> 0.60$).
  - `OVEREXPOSURE_GLARE`: Saturated bloom spilling beyond solar disk.
  - `OFF_TARGET`: Field of view contains no identifiable solar disk.

---

### 2.5 Temporal Registration & Change Detection (`ai/vision/temporal.py`)

- **Fourier Phase Correlation Registration**:
  Compensates for pan/tilt servo tracking jitter (mechanical resolution $\sim 0.5^\circ - 1^\circ$ creates frame-to-frame pixel shifts).
  Given current image $f(x,y)$ and reference $g(x,y)$, cross-power spectrum:
  $$R(u,v) = \frac{F(u,v) G^*(u,v)}{|F(u,v) G^*(u,v)|}$$
  The inverse Fourier transform yields a Dirac impulse at the sub-pixel translation vector $(\Delta x, \Delta y)$.
- **Masked Differential Photometry**:
  Measures absolute pixel difference on aligned solar disks to isolate transient changes (newly emerged sunspots vs rapid cloud transits).

---

## 3. Hardware Trade-offs & Sensor Profiles

The system explicitly adapts to different hardware classes:

| Attribute | ESP32-CAM Prototype (OV2640) | Observatory Instrument (e.g. SDO, Kanzelhöhe) |
|---|---|---|
| **Sensor Class** | Uncooled CMOS, 1/4" rolling shutter | Cooled scientific CCD, global shutter |
| **Bit Depth** | 8-bit per channel (sRGB / JPEG compressed) | 12-bit / 16-bit linear FITS |
| **Dynamic Range** | Low (~48–54 dB); prone to blooming | High (>80 dB); calibrated solar filters |
| **Optical Distortions** | Noticeable lens vignetting, barrel distortion | Diffraction-limited telescope optics |
| **Thermal Noise** | High ($\sigma_n \approx 4 - 8$ DN at daytime temp) | Very low ($\sigma_n < 1$ DN) |
| **Tracking Jitter** | Dual-axis RC servos ($1^\circ$ backlash/jitter) | Equatorial mount with sidereal encoder drive |
| **Target Role** | Environmental solar tracking & presence verification | High-precision helioseismology & magnetic flux |

---

## 4. Scientific Disclaimers & Integrity Constraints

1. **No Solar Flare Prediction**:
   Solar flares originate in complex twisted coronal magnetic fields (free magnetic energy release via reconnection). Predicting flares requires high-cadence vector magnetograms (Stokes $I, Q, U, V$) and coronal EUV imaging. Agent 5 extracts white-light sunspot geometry and optical quality, and explicitly refrains from claiming flare prediction capability.
2. **Atmospheric Seeing vs Inherent Blur**:
   Ground-based observations without adaptive optics suffer from atmospheric turbulence (Fried parameter $r_0$). A drop in `blur_score` may reflect local thermal seeing rather than camera defocus.
