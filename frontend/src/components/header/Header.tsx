import React, { useState, useEffect } from 'react';
import { useObservatory } from '../../context/ObservatoryContext';
import type { SimulationScenarioId } from '../../services/simulator';
import { SIMULATION_SCENARIOS } from '../../services/simulator';
import { 
  Activity, 
  Satellite, 
  ShieldAlert, 
  SunMedium 
} from 'lucide-react';

export const Header: React.FC = () => {
  const {
    systemMode,
    setSystemMode,
    isOnline,
    isSimulationMode,
    activeScenario,
    switchScenario,
    wsStatus,
    telemetry,
    triggerEmergencyStop,
    isReplayActive,
    setIsReplayActive
  } = useObservatory();

  const [utcTime, setUtcTime] = useState<string>('');
  const [localTime, setLocalTime] = useState<string>('');
  const [showEstopConfirm, setShowEstopConfirm] = useState<boolean>(false);


  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setUtcTime(now.toUTCString().slice(17, 25) + ' UTC');
      setLocalTime(now.toLocaleTimeString());
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleEstop = async () => {
    setShowEstopConfirm(false);
    await triggerEmergencyStop();
  };

  return (
    <>
      {/* Simulation Banner if in Simulation Mode */}
      {isSimulationMode && !isReplayActive && (
        <div className="sim-mode-banner">
          <div className="sim-title">
            <span className="sim-badge">SIMULATION MODE ACTIVE</span>
            <span>Edge & AI Simulation Engine Engaged (No physical hardware connected)</span>
          </div>
          <div className="scenario-selector">
            <span>Scenario:</span>
            <select
              className="scenario-select"
              value={activeScenario}
              onChange={(e) => switchScenario(e.target.value as SimulationScenarioId)}
            >
              {SIMULATION_SCENARIOS.map((sc) => (
                <option key={sc.id} value={sc.id}>
                  {sc.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      )}

      {/* Replay Banner if in Replay Mode */}
      {isReplayActive && (
        <div className="sim-mode-banner" style={{ background: 'linear-gradient(90deg, #1b0a24, #3d1452, #1b0a24)', borderBottomColor: '#bd00ff' }}>
          <div className="sim-title" style={{ color: '#f3c4ff' }}>
            <span className="sim-badge" style={{ background: '#bd00ff', color: '#fff' }}>HISTORICAL REPLAY MODE</span>
            <span>Telemetry Scrubbing Active — Real-time stream frozen</span>
          </div>
          <button
            onClick={() => setIsReplayActive(false)}
            style={{
              background: '#bd00ff',
              color: '#fff',
              border: 'none',
              padding: '2px 8px',
              fontFamily: 'var(--font-mono)',
              fontSize: '11px',
              fontWeight: 700,
              cursor: 'pointer',
              borderRadius: '2px'
            }}
          >
            EXIT REPLAY
          </button>
        </div>
      )}

      <header className="observatory-header">
        {/* Brand */}
        <div className="header-brand">
          <div className="brand-icon">
            <SunMedium size={20} />
          </div>
          <div className="brand-info">
            <h1>Solar Sentry</h1>
            <div className="brand-subtitle">Autonomous Cognitive Solar Observatory • Ops Deck</div>
          </div>
        </div>

        {/* Mission Clocks */}
        <div className="header-center">
          <div className="mission-clock">
            <div className="clock-group">
              <span className="label">UTC Time</span>
              <span className="time">{utcTime || '00:00:00 UTC'}</span>
            </div>
            <div className="clock-group">
              <span className="label">Local</span>
              <span className="time">{localTime || '00:00:00'}</span>
            </div>
            <div className="clock-group">
              <span className="label">ESP32 Uptime</span>
              <span className="time" style={{ color: 'var(--text-standard)' }}>
                {Math.floor(telemetry.uptime_seconds / 3600)}h {Math.floor((telemetry.uptime_seconds % 3600) / 60)}m {telemetry.uptime_seconds % 60}s
              </span>
            </div>
          </div>
        </div>

        {/* Status & Actions */}
        <div className="header-actions">
          {/* Connection Pill */}
          <div className="conn-status-pill">
            <span className={`conn-dot ${isSimulationMode ? 'online' : wsStatus === 'CONNECTED' ? 'online' : 'offline'}`} />
            <span>
              {isSimulationMode ? 'SIMULATOR (1 Hz)' : wsStatus === 'CONNECTED' ? `WS LIVE (${telemetry.wifi_rssi} dBm)` : wsStatus}
            </span>
          </div>

          {/* Dual State System Mode Toggle: DEMO <-> LIVE HARDWARE */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            background: 'rgba(0, 0, 0, 0.4)',
            border: '1px solid var(--border-mid)',
            borderRadius: '6px',
            padding: '2px',
            gap: '2px'
          }}>
            <button
              onClick={() => setSystemMode('DEMO')}
              style={{
                background: systemMode === 'DEMO' ? 'rgba(255, 170, 0, 0.2)' : 'transparent',
                border: systemMode === 'DEMO' ? '1px solid var(--solar-gold)' : 'none',
                color: systemMode === 'DEMO' ? 'var(--solar-gold)' : 'var(--text-muted)',
                fontFamily: 'var(--font-mono)',
                fontSize: '11px',
                fontWeight: 600,
                padding: '4px 10px',
                borderRadius: '4px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '5px'
              }}
              title="DEMO MODE: Synthetic observation, 10 deterministic test scenarios, virtual twin"
            >
              <Activity size={12} />
              <span>DEMO</span>
            </button>

            <button
              onClick={() => setSystemMode('HARDWARE')}
              style={{
                background: systemMode === 'HARDWARE'
                  ? (isOnline ? 'rgba(0, 230, 118, 0.2)' : 'rgba(255, 77, 77, 0.2)')
                  : 'transparent',
                border: systemMode === 'HARDWARE'
                  ? (isOnline ? '1px solid var(--green-nominal)' : '1px solid var(--red-alert)')
                  : 'none',
                color: systemMode === 'HARDWARE'
                  ? (isOnline ? 'var(--green-nominal)' : 'var(--red-alert)')
                  : 'var(--text-muted)',
                fontFamily: 'var(--font-mono)',
                fontSize: '11px',
                fontWeight: 600,
                padding: '4px 10px',
                borderRadius: '4px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '5px'
              }}
              title="LIVE HARDWARE MODE: Real ESP32, ESP32-CAM and dual servos. Reports OFFLINE if disconnected."
            >
              <span style={{
                width: '7px',
                height: '7px',
                borderRadius: '50%',
                background: systemMode === 'HARDWARE'
                  ? (isOnline ? 'var(--green-nominal)' : 'var(--red-alert)')
                  : 'var(--text-muted)'
              }} />
              <span>HARDWARE {systemMode === 'HARDWARE' && (isOnline ? '(ONLINE)' : '(OFFLINE)')}</span>
            </button>
          </div>


          {/* Replay Toggle */}
          <button
            onClick={() => setIsReplayActive(!isReplayActive)}
            style={{
              background: isReplayActive ? '#3d1452' : 'var(--bg-panel-elevated)',
              border: `1px solid ${isReplayActive ? '#bd00ff' : 'var(--border-mid)'}`,
              color: isReplayActive ? '#f3c4ff' : 'var(--text-standard)',
              fontFamily: 'var(--font-mono)',
              fontSize: '11px',
              padding: '5px 10px',
              borderRadius: 'var(--radius-sm)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <Satellite size={13} />
            <span>REPLAY</span>
          </button>

          {/* Emergency Stop Button */}
          <button className="btn-estop" onClick={() => setShowEstopConfirm(true)}>
            <ShieldAlert size={14} />
            <span>E-STOP</span>
          </button>
        </div>
      </header>

      {/* Emergency Stop Confirmation Modal */}
      {showEstopConfirm && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(5, 8, 14, 0.85)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000
          }}
        >
          <div
            style={{
              width: '420px',
              background: 'var(--bg-panel)',
              border: '2px solid var(--status-red)',
              borderRadius: 'var(--radius-md)',
              padding: '20px',
              boxShadow: 'var(--shadow-glow-red)',
              display: 'flex',
              flexDirection: 'column',
              gap: '16px'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--status-red)' }}>
              <ShieldAlert size={28} />
              <h2 style={{ fontSize: '16px', fontWeight: 800, textTransform: 'uppercase' }}>Confirm Emergency Stop</h2>
            </div>
            <p style={{ color: 'var(--text-standard)', fontSize: '12px', lineHeight: 1.5 }}>
              Triggering Emergency Stop will immediately override central tracking, disengage all active missions, 
              stow dual-axis servos to the safe park pose (Pan: 90°, Tilt: 0°), and lock edge state to <strong>SUSPEND</strong>.
            </p>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                onClick={() => setShowEstopConfirm(false)}
                style={{
                  background: 'var(--bg-panel-elevated)',
                  border: '1px solid var(--border-mid)',
                  color: 'var(--text-standard)',
                  padding: '6px 14px',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '11px',
                  cursor: 'pointer',
                  borderRadius: 'var(--radius-xs)'
                }}
              >
                CANCEL
              </button>
              <button
                onClick={handleEstop}
                style={{
                  background: 'var(--status-red)',
                  border: '1px solid #ff5982',
                  color: '#fff',
                  padding: '6px 16px',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '11px',
                  fontWeight: 800,
                  cursor: 'pointer',
                  borderRadius: 'var(--radius-xs)'
                }}
              >
                CONFIRM E-STOP
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
