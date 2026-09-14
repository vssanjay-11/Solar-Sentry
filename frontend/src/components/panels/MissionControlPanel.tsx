import React from 'react';
import { useObservatory } from '../../context/ObservatoryContext';
import { Target, Play, Square, Compass, RefreshCw } from 'lucide-react';

export const MissionControlPanel: React.FC = () => {
  const { missionTarget, telemetry, sendCommand } = useObservatory();

  return (
    <div className="hud-panel">
      <div className="panel-header">
        <div className="panel-title">
          <Target size={14} />
          <span>Mission Control • Active Target</span>
        </div>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--solar-gold)', fontWeight: 700 }}>
          {missionTarget.name}
        </span>
      </div>

      <div className="panel-body">
        <div className="telemetry-metric-grid">
          <div className="metric-card">
            <div className="metric-card-header">
              <span>Target Azimuth</span>
            </div>
            <div className="metric-card-val">
              {missionTarget.target_azimuth}°
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)' }}>
              Calculated solar ephemeris
            </div>
          </div>

          <div className="metric-card">
            <div className="metric-card-header">
              <span>Target Elevation</span>
            </div>
            <div className="metric-card-val">
              {missionTarget.target_elevation}°
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)' }}>
              Altitude above horizon
            </div>
          </div>

          <div className="metric-card">
            <div className="metric-card-header">
              <span>Hardware Pan/Tilt</span>
            </div>
            <div className="metric-card-val" style={{ fontSize: '15px' }}>
              ({telemetry.pan}°, {telemetry.tilt}°)
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)' }}>
              Target: ({missionTarget.target_pan}°, {missionTarget.target_tilt}°)
            </div>
          </div>

          <div className="metric-card">
            <div className="metric-card-header">
              <span>Tracking Boresight Error</span>
            </div>
            <div className="metric-card-val" style={{ color: 'var(--status-green)' }}>
              {missionTarget.tracking_error_deg}°
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)' }}>
              Closed-loop CV centroid
            </div>
          </div>
        </div>

        {/* Quick Action Buttons */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', marginTop: '4px' }}>
          <button
            className="btn-cmd highlight-observe"
            onClick={() => sendCommand('OBSERVE')}
          >
            <Play size={12} />
            <span>OBSERVE SUN</span>
          </button>

          <button
            className="btn-cmd"
            onClick={() => sendCommand('SCAN')}
          >
            <Compass size={12} />
            <span>RASTER SCAN</span>
          </button>

          <button
            className="btn-cmd"
            onClick={() => sendCommand('PARK')}
          >
            <Square size={12} />
            <span>PARK / STOW</span>
          </button>
        </div>
      </div>
    </div>
  );
};
