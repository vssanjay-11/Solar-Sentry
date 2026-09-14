import React from 'react';
import { useObservatory } from '../../context/ObservatoryContext';
import { Thermometer, Droplets, Wind, Sun, CloudRain } from 'lucide-react';

export const EnvironmentPanel: React.FC = () => {
  const { telemetry } = useObservatory();

  // Rain raw ADC is 0-4095. Low reading means wet (<2000), high reading means dry (>3500)
  const rainPercentage = Math.max(0, Math.min(100, Math.round((telemetry.rain_raw / 4095) * 100)));

  return (
    <div className="hud-panel">
      <div className="panel-header">
        <div className="panel-title">
          <Thermometer size={14} />
          <span>Microclimate Telemetry</span>
        </div>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-muted)' }}>
          DHT22 / BMP280 / BH1750
        </span>
      </div>

      <div className="panel-body">
        <div className="telemetry-metric-grid">
          {/* Temperature */}
          <div className="metric-card">
            <div className="metric-card-header">
              <span>Ambient Temp</span>
              <Thermometer size={12} color="var(--cyan-primary)" />
            </div>
            <div className="metric-card-val">
              {telemetry.temperature}
              <span className="unit">°C</span>
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)' }}>
              Optical deck sensor
            </div>
          </div>

          {/* Humidity */}
          <div className="metric-card">
            <div className="metric-card-header">
              <span>Relative Humidity</span>
              <Droplets size={12} color={telemetry.humidity > 75 ? 'var(--status-red)' : 'var(--cyan-primary)'} />
            </div>
            <div className="metric-card-val">
              {telemetry.humidity}
              <span className="unit">%</span>
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: telemetry.humidity > 75 ? 'var(--status-red)' : 'var(--text-muted)' }}>
              {telemetry.humidity > 75 ? 'CONDENSATION RISK' : 'Safe envelope (<75%)'}
            </div>
          </div>

          {/* Pressure */}
          <div className="metric-card">
            <div className="metric-card-header">
              <span>Barometric Pres</span>
              <Wind size={12} color="var(--cyan-primary)" />
            </div>
            <div className="metric-card-val">
              {telemetry.pressure}
              <span className="unit">hPa</span>
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)' }}>
              BMP280 I2C 0x76
            </div>
          </div>

          {/* Lux */}
          <div className="metric-card">
            <div className="metric-card-header">
              <span>Illuminance</span>
              <Sun size={12} color={telemetry.lux >= 40000 ? 'var(--solar-gold)' : 'var(--text-muted)'} />
            </div>
            <div className="metric-card-val">
              {telemetry.lux.toLocaleString()}
              <span className="unit">Lux</span>
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: telemetry.lux >= 40000 ? 'var(--solar-gold)' : 'var(--text-muted)' }}>
              {telemetry.lux >= 40000 ? 'Direct Solar LOS' : 'Attenuated / Diffuse'}
            </div>
          </div>
        </div>

        {/* Rain Sensor 12-bit ADC Bar */}
        <div style={{ background: 'var(--bg-deep)', padding: '10px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-dim)', display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontFamily: 'var(--font-mono)', fontSize: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <CloudRain size={13} color={telemetry.rain_detected ? 'var(--status-red)' : 'var(--cyan-primary)'} />
              <span style={{ color: 'var(--text-bright)' }}>Precipitation Sensor (GPIO34 ADC1)</span>
            </div>
            <span style={{ color: telemetry.rain_detected ? 'var(--status-red)' : 'var(--status-green)', fontWeight: 700 }}>
              {telemetry.rain_detected ? 'RAIN DETECTED' : 'DRY SURFACE'}
            </span>
          </div>

          <div style={{ height: '6px', width: '100%', background: 'var(--bg-panel-elevated)', borderRadius: '3px', overflow: 'hidden' }}>
            <div
              style={{
                height: '100%',
                width: `${rainPercentage}%`,
                background: telemetry.rain_detected ? 'var(--status-red)' : 'linear-gradient(90deg, #0099ff, var(--status-green))',
                transition: 'width 0.3s ease'
              }}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)' }}>
            <span>Wet (0 ADC)</span>
            <span style={{ color: 'var(--text-bright)', fontWeight: 700 }}>Raw: {telemetry.rain_raw} / 4095 ADC</span>
            <span>Dry (4095 ADC)</span>
          </div>
        </div>
      </div>
    </div>
  );
};
