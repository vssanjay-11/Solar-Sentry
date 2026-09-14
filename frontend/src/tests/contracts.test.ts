import { describe, it, expect } from 'vitest';
import { ObservatorySimulator } from '../services/simulator';

describe('Contracts & Schema Compatibility', () => {
  const sim = new ObservatorySimulator();

  it('SensorTelemetry adheres to docs/contracts/SensorTelemetry.json requirements', () => {
    const tick = sim.tick();
    const t = tick.telemetry;

    // Required fields from SensorTelemetry.json
    expect(typeof t.device_id).toBe('string');
    expect(typeof t.timestamp).toBe('string');
    expect(typeof t.temperature).toBe('number');
    expect(typeof t.humidity).toBe('number');
    expect(typeof t.pressure).toBe('number');
    expect(typeof t.lux).toBe('number');
    expect(typeof t.rain_raw).toBe('number');
    expect(typeof t.pan).toBe('number');
    expect(typeof t.tilt).toBe('number');
    expect(typeof t.state).toBe('string');
    expect(typeof t.health).toBe('number');
    expect(typeof t.firmware_version).toBe('string');

    // Bounds checks
    expect(t.humidity).toBeGreaterThanOrEqual(0);
    expect(t.humidity).toBeLessThanOrEqual(100);
    expect(t.pan).toBeGreaterThanOrEqual(0);
    expect(t.pan).toBeLessThanOrEqual(180);
    expect(t.tilt).toBeGreaterThanOrEqual(0);
    expect(t.tilt).toBeLessThanOrEqual(180);
    expect(t.health).toBeGreaterThanOrEqual(0);
    expect(t.health).toBeLessThanOrEqual(100);
    expect(t.rain_raw).toBeGreaterThanOrEqual(0);
    expect(t.rain_raw).toBeLessThanOrEqual(4095);

    // Valid state enum
    const validStates = ['BOOT', 'SELF_CHECK', 'STANDBY', 'OBSERVE', 'WAIT', 'SCAN', 'SUSPEND', 'FAULT', 'SAFE', 'DEGRADED'];
    expect(validStates).toContain(t.state);
  });

  it('CommandResult adheres to docs/contracts/CommandResult.json requirements', () => {
    const res = sim.executeCommand({
      command_id: 'cmd-test-99',
      command: 'OBSERVE'
    });

    expect(res.command_id).toBe('cmd-test-99');
    expect(['SUCCESS', 'REJECTED_SAFETY', 'INVALID_PARAMS', 'EXECUTION_ERROR']).toContain(res.status);
    expect(typeof res.current_pan).toBe('number');
    expect(typeof res.current_tilt).toBe('number');
    expect(typeof res.current_state).toBe('string');
    expect(res.current_pan).toBeGreaterThanOrEqual(0);
    expect(res.current_pan).toBeLessThanOrEqual(180);
    expect(res.current_tilt).toBeGreaterThanOrEqual(0);
    expect(res.current_tilt).toBeLessThanOrEqual(180);
  });
});
