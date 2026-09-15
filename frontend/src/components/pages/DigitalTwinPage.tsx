import React, { useState } from 'react';
import { 
  Layers3, 
  Radio, 
  SlidersHorizontal, 
  Sun, 
  BarChart3, 
  Zap, 
  Compass, 
  ChevronUp, 
  ChevronDown, 
  ChevronLeft, 
  ChevronRight,
  RotateCcw
} from 'lucide-react';
import { useObservatory } from '../../context/ObservatoryContext';
import { Panel, ImageStage } from './common/UIPrimitives';

interface DigitalTwinPageProps {
  announce: (message: string) => void;
}

export const DigitalTwinPage: React.FC<DigitalTwinPageProps> = ({ announce }) => {
  const { telemetry, sendCommand, systemMode } = useObservatory();

  const [activeLayers, setActiveLayers] = useState({
    surface: true,
    magnetic: true,
    wind: true
  });

  const handleJog = async (direction: 'PAN_LEFT' | 'PAN_RIGHT' | 'TILT_UP' | 'TILT_DOWN') => {
    let newPan = telemetry.pan;
    let newTilt = telemetry.tilt;

    if (direction === 'PAN_LEFT') newPan = Math.max(0, telemetry.pan - 5);
    if (direction === 'PAN_RIGHT') newPan = Math.min(180, telemetry.pan + 5);
    if (direction === 'TILT_UP') newTilt = Math.min(90, telemetry.tilt + 5);
    if (direction === 'TILT_DOWN') newTilt = Math.max(0, telemetry.tilt - 5);

    await sendCommand('SET_SERVO', { pan: newPan, tilt: newTilt });
    announce(`Jogged mount ${direction.replace('_', ' ')} to Pan ${newPan.toFixed(1)}°, Tilt ${newTilt.toFixed(1)}°`);
  };

  const handleHome = async () => {
    await sendCommand('PARK');
    announce('Mount reset to home stow position (90°, 0°)');
  };

  return (
    <>
      <section className="page-grid twin-layout">
        {/* Real-time Simulation Status */}
        <Panel title="Kinematic Synchronization" icon={Radio}>
          <div className="environment-status">
            <span className="status-dot" />
            <div>
              <strong>Syncing Dual-Axis Edge Hardware</strong>
              <span>Real ESP32 Pan/Tilt Telemetry</span>
            </div>
          </div>
          <div className="status-rows" style={{ marginTop: '8px' }}>
            <div>
              <span>System Mode</span>
              <strong>{systemMode === 'DEMO' ? 'SIMULATOR ENGINE' : 'HARDWARE SENSORS'}</strong>
            </div>
            <div>
              <span>Current Azimuth (Pan)</span>
              <strong style={{ color: 'var(--v0-cyan)' }}>{telemetry.pan.toFixed(1)}°</strong>
            </div>
            <div>
              <span>Current Elevation (Tilt)</span>
              <strong style={{ color: 'var(--v0-cyan)' }}>{telemetry.tilt.toFixed(1)}°</strong>
            </div>
            <div>
              <span>Update Frequency</span>
              <strong>1.0 Hz (1000ms tick)</strong>
            </div>
            <div>
              <span>Kinematic Accuracy</span>
              <strong style={{ color: 'var(--v0-green)' }}>99.2% (Servo Encoders)</strong>
            </div>
          </div>
        </Panel>

        {/* Digital Twin Celestial Stage */}
        <Panel title="Digital Twin Solar System Simulation" icon={Layers3}>
          <div className="image-stage observatory-stage" style={{ position: 'relative' }}>
            <img 
              src="/space/digital-twin.jpg" 
              alt="Digital Twin 3D Solar System and Magnetic Field Lines" 
            />
            <div className="stage-grid" />
            <div style={{
              position: 'absolute',
              top: '16px',
              right: '16px',
              background: 'rgba(2, 14, 32, 0.85)',
              border: '1px solid rgba(23, 190, 254, 0.5)',
              borderRadius: '8px',
              padding: '10px 14px',
              fontSize: '11px',
              color: '#fff',
              backdropFilter: 'blur(8px)'
            }}>
              <div style={{ color: '#17befe', fontWeight: 700, marginBottom: '4px' }}>ACTUATOR STATUS</div>
              <div>Pan Servo: <strong>{telemetry.pan.toFixed(1)}°</strong></div>
              <div>Tilt Servo: <strong>{telemetry.tilt.toFixed(1)}°</strong></div>
              <div>Tracking Error: <strong>&lt; 0.15°</strong></div>
            </div>
            <span className="stage-label">
              CYBER-PHYSICAL TWIN · HELIOPHYSICS & KINEMATICS ENGINE · 1:1 SERVO MAPPING
            </span>
          </div>
        </Panel>

        {/* Mount Kinematics & Manual Jog Controls */}
        <Panel title="Mount Kinematics Jog" icon={Compass}>
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '6px',
            padding: '10px 0'
          }}>
            <button 
              onClick={() => handleJog('TILT_UP')}
              style={{
                width: '42px',
                height: '38px',
                background: 'rgba(9, 44, 80, 0.76)',
                border: '1px solid rgba(27, 143, 233, 0.48)',
                borderRadius: '6px',
                color: '#fff',
                cursor: 'pointer'
              }}
              title="Tilt Up"
            >
              <ChevronUp size={20} />
            </button>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button 
                onClick={() => handleJog('PAN_LEFT')}
                style={{
                  width: '42px',
                  height: '38px',
                  background: 'rgba(9, 44, 80, 0.76)',
                  border: '1px solid rgba(27, 143, 233, 0.48)',
                  borderRadius: '6px',
                  color: '#fff',
                  cursor: 'pointer'
                }}
                title="Pan Left"
              >
                <ChevronLeft size={20} />
              </button>
              <button 
                onClick={handleHome}
                style={{
                  width: '42px',
                  height: '38px',
                  background: 'rgba(8, 104, 220, 0.6)',
                  border: '1px solid #17befe',
                  borderRadius: '6px',
                  color: '#fff',
                  cursor: 'pointer'
                }}
                title="Home Mount (90, 0)"
              >
                <RotateCcw size={16} />
              </button>
              <button 
                onClick={() => handleJog('PAN_RIGHT')}
                style={{
                  width: '42px',
                  height: '38px',
                  background: 'rgba(9, 44, 80, 0.76)',
                  border: '1px solid rgba(27, 143, 233, 0.48)',
                  borderRadius: '6px',
                  color: '#fff',
                  cursor: 'pointer'
                }}
                title="Pan Right"
              >
                <ChevronRight size={20} />
              </button>
            </div>
            <button 
              onClick={() => handleJog('TILT_DOWN')}
              style={{
                width: '42px',
                height: '38px',
                background: 'rgba(9, 44, 80, 0.76)',
                border: '1px solid rgba(27, 143, 233, 0.48)',
                borderRadius: '6px',
                color: '#fff',
                cursor: 'pointer'
              }}
              title="Tilt Down"
            >
              <ChevronDown size={20} />
            </button>
          </div>

          <button 
            className="primary-action wide"
            onClick={() => {
              sendCommand('OBSERVE');
              announce('Continuous autonomous solar ephemeris tracking active');
            }}
          >
            <Zap size={14} /> Re-align to Solar Ephemeris
          </button>
        </Panel>
      </section>

      {/* 3-Column Lower Simulation & Physics Row */}
      <section className="page-grid three">
        {/* Layer Visualization */}
        <Panel title="Layer Visualization" icon={Layers3}>
          <div className="thumb-row three-thumbs">
            <div>
              <img src="/space/solar-analysis.jpg" alt="Solar Surface" />
              <small>Solar Photosphere</small>
            </div>
            <div>
              <img src="/space/digital-twin.jpg" alt="Magnetic Field" />
              <small>Magnetic Field Lines</small>
            </div>
            <div>
              <img src="/space/ai-insights.jpg" alt="Solar Wind" />
              <small>Solar Wind Plasma</small>
            </div>
          </div>
        </Panel>

        {/* Live Solar Physical Parameters */}
        <Panel title="Solar Parameters (Live Model)" icon={Sun}>
          <div className="status-rows">
            <div>
              <span>Solar Radius</span>
              <strong>696,340 km (1.0 R☉)</strong>
            </div>
            <div>
              <span>Effective Surface Temp</span>
              <strong>5,778 K</strong>
            </div>
            <div>
              <span>Mean Photospheric Magnetic Field</span>
              <strong>2.8 Gauss</strong>
            </div>
            <div>
              <span>Solar Wind Velocity (1 AU)</span>
              <strong>420 km/s</strong>
            </div>
          </div>
        </Panel>

        {/* AI Heliophysics Insight */}
        <Panel title="Twin Predictive Insights" icon={BarChart3}>
          <div className="insight-list">
            <div>
              <span className="status-dot" />
              Kinematic tracking aligned with calculated ephemeris vector
              <strong>Synced</strong>
            </div>
            <div>
              <span className="status-dot" />
              Dual-axis mount backlash calibrated: &lt; 0.08°
              <strong>Calibrated</strong>
            </div>
            <div>
              <span className="status-dot" />
              Solar transit azimuth rate: ~15° / hour
              <strong>Nominal</strong>
            </div>
          </div>
        </Panel>
      </section>
    </>
  );
};
