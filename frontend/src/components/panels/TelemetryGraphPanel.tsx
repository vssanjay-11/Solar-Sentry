import React, { useState } from 'react';
import { useObservatory } from '../../context/ObservatoryContext';
import { LineChart, BarChart3, Clock } from 'lucide-react';
import { TelemetryPoint } from '../../types/telemetry';

type MetricKey = 'ors' | 'temperature' | 'humidity' | 'lux' | 'pan';

export const TelemetryGraphPanel: React.FC = () => {
  const { telemetryHistory } = useObservatory();
  const [selectedMetric, setSelectedMetric] = useState<MetricKey>('ors');
  const [timeRange, setTimeRange] = useState<'15m' | '1h' | '6h' | '24h'>('1h');

  const metricConfigs: Record<MetricKey, { label: string; unit: string; color: string; min: number; max: number }> = {
    ors: { label: 'Readiness Score (ORS)', unit: '%', color: 'var(--cyan-primary)', min: 0, max: 100 },
    temperature: { label: 'Temperature', unit: '°C', color: '#ff7733', min: 20, max: 40 },
    humidity: { label: 'Relative Humidity', unit: '%', color: '#00ccff', min: 20, max: 100 },
    lux: { label: 'Ambient Lux', unit: 'Lux', color: 'var(--solar-gold)', min: 0, max: 70000 },
    pan: { label: 'Actuator Pan Pose', unit: '°', color: 'var(--status-green)', min: 0, max: 180 }
  };

  const cfg = metricConfigs[selectedMetric];
  const points = telemetryHistory.slice(-25);

  // SVG Chart Dimensions
  const svgWidth = 600;
  const svgHeight = 160;
  const paddingLeft = 45;
  const paddingRight = 15;
  const paddingTop = 15;
  const paddingBottom = 25;
  const plotWidth = svgWidth - paddingLeft - paddingRight;
  const plotHeight = svgHeight - paddingTop - paddingBottom;

  // Calculate coordinates
  const getX = (idx: number, total: number) => {
    if (total <= 1) return paddingLeft;
    return paddingLeft + (idx / (total - 1)) * plotWidth;
  };

  const getY = (val: number) => {
    const clamped = Math.max(cfg.min, Math.min(cfg.max, val));
    const norm = (clamped - cfg.min) / (cfg.max - cfg.min);
    return paddingTop + (1 - norm) * plotHeight;
  };

  const pathD = points.map((p, i) => {
    const x = getX(i, points.length);
    const y = getY(p[selectedMetric]);
    return `${i === 0 ? 'M' : 'L'} ${x} ${y}`;
  }).join(' ');

  return (
    <div className="hud-panel">
      <div className="panel-header">
        <div className="panel-title">
          <BarChart3 size={14} />
          <span>Historical Telemetry Streams</span>
        </div>

        {/* Controls: Metric Selector & Time Window */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <select
            value={selectedMetric}
            onChange={(e) => setSelectedMetric(e.target.value as MetricKey)}
            style={{
              background: 'var(--bg-panel-elevated)',
              border: '1px solid var(--border-mid)',
              color: 'var(--text-bright)',
              fontFamily: 'var(--font-mono)',
              fontSize: '10px',
              padding: '2px 6px',
              borderRadius: 'var(--radius-xs)',
              cursor: 'pointer'
            }}
          >
            <option value="ors">ORS Score</option>
            <option value="temperature">Temperature (°C)</option>
            <option value="humidity">Humidity (%)</option>
            <option value="lux">Illuminance (Lux)</option>
            <option value="pan">Pan Angle (°)</option>
          </select>

          <div style={{ display: 'flex', gap: '2px' }}>
            {(['15m', '1h', '6h', '24h'] as const).map((r) => (
              <button
                key={r}
                onClick={() => setTimeRange(r)}
                style={{
                  background: timeRange === r ? 'var(--cyan-dim)' : 'var(--bg-deep)',
                  color: timeRange === r ? '#000' : 'var(--text-muted)',
                  border: '1px solid var(--border-dim)',
                  padding: '2px 6px',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '9px',
                  borderRadius: '2px',
                  cursor: 'pointer',
                  fontWeight: timeRange === r ? 800 : 400
                }}
              >
                {r}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="panel-body" style={{ padding: '8px' }}>
        <svg viewBox={`0 0 ${svgWidth} ${svgHeight}`} style={{ width: '100%', height: '180px', display: 'block' }}>
          {/* Horizontal Gridlines & Y-Axis Labels */}
          {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
            const y = paddingTop + ratio * plotHeight;
            const val = Math.round(cfg.max - ratio * (cfg.max - cfg.min));
            return (
              <g key={ratio}>
                <line
                  x1={paddingLeft}
                  y1={y}
                  x2={svgWidth - paddingRight}
                  y2={y}
                  stroke="var(--border-dim)"
                  strokeDasharray="3 3"
                />
                <text
                  x={paddingLeft - 6}
                  y={y + 3}
                  textAnchor="end"
                  fill="var(--text-dim)"
                  style={{ fontFamily: 'var(--font-mono)', fontSize: '8px' }}
                >
                  {val}{cfg.unit}
                </text>
              </g>
            );
          })}

          {/* Sparkline Area Fill */}
          {points.length > 0 && (
            <path
              d={`${pathD} L ${getX(points.length - 1, points.length)} ${paddingTop + plotHeight} L ${paddingLeft} ${paddingTop + plotHeight} Z`}
              fill={cfg.color}
              fillOpacity={0.12}
            />
          )}

          {/* Main Trend Line */}
          {points.length > 0 && (
            <path
              d={pathD}
              fill="none"
              stroke={cfg.color}
              strokeWidth={2}
              style={{ transition: 'd 0.3s ease' }}
            />
          )}

          {/* Dots on Data Points */}
          {points.map((p, i) => {
            const cx = getX(i, points.length);
            const cy = getY(p[selectedMetric]);
            return (
              <circle
                key={i}
                cx={cx}
                cy={cy}
                r={i === points.length - 1 ? 4 : 2}
                fill={cfg.color}
                stroke="var(--bg-deep)"
                strokeWidth={1}
              />
            );
          })}

          {/* Time Labels on X-Axis */}
          {points.length > 0 && (
            <>
              <text
                x={paddingLeft}
                y={svgHeight - 6}
                fill="var(--text-dim)"
                style={{ fontFamily: 'var(--font-mono)', fontSize: '8px' }}
              >
                {points[0].timestamp}
              </text>
              <text
                x={svgWidth - paddingRight}
                y={svgHeight - 6}
                textAnchor="end"
                fill="var(--text-dim)"
                style={{ fontFamily: 'var(--font-mono)', fontSize: '8px' }}
              >
                {points[points.length - 1].timestamp} (NOW)
              </text>
            </>
          )}
        </svg>
      </div>
    </div>
  );
};
