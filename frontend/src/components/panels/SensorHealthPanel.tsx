import React from 'react';
import { useObservatory } from '../../context/ObservatoryContext';
import { Activity, CheckCircle2, XCircle, Camera, Wifi } from 'lucide-react';

export const SensorHealthPanel: React.FC = () => {
  const { telemetry } = useObservatory();
  const { sensor_status } = telemetry;

  const sensorList = [
    { name: 'DHT22 Temp/Hum', pin: 'GPIO4', ok: sensor_status.dht22, bus: 'OneWire 3.3V' },
    { name: 'BH1750 Lux', pin: 'GPIO21/22', ok: sensor_status.bh1750, bus: 'I2C (100 kHz)' },
    { name: 'BMP280 Baro', pin: 'GPIO21/22', ok: sensor_status.bmp280, bus: 'I2C 0x76' },
    { name: 'Rain Detector', pin: 'GPIO34', ok: sensor_status.rain, bus: 'ADC1 Ch6' },
    { name: 'ESP32-CAM Node', pin: telemetry.camera_ip || 'Wi-Fi', ok: telemetry.camera_online, bus: 'HTTP Bridge' }
  ];

  return (
    <div className="hud-panel">
      <div className="panel-header">
        <div className="panel-title">
          <Activity size={14} />
          <span>Sensor Bus Matrix</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-muted)' }}>
          <Wifi size={12} color="var(--cyan-primary)" />
          <span>{telemetry.wifi_rssi} dBm</span>
        </div>
      </div>

      <div className="panel-body">
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {sensorList.map((s) => (
            <div
              key={s.name}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '6px 10px',
                background: 'var(--bg-deep)',
                border: '1px solid var(--border-dim)',
                borderRadius: 'var(--radius-xs)',
                fontFamily: 'var(--font-mono)',
                fontSize: '11px'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                {s.ok ? (
                  <CheckCircle2 size={13} color="var(--status-green)" />
                ) : (
                  <XCircle size={13} color="var(--status-red)" />
                )}
                <span style={{ color: 'var(--text-bright)', fontWeight: 600 }}>{s.name}</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '9px' }}>
                <span style={{ color: 'var(--text-dim)' }}>{s.pin}</span>
                <span
                  style={{
                    color: s.ok ? 'var(--status-green)' : 'var(--status-red)',
                    background: s.ok ? 'rgba(0, 255, 157, 0.1)' : 'rgba(255, 42, 95, 0.1)',
                    padding: '1px 5px',
                    borderRadius: '2px',
                    fontWeight: 700
                  }}
                >
                  {s.ok ? 'HEALTHY' : 'FAULT'}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
