import { describe, it, expect, beforeEach } from 'vitest';
import { ObservatorySimulator } from '../services/simulator';

describe('ObservatorySimulator Scenarios & Physics', () => {
  let sim: ObservatorySimulator;

  beforeEach(() => {
    sim = new ObservatorySimulator();
  });

  it('Scenario 1: CLEAR_SKY_OPTIMAL produces nominal state and high ORS', () => {
    sim.setScenario('CLEAR_SKY_OPTIMAL');
    const tick = sim.tick();

    expect(tick.telemetry.state).toBe('OBSERVE');
    expect(tick.decision).toBe('OBSERVE');
    expect(tick.ors_score).toBeGreaterThanOrEqual(80);
    expect(tick.telemetry.rain_detected).toBe(false);
    expect(tick.telemetry.lux).toBeGreaterThan(40000);
    expect(tick.vision.disk_detected).toBe(true);
  });

  it('Scenario 2: CLOUD_TRANSIT produces WAIT state and degraded optics with explainability', () => {
    sim.setScenario('CLOUD_TRANSIT');
    const tick = sim.tick();

    expect(tick.telemetry.state).toBe('WAIT');
    expect(tick.decision).toBe('WAIT');
    expect(tick.ors_score).toBeLessThan(70);
    expect(tick.xai.why_factors.length).toBeGreaterThan(0);
    expect(tick.xai.why_factors.some(f => f.includes('Cloud transit') || f.includes('Humidity'))).toBe(true);
  });

  it('Scenario 3: SUDDEN_RAIN_ALARM triggers emergency stow to (90, 0) and SUSPEND state', () => {
    sim.setScenario('SUDDEN_RAIN_ALARM');
    const tick = sim.tick();

    expect(tick.telemetry.state).toBe('SUSPEND');
    expect(tick.decision).toBe('SUSPEND');
    expect(tick.telemetry.rain_detected).toBe(true);
    expect(tick.telemetry.rain_raw).toBeLessThan(2000);
    expect(tick.telemetry.pan).toBe(90);
    expect(tick.telemetry.tilt).toBe(0); // Safely stowed
    expect(tick.alerts.some(a => a.severity === 'CRITICAL')).toBe(true);
  });

  it('Scenario 4: SENSOR_DRIFT_DEGRADED flags sensor inconsistency and enters DEGRADED state', () => {
    sim.setScenario('SENSOR_DRIFT_DEGRADED');
    const tick = sim.tick();

    expect(tick.telemetry.state).toBe('DEGRADED');
    expect(tick.health.is_anomaly).toBe(true);
    expect(tick.health.anomaly_score).toBeGreaterThan(0.5);
    expect(tick.telemetry.sensor_status.bmp280).toBe(false);
  });

  it('Scenario 5: COMMS_LOSS_FAILSAFE parks actuators to (90, 0) and enters SAFE state', () => {
    sim.setScenario('COMMS_LOSS_FAILSAFE');
    const tick = sim.tick();

    expect(tick.telemetry.state).toBe('SAFE');
    expect(tick.decision).toBe('SAFE');
    expect(tick.telemetry.pan).toBe(90);
    expect(tick.telemetry.tilt).toBe(0);
  });

  it('Dispatches EMERGENCY_STOP command correctly', () => {
    const result = sim.executeCommand({
      command_id: 'test-estop-01',
      command: 'EMERGENCY_STOP'
    });

    expect(result.status).toBe('SUCCESS');
    expect(result.current_state).toBe('SUSPEND');
    expect(result.current_pan).toBe(90);
    expect(result.current_tilt).toBe(0);
  });

  it('Dispatches SET_SERVO command with clamp between 0 and 180', () => {
    const result = sim.executeCommand({
      command_id: 'test-slew-01',
      command: 'SET_SERVO',
      pan: 120,
      tilt: 65,
      speed: 80
    });

    expect(result.status).toBe('SUCCESS');
    expect(result.current_pan).toBe(120);
    expect(result.current_tilt).toBe(65);
  });
});
