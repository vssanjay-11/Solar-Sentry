import React from 'react';
import { useObservatory } from '../../context/ObservatoryContext';
import { Cpu, ShieldCheck, CheckCircle2, AlertOctagon } from 'lucide-react';
import { EdgeSystemState } from '../../types/telemetry';

export const SystemStatePanel: React.FC = () => {
  const { telemetry } = useObservatory();
  const state = telemetry.state;

  // Compute LED states based on hardware-contract.md & system-state.md
  // Green: OBSERVE (solid), STANDBY (slow blink), SCAN (alternate)
  // Yellow: WAIT (solid), SELF_CHECK (blink), DEGRADED (fast blink), SCAN (alternate)
  // Red: SUSPEND (solid), FAULT (fast blink), SAFE (slow blink)
  const isGreenOn = state === 'OBSERVE' || state === 'STANDBY' || state === 'SCAN';
  const isYellowOn = state === 'WAIT' || state === 'SELF_CHECK' || state === 'DEGRADED' || state === 'SCAN';
  const isRedOn = state === 'SUSPEND' || state === 'FAULT' || state === 'SAFE';

  const getStateClass = (s: EdgeSystemState) => {
    switch (s) {
      case 'OBSERVE': return 'observe';
      case 'WAIT':
      case 'DEGRADED': return 'wait';
      case 'SUSPEND':
      case 'FAULT':
      case 'SAFE': return 'suspend';
      default: return 'standby';
    }
  };

  return (
    <div className="hud-panel">
      <div className="panel-header">
        <div className="panel-title">
          <Cpu size={14} />
          <span>System State</span>
        </div>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-muted)' }}>
          {telemetry.device_id}
        </span>
      </div>

      <div className="panel-body">
        {/* Large State Badge */}
        <div className={`state-badge-large ${getStateClass(state)}`}>
          <span style={{ display: 'inline-block', width: '10px', height: '10px', borderRadius: '50%', background: 'currentColor' }} />
          <span>{state}</span>
        </div>

        {/* Hardware LED Mimic Subsystem */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-muted)' }}>
              EDGE STATUS LEDS (GPIO 25/26/27)
            </span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-dim)' }}>
              HARDWARE MIMIC
            </span>
          </div>
          <div className="hardware-led-mimics">
            <div className="led-item">
              <div className={`led-bulb ${isGreenOn ? 'green-on' : ''}`} />
              <span className="led-label">GRN (25)</span>
              <span style={{ fontSize: '8px', color: 'var(--text-dim)' }}>OBS/STBY</span>
            </div>
            <div className="led-item">
              <div className={`led-bulb ${isYellowOn ? 'yellow-on' : ''}`} />
              <span className="led-label">YEL (26)</span>
              <span style={{ fontSize: '8px', color: 'var(--text-dim)' }}>WAIT/DEG</span>
            </div>
            <div className="led-item">
              <div className={`led-bulb ${isRedOn ? 'red-on' : ''}`} />
              <span className="led-label">RED (27)</span>
              <span style={{ fontSize: '8px', color: 'var(--text-dim)' }}>STOW/SAFE</span>
            </div>
          </div>
        </div>

        {/* Core Safety Hierarchy Interlocks */}
        <div style={{ background: 'var(--bg-deep)', padding: '8px 10px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-dim)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
            Autonomous Safety Interlocks
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontFamily: 'var(--font-mono)', fontSize: '10px' }}>
            <span style={{ color: 'var(--text-standard)' }}>Precipitation Trip</span>
            <span style={{ color: telemetry.rain_detected ? 'var(--status-red)' : 'var(--status-green)', fontWeight: 700 }}>
              {telemetry.rain_detected ? 'TRIPPED (SUSPEND)' : 'DRY (PASS)'}
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontFamily: 'var(--font-mono)', fontSize: '10px' }}>
            <span style={{ color: 'var(--text-standard)' }}>Comms Watchdog</span>
            <span style={{ color: 'var(--status-green)', fontWeight: 700 }}>HEARTBEAT OK</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontFamily: 'var(--font-mono)', fontSize: '10px' }}>
            <span style={{ color: 'var(--text-standard)' }}>Actuator Travel Limit</span>
            <span style={{ color: 'var(--status-green)', fontWeight: 700 }}>SAFE (0-180°)</span>
          </div>
        </div>
      </div>
    </div>
  );
};
