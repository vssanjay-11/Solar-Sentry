import React from 'react';
import { useObservatory } from '../../context/ObservatoryContext';
import { ShieldCheck, AlertTriangle } from 'lucide-react';

export const ObservatoryHealthPanel: React.FC = () => {
  const { observatoryHealth } = useObservatory();

  const getHealthColor = (score: number) => {
    if (score >= 85) return 'var(--status-green)';
    if (score >= 60) return 'var(--status-yellow)';
    return 'var(--status-red)';
  };

  return (
    <div className="hud-panel">
      <div className="panel-header">
        <div className="panel-title">
          <ShieldCheck size={14} />
          <span>Observatory Health</span>
        </div>
        <span
          style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '11px',
            color: getHealthColor(observatoryHealth.overall),
            fontWeight: 800
          }}
        >
          {observatoryHealth.overall}% INTEGRITY
        </span>
      </div>

      <div className="panel-body">
        {/* Subsystem Bars */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: 'var(--font-mono)', fontSize: '10px', marginBottom: '2px' }}>
              <span style={{ color: 'var(--text-muted)' }}>Edge Controller & Actuators</span>
              <span style={{ color: 'var(--text-bright)', fontWeight: 700 }}>{observatoryHealth.edge_hardware}%</span>
            </div>
            <div style={{ height: '4px', background: 'var(--bg-deep)', borderRadius: '2px', overflow: 'hidden' }}>
              <div style={{ height: '100%', width: `${observatoryHealth.edge_hardware}%`, background: getHealthColor(observatoryHealth.edge_hardware) }} />
            </div>
          </div>

          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: 'var(--font-mono)', fontSize: '10px', marginBottom: '2px' }}>
              <span style={{ color: 'var(--text-muted)' }}>Optical Vision System</span>
              <span style={{ color: 'var(--text-bright)', fontWeight: 700 }}>{observatoryHealth.optical_vision}%</span>
            </div>
            <div style={{ height: '4px', background: 'var(--bg-deep)', borderRadius: '2px', overflow: 'hidden' }}>
              <div style={{ height: '100%', width: `${observatoryHealth.optical_vision}%`, background: getHealthColor(observatoryHealth.optical_vision) }} />
            </div>
          </div>

          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: 'var(--font-mono)', fontSize: '10px', marginBottom: '2px' }}>
              <span style={{ color: 'var(--text-muted)' }}>Telemetry & Comms Network</span>
              <span style={{ color: 'var(--text-bright)', fontWeight: 700 }}>{observatoryHealth.network_comms}%</span>
            </div>
            <div style={{ height: '4px', background: 'var(--bg-deep)', borderRadius: '2px', overflow: 'hidden' }}>
              <div style={{ height: '100%', width: `${observatoryHealth.network_comms}%`, background: getHealthColor(observatoryHealth.network_comms) }} />
            </div>
          </div>
        </div>

        {/* Isolation Forest Anomaly Metric */}
        <div
          style={{
            background: observatoryHealth.is_anomaly ? 'rgba(255, 42, 95, 0.15)' : 'var(--bg-deep)',
            border: `1px solid ${observatoryHealth.is_anomaly ? 'var(--status-red)' : 'var(--border-dim)'}`,
            borderRadius: 'var(--radius-sm)',
            padding: '8px 10px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertTriangle size={14} color={observatoryHealth.is_anomaly ? 'var(--status-red)' : 'var(--cyan-primary)'} />
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-bright)', fontWeight: 700 }}>
                Isolation Forest AI Score
              </span>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)' }}>
                Multi-sensor covariance anomaly model
              </span>
            </div>
          </div>

          <div style={{ textAlign: 'right' }}>
            <div
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '14px',
                fontWeight: 800,
                color: observatoryHealth.is_anomaly ? 'var(--status-red)' : 'var(--cyan-primary)'
              }}
            >
              {observatoryHealth.anomaly_score.toFixed(2)}
            </div>
            <span
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '8px',
                color: observatoryHealth.is_anomaly ? 'var(--status-red)' : 'var(--status-green)',
                fontWeight: 700
              }}
            >
              {observatoryHealth.is_anomaly ? 'OUTLIER DETECTED' : 'NOMINAL (< 0.50)'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
