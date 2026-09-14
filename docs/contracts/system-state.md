# Solar Sentry — System State Machine Specification

## 1. Authoritative States

The Solar Sentry edge and central cognitive platform adhere to the following shared state machine:

| State | Description | Edge Actuator Pose | Status LEDs |
|---|---|---|---|
| `BOOT` | System powering on, initialization | Neutral (90, 0) | All LEDs cycle |
| `SELF_CHECK` | Hardware diagnostic, sensor bus scanning | Neutral (90, 0) | Yellow blinking |
| `STANDBY` | Ready, idle, awaiting observation or backend instructions | Neutral (90, 0) | Green blinking (slow) |
| `OBSERVE` | Active solar tracking and acquisition | Dynamic (Target Sun) | Green solid |
| `WAIT` | Conditions marginal or cloud transit; waiting for clear sky | Hold current pose | Yellow solid |
| `SCAN` | Active multi-region search pattern | Sweeping candidate angles | Green + Yellow alternate |
| `SUSPEND` | Adverse weather (e.g. Rain) or high risk; tracking suspended | Parked / Stowed (90, 0) | Red solid |
| `FAULT` | Hardware subsystem failure detected | Stowed (90, 0) | Red fast blinking |
| `SAFE` | Fail-safe mode (comms timeout or watchdog recovery) | Parked / Stowed (90, 0) | Red slow blinking |
| `DEGRADED` | One or more non-critical sensors failed; operating in degraded mode | Restricted tracking | Yellow fast blinking |

---

## 2. Transition Rules

1. **Bootup**: `BOOT` $\to$ `SELF_CHECK` $\to$ `STANDBY` (if all sensors pass) or `DEGRADED` (if non-critical sensor fails).
2. **Observation**: `STANDBY` $\xrightarrow{\text{Command: OBSERVE}}$ `OBSERVE`.
3. **Rain Emergency Override**: Any state $\xrightarrow{\text{Rain Detected}}$ `SUSPEND` (immediate edge override).
4. **Comms Timeout**: `OBSERVE` / `SCAN` $\xrightarrow{\text{No heartbeat} > 30\text{s}}$ `SAFE`.
5. **Recovery**: `SUSPEND` $\xrightarrow{\text{Rain dry} + \text{Command: RESUME}}$ `STANDBY`.
