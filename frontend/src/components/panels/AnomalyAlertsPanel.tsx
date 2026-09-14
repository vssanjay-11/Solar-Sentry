import React from 'react';
import { useObservatory } from '../../context/ObservatoryContext';
import { ShieldAlert, AlertTriangle, Info, Check, Trash2 } from 'lucide-react';
import { AlertSeverity } from '../../types/alerts';

export const AnomalyAlertsPanel: React.FC = () => {
  const { alerts, acknowledgeAlert, clearAlerts } = useObservatory();

  const getSeverityIcon = (sev: AlertSeverity) => {
    switch (sev) {
      case 'CRITICAL': return <ShieldAlert size={14} color="var(--status-red)" />;
      case 'WARNING': return <AlertTriangle size={14} color="var(--status-yellow)" />;
      default: return <Info size={14} color="var(--cyan-primary)" />;
    }
  };

  const getSeverityBadgeClass = (sev: AlertSeverity) => {
    switch (sev) {
      case 'CRITICAL': return { bg: 'rgba(255, 42, 95, 0.2)', border: 'var(--status-red)', color: 'var(--status-red)' };
      case 'WARNING': return { bg: 'rgba(255, 183, 0, 0.2)', border: 'var(--status-yellow)', color: 'var(--status-yellow)' };
      default: return { bg: 'rgba(0, 229, 255, 0.15)', border: 'var(--cyan-primary)', color: 'var(--cyan-primary)' };
    }
  };

  return (
    <div className="hud-panel">
      <div className="panel-header">
        <div className="panel-title">
          <ShieldAlert size={14} />
          <span>Anomaly & Safety Alerts ({alerts.length})</span>
        </div>
        {alerts.length > 0 && (
          <button
            onClick={clearAlerts}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              fontFamily: 'var(--font-mono)',
              fontSize: '10px'
            }}
          >
            <Trash2 size={11} />
            <span>CLEAR ALL</span>
          </button>
        )}
      </div>

      <div className="panel-body" style={{ maxHeight: '240px', overflowY: 'auto' }}>
        {alerts.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '24px 0', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', fontSize: '11px' }}>
            ALL SUBSYSTEMS NOMINAL • NO ACTIVE ANOMALIES
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {alerts.map((alt) => {
              const badgeStyle = getSeverityBadgeClass(alt.severity);
              return (
                <div
                  key={alt.alert_id}
                  style={{
                    background: 'var(--bg-deep)',
                    border: `1px solid ${alt.severity === 'CRITICAL' ? 'var(--status-red)' : 'var(--border-dim)'}`,
                    borderLeft: `3px solid ${badgeStyle.border}`,
                    borderRadius: 'var(--radius-xs)',
                    padding: '8px 10px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '4px'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      {getSeverityIcon(alt.severity)}
                      <span
                        style={{
                          background: badgeStyle.bg,
                          color: badgeStyle.color,
                          border: `1px solid ${badgeStyle.border}`,
                          fontSize: '9px',
                          fontFamily: 'var(--font-mono)',
                          fontWeight: 800,
                          padding: '1px 5px',
                          borderRadius: '2px'
                        }}
                      >
                        {alt.severity}
                      </span>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-muted)' }}>
                        [{alt.source}]
                      </span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-dim)' }}>
                        {new Date(alt.timestamp).toLocaleTimeString()}
                      </span>
                      <button
                        onClick={() => acknowledgeAlert(alt.alert_id)}
                        className="btn-ack"
                        title="Acknowledge alert"
                      >
                        <Check size={11} style={{ marginRight: '3px' }} />
                        ACK
                      </button>
                    </div>
                  </div>

                  <p style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-bright)', margin: 0 }}>
                    {alt.message}
                  </p>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
