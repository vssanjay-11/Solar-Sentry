import React from 'react';
import { useObservatory } from '../../context/ObservatoryContext';
import { TrendingUp, TrendingDown, Minus, HelpCircle, Clock } from 'lucide-react';
import { TrendDirection } from '../../types/intelligence';

export const PredictionPanel: React.FC = () => {
  const { predictions } = useObservatory();

  const getTrendIcon = (trend: TrendDirection) => {
    switch (trend) {
      case 'INCREASING': return <TrendingUp size={12} color="var(--status-green)" />;
      case 'SLIGHT_DECLINE':
      case 'DEGRADING': return <TrendingDown size={12} color="var(--status-red)" />;
      case 'STABLE': return <Minus size={12} color="var(--cyan-primary)" />;
      default: return <HelpCircle size={12} color="var(--text-muted)" />;
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 75) return 'var(--status-green)';
    if (score >= 50) return 'var(--status-yellow)';
    return 'var(--status-red)';
  };

  const horizons = [
    { label: '+15 MIN', data: predictions.horizon_15m },
    { label: '+30 MIN', data: predictions.horizon_30m },
    { label: '+60 MIN', data: predictions.horizon_60m },
  ];

  return (
    <div className="hud-panel">
      <div className="panel-header">
        <div className="panel-title">
          <Clock size={14} />
          <span>Predictive Readiness Forecast</span>
        </div>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-muted)' }}>
          AGENT 6 MULTI-HORIZON AI
        </span>
      </div>

      <div className="panel-body">
        <div className="prediction-horizon-grid">
          {horizons.map((h) => (
            <div key={h.label} className="horizon-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span className="title">{h.label}</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
                  {getTrendIcon(h.data.trend)}
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)' }}>
                    {h.data.trend}
                  </span>
                </div>
              </div>

              <div className="score" style={{ color: getScoreColor(h.data.score) }}>
                {h.data.score}
                <span style={{ fontSize: '10px', color: 'var(--text-muted)', marginLeft: '3px' }}>ORS</span>
              </div>

              {/* Confidence Interval Error Envelope */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', marginTop: '2px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: 'var(--font-mono)', fontSize: '8px', color: 'var(--text-dim)' }}>
                  <span>CI: {h.data.confidence_lower}</span>
                  <span>{h.data.confidence_upper}</span>
                </div>
                <div style={{ height: '3px', width: '100%', background: 'var(--bg-panel-elevated)', borderRadius: '2px', position: 'relative' }}>
                  <div
                    style={{
                      position: 'absolute',
                      left: `${h.data.confidence_lower}%`,
                      width: `${Math.max(4, h.data.confidence_upper - h.data.confidence_lower)}%`,
                      height: '100%',
                      background: 'var(--cyan-primary)',
                      borderRadius: '2px'
                    }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>

        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-dim)', textAlign: 'center', marginTop: '2px' }}>
          *Probabilistic forecasting combines microclimate trends with solar elevation physics.
        </div>
      </div>
    </div>
  );
};
