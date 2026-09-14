import React from 'react';
import { useObservatory } from '../../context/ObservatoryContext';
import { Sun, Crosshair, Sparkles } from 'lucide-react';

export const SolarAnalysisPanel: React.FC = () => {
  const { vision } = useObservatory();

  return (
    <div className="hud-panel">
      <div className="panel-header">
        <div className="panel-title">
          <Crosshair size={14} />
          <span>Solar Disk Photometry</span>
        </div>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--cyan-primary)' }}>
          AGENT 5 CV STREAM
        </span>
      </div>

      <div className="panel-body">
        <div className="telemetry-metric-grid">
          <div className="metric-card">
            <div className="metric-card-header">
              <span>Disk Center (X, Y)</span>
            </div>
            <div className="metric-card-val" style={{ fontSize: '14px' }}>
              ({vision.center_x.toFixed(0)}, {vision.center_y.toFixed(0)})
              <span className="unit">px</span>
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)' }}>
              Sub-pixel centroid fit
            </div>
          </div>

          <div className="metric-card">
            <div className="metric-card-header">
              <span>Fitted Radius</span>
            </div>
            <div className="metric-card-val">
              {vision.radius_px}
              <span className="unit">px</span>
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)' }}>
              Optical disk diameter: {vision.radius_px * 2} px
            </div>
          </div>

          <div className="metric-card">
            <div className="metric-card-header">
              <span>Limb Darkening (μ)</span>
            </div>
            <div className="metric-card-val">
              {vision.limb_darkening_coeff}
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)' }}>
              Eddington approximation
            </div>
          </div>

          <div className="metric-card">
            <div className="metric-card-header">
              <span>Cloud Occlusion</span>
            </div>
            <div className="metric-card-val" style={{ color: vision.cloud_occlusion_percent > 30 ? 'var(--status-yellow)' : 'var(--status-green)' }}>
              {vision.cloud_occlusion_percent.toFixed(1)}
              <span className="unit">%</span>
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)' }}>
              Direct line-of-sight obstruction
            </div>
          </div>
        </div>

        {/* Sunspots & Active Regions List */}
        <div style={{ background: 'var(--bg-deep)', padding: '8px 10px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-dim)', display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontFamily: 'var(--font-mono)', fontSize: '10px' }}>
            <span style={{ color: 'var(--text-bright)', fontWeight: 700 }}>
              Resolved Active Regions / Sunspots ({vision.sunspots.length})
            </span>
            <span style={{ color: 'var(--solar-gold)' }}>NOAA SWPC CROSS-REF</span>
          </div>

          {vision.sunspots.map((spot) => (
            <div
              key={spot.id}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '4px 6px',
                background: 'var(--bg-panel-elevated)',
                borderRadius: 'var(--radius-xs)',
                fontFamily: 'var(--font-mono)',
                fontSize: '10px'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--solar-gold)' }} />
                <span style={{ color: 'var(--text-bright)', fontWeight: 700 }}>{spot.id}</span>
              </div>
              <span style={{ color: 'var(--text-muted)' }}>({spot.x}, {spot.y})</span>
              <span style={{ color: 'var(--cyan-primary)' }}>{spot.area_px} px²</span>
              <span style={{ color: 'var(--text-dim)' }}>I/I₀: {spot.intensity_ratio}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
