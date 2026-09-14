import React, { useState } from 'react';
import { useObservatory } from '../../context/ObservatoryContext';
import { Sliders, Send, RotateCcw, ArrowUp, ArrowDown, ArrowLeft, ArrowRight, ShieldCheck } from 'lucide-react';

export const CommandControlPanel: React.FC = () => {
  const { telemetry, sendCommand } = useObservatory();
  const [targetPan, setTargetPan] = useState<number>(telemetry.pan);
  const [targetTilt, setTargetTilt] = useState<number>(telemetry.tilt);
  const [speed, setSpeed] = useState<number>(100);
  const [lastResult, setLastResult] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState<boolean>(false);

  const handleSlew = async () => {
    setIsBusy(true);
    setLastResult(null);
    try {
      const res = await sendCommand('SET_SERVO', { pan: targetPan, tilt: targetTilt, speed });
      setLastResult(`${res.status}: ${res.message}`);
    } catch (err: any) {
      setLastResult(`ERROR: ${err.message}`);
    } finally {
      setIsBusy(false);
    }
  };

  const handleJog = (dPan: number, dTilt: number) => {
    const newPan = Math.max(0, Math.min(180, targetPan + dPan));
    const newTilt = Math.max(0, Math.min(180, targetTilt + dTilt));
    setTargetPan(newPan);
    setTargetTilt(newTilt);
  };

  return (
    <div className="hud-panel">
      <div className="panel-header">
        <div className="panel-title">
          <Sliders size={14} />
          <span>Manual Actuator Flight Deck</span>
        </div>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-muted)' }}>
          DIRECT DISPATCH
        </span>
      </div>

      <div className="panel-body">
        {/* Jog & Servo Angles */}
        <div className="servo-control-grid">
          {/* Pan Slider */}
          <div className="servo-slider-group">
            <label>
              <span>PAN SERVO (GPIO18)</span>
              <span style={{ color: 'var(--cyan-primary)', fontWeight: 700 }}>{targetPan}°</span>
            </label>
            <input
              type="range"
              min="0"
              max="180"
              value={targetPan}
              onChange={(e) => setTargetPan(Number(e.target.value))}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '8px', color: 'var(--text-dim)' }}>
              <span>0° (CCW Limit)</span>
              <span>90° (Neutral)</span>
              <span>180° (CW Limit)</span>
            </div>
          </div>

          {/* Tilt Slider */}
          <div className="servo-slider-group">
            <label>
              <span>TILT SERVO (GPIO19)</span>
              <span style={{ color: 'var(--solar-gold)', fontWeight: 700 }}>{targetTilt}°</span>
            </label>
            <input
              type="range"
              min="0"
              max="180"
              value={targetTilt}
              onChange={(e) => setTargetTilt(Number(e.target.value))}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '8px', color: 'var(--text-dim)' }}>
              <span>0° (Stow / Horizon)</span>
              <span>90° (Zenith)</span>
              <span>180° (Invert)</span>
            </div>
          </div>
        </div>

        {/* Jog Pad & Actions */}
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          {/* D-Pad */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 30px)', gridTemplateRows: 'repeat(3, 30px)', gap: '4px' }}>
            <div />
            <button className="btn-cmd" style={{ padding: 0 }} onClick={() => handleJog(0, 5)} title="Tilt Up +5°">
              <ArrowUp size={14} />
            </button>
            <div />

            <button className="btn-cmd" style={{ padding: 0 }} onClick={() => handleJog(-5, 0)} title="Pan Left -5°">
              <ArrowLeft size={14} />
            </button>
            <div style={{ background: 'var(--bg-deep)', borderRadius: '2px', border: '1px solid var(--border-dim)' }} />
            <button className="btn-cmd" style={{ padding: 0 }} onClick={() => handleJog(5, 0)} title="Pan Right +5°">
              <ArrowRight size={14} />
            </button>

            <div />
            <button className="btn-cmd" style={{ padding: 0 }} onClick={() => handleJog(0, -5)} title="Tilt Down -5°">
              <ArrowDown size={14} />
            </button>
            <div />
          </div>

          {/* Slew Dispatch Button */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <button
              className="btn-cmd"
              onClick={handleSlew}
              disabled={isBusy}
              style={{
                background: 'linear-gradient(90deg, #0b314a, #082337)',
                borderColor: 'var(--cyan-primary)',
                color: 'var(--cyan-primary)',
                padding: '10px',
                fontWeight: 800
              }}
            >
              <Send size={14} />
              <span>{isBusy ? 'SLEWING GIMBAL...' : `DISPATCH SLEW (${targetPan}°, ${targetTilt}°)`}</span>
            </button>

            <div style={{ display: 'flex', gap: '6px' }}>
              <button
                className="btn-cmd"
                style={{ flex: 1 }}
                onClick={() => sendCommand('CALIBRATE')}
              >
                <RotateCcw size={12} />
                <span>CALIBRATE</span>
              </button>
              <button
                className="btn-cmd"
                style={{ flex: 1 }}
                onClick={() => {
                  setTargetPan(90);
                  setTargetTilt(0);
                  sendCommand('PARK');
                }}
              >
                <span>PARK (90, 0)</span>
              </button>
            </div>
          </div>
        </div>

        {/* Command Result Banner */}
        {lastResult && (
          <div
            style={{
              padding: '6px 10px',
              borderRadius: 'var(--radius-xs)',
              background: 'rgba(0, 229, 255, 0.08)',
              border: '1px solid var(--cyan-dim)',
              fontFamily: 'var(--font-mono)',
              fontSize: '10px',
              color: 'var(--cyan-primary)',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <ShieldCheck size={13} />
            <span>{lastResult}</span>
          </div>
        )}
      </div>
    </div>
  );
};
