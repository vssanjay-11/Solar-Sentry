# Solar Sentry — Hardware Pin Contract & Electrical Guidelines

**Module Owner**: Agent 1 (Edge Device & ESP32 Integration)  
**Target Hardware**: ESP32 DevKit V1 (30-pin / 38-pin compatible) + ESP32-CAM AI-Thinker Module

---

## 1. Pin Assignment Table

| Subsystem | Component | Pin Identifier | ESP32 GPIO | Electrical Specs | Function / Notes |
|---|---|---|---|---|---|
| **Environment** | DHT22 | DATA | **GPIO4** | 3.3V, External 10k pull-up to 3.3V | Ambient Temperature & Relative Humidity |
| **Light** | BH1750 | SDA | **GPIO21** | 3.3V, I2C bus shared | Ambient Illuminance (Lux, 1–65535 lx) |
| | | SCL | **GPIO22** | 3.3V, I2C bus shared | I2C Clock (Standard 100 kHz) |
| **Pressure** | BMP280 | SDA | **GPIO21** | 3.3V, I2C bus shared | Barometric Pressure (hPa) & Secondary Temp |
| | | SCL | **GPIO22** | 3.3V, I2C bus shared | Default I2C Address `0x76` (or `0x77` alternate) |
| **Weather** | Rain Sensor | AO | **GPIO34** | 3.3V, Analog Input | ADC1 Channel 6 (Input-only, no internal pull-up) |
| **Actuator** | Pan Servo | PWM Signal | **GPIO18** | 5V external power, 3.3V PWM | Horizontal tracking ($0^\circ \text{ to } 180^\circ$) |
| **Actuator** | Tilt Servo | PWM Signal | **GPIO19** | 5V external power, 3.3V PWM | Vertical elevation ($0^\circ \text{ to } 180^\circ$) |
| **Indicators** | Green LED | Anode | **GPIO25** | 3.3V via $220\Omega\text{--}330\Omega$ resistor | Normal / Observing / Standby status |
| | Yellow LED | Anode | **GPIO26** | 3.3V via $220\Omega\text{--}330\Omega$ resistor | Warning / Degraded / Connecting status |
| | Red LED | Anode | **GPIO27** | 3.3V via $220\Omega\text{--}330\Omega$ resistor | Fault / Rain Suspended / Emergency Safe |
| **Vision** | ESP32-CAM | Network | N/A (Wi-Fi) | 5V 2A dedicated supply | Isolated environmental vision node over HTTP |

---

## 2. Power and Electrical Isolation

1. **Common Ground**: The ESP32 DevKit GND, external 5V power supply GND, and servo motor power GND **MUST** be tied together.
2. **Servo Power Supply**: Servos (Pan on GPIO18, Tilt on GPIO19) must **NEVER** be powered directly from the ESP32 3.3V or 5V (VIN) pin, as current draw spikes (up to 1.5A stall) will cause brownouts and CPU reset (`RTCWDT_RTC_RESET`). Use an external regulated 5V (minimum 2A) supply for servo VCC.
3. **I2C Bus Guidelines**:
   - BH1750 (Address `0x23`) and BMP280 (Address `0x76`) share `GPIO21` (SDA) and `GPIO22` (SCL).
   - Ensure $4.7\text{k}\Omega$ pull-up resistors to 3.3V are present on both SDA and SCL if breakout modules do not have onboard pull-ups.
4. **Rain Sensor Analog Characteristics**:
   - GPIO34 is an analog-only pin belonging to ADC1 (safe to read while Wi-Fi is active, unlike ADC2 pins).
   - Output range: 12-bit ADC ($0\text{--}4095$).
   - Dry state: $\sim 3500\text{--}4095$.
   - Wet / Rain state: $< 2000$ (configurable in `config.h` via `RAIN_THRESHOLD_ANALOG`).

---

## 3. Local Safety Interlocks & Safe Positions

- **Stow / Safe Position**: `Pan = 90°` (centered), `Tilt = 0°` (horizontal/stowed downwards to shield lens).
- **Physical Bounds**:
  - `PAN_MIN_ANGLE = 0°`, `PAN_MAX_ANGLE = 180°`
  - `TILT_MIN_ANGLE = 0°`, `TILT_MAX_ANGLE = 180°`
- **Rain Emergency**: If analog reading $< \text{RAIN\_THRESHOLD}$ for 3 consecutive samples, the hardware enters `SUSPEND` state immediately, drives servos to Stow Position, and illuminates the RED LED.

---

## 4. ESP32-CAM Architecture

- The ESP32-CAM is an independent Wi-Fi microcontroller.
- Provides `/capture` for raw JPEG image frames and `/status` for camera sensor health.
- The Main ESP32 probes the camera's availability via HTTP ping or reports its configured IP to the Backend.
