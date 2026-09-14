import React from 'react';
import { useObservatory } from '../../context/ObservatoryContext';
import { Gauge, Sparkles } from 'lucide-react';

export const ReadinessGaugePanel: React.FC = () => {
  const { orsScore, orsFactors } = useObservatory();

  // SVG circular gauge properties
  const radius = 54;
  const stroke = 8;
  const normalizedRadius = radius - stroke * 2;
  const circumference = normalizedRadius * 2 * Math.PI;
  const strokeDashoffset = circumference - (orsScore / 100) * circumference;

  const getGaugeColor = (score: number) => {
    if (score >= 75) return 'var(--status-green)';
    if (score >= 50) return 'var(--status-yellow)';
    return 'var(--status-red)';
  };

  const factors = [
    { label: 'Solar Elevation', value: orsFactors.solar_elevation },
    { label: 'Atmos Seeing', value: orsFactors.atmospheric_seeing },
    { label: 'Cloud Transparency', value: orsFactors.cloud_transparency },
    { label: 'Sensor Integrity', value: orsFactors.sensor_health },
    { label: 'Tracking Stability', value: orsFactors.tracking_stability }
  ];

  return (
    <div className="hud-panel">
      <div className="panel-header">
        <div className="panel-title">
          <Gauge size={14} />
          <span>Observation Readiness</span>
        </div>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: getGaugeColor(orsScore), fontWeight: 700 }}>
          {orsScore >= 75 ? 'NOMINAL' : orsScore >= 50 ? 'MARGINAL' : 'INHIBITED'}
        </span>
      </div>

      <div className="panel-body">
        <div className="ors-gauge-container">
          <svg className="ors-svg-gauge" viewBox="0 0 120 120">
            {/* Background Track */}
            <circle
              stroke="var(--border-mid)"
              fill="transparent"
              strokeWidth={stroke}
              r={normalizedRadius}
              cx="60"
              cy="60"
            />
            {/* Progress Arc */}
            <circle
              stroke={getGaugeColor(orsScore)}
              fill="transparent"
              strokeWidth={stroke}
              strokeDasharray={`${circumference} ${circumference}`}
              style={{ strokeDashoffset, transition: 'stroke-dashoffset 0.5s ease, stroke 0.5s ease' }}
              strokeLinecap="round"
              r={normalizedRadius}
              cx="60"
              cy="60"
              transform="rotate(-90 60 60)"
            />
            {/* Center Score Text */}
            <text
              x="60"
              y="56"
              textAnchor="middle"
              fill="var(--text-bright)"
              style={{ fontFamily: 'var(--font-mono)', fontSize: '24px', fontWeight: 800 }}
            >
              {orsScore}
            </text>
            <text
              x="60"
              y="74"
              textAnchor="middle"
              fill="var(--text-muted)"
              style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', letterSpacing: '0.8px' }}
            >
              ORS SCORE
            </text>
          </svg>

          {/* Sub-factor Breakdown Bars */}
          <div className="ors-factors-list">
            {factors.map((f) => (
              <div key={f.label} className="factor-row">
                <span className="name">{f.label}</span>
                <div className="factor-bar-wrapper">
                  <div
                    className="factor-bar-fill"
                    style={{
                      width: `${f.value}%`,
                      backgroundColor: f.value >= 70 ? 'var(--cyan-primary)' : f.value >= 40 ? 'var(--status-yellow)' : 'var(--status-red)'
                    }}
                  />
                </div>
                <span style={{ width: '26px', textAlign: 'right', fontWeight: 700 }}>{f.value}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
