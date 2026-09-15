import React, { useState } from 'react';
import { 
  Settings, 
  Bell, 
  Cpu, 
  ShieldCheck, 
  Wifi, 
  RefreshCw, 
  ExternalLink,
  Save,
  CheckCircle,
  AlertTriangle,
  Info
} from 'lucide-react';
import { useObservatory } from '../../context/ObservatoryContext';
import { Panel } from './common/UIPrimitives';

interface SettingsPageProps {
  announce: (message: string) => void;
}

export const SettingsPage: React.FC<SettingsPageProps> = ({ announce }) => {
  const { 
    systemMode, 
    setSystemMode, 
    cameraState, 
    rediscoverCamera, 
    updateCameraUrl,
    isOnline 
  } = useObservatory();

  const [activeTab, setActiveTab] = useState<'General' | 'Hardware' | 'Notifications' | 'About'>('Hardware');
  const [manualIp, setManualIp] = useState<string>(cameraState.ip || '');
  const [isScanning, setIsScanning] = useState<boolean>(false);
  const [saveNotice, setSaveNotice] = useState<string | null>(null);

  const handleScanDevices = async () => {
    setIsScanning(true);
    announce(`Scanning local network for ${cameraState.hostname}...`);
    try {
      await rediscoverCamera();
      announce('Hardware scan complete.');
    } finally {
      setIsScanning(false);
    }
  };

  const handleSaveManualConfig = async () => {
    if (!manualIp) return;
    const fullUrl = manualIp.startsWith('http') ? manualIp : `http://${manualIp}`;
    await updateCameraUrl(fullUrl);
    setSaveNotice('Camera target URL updated successfully.');
    announce('Camera URL configuration updated');
    setTimeout(() => setSaveNotice(null), 3000);
  };

  return (
    <>
      {/* Settings Navigation Tabs */}
      <div className="settings-tabs">
        {(['Hardware', 'General', 'Notifications', 'About'] as const).map((tab) => (
          <button
            key={tab}
            className={activeTab === tab ? 'active' : ''}
            onClick={() => setActiveTab(tab)}
          >
            {tab === 'Hardware' ? 'Hardware & Camera' : tab}
          </button>
        ))}
      </div>

      {activeTab === 'Hardware' && (
        <section className="page-grid settings-layout">
          {/* Operational Mode Selection Panel */}
          <Panel title="System Operational Mode" icon={Cpu}>
            <div className="status-rows">
              <div>
                <span>Current Mode</span>
                <strong style={{ color: systemMode === 'DEMO' ? 'var(--v0-gold)' : 'var(--v0-green)' }}>
                  {systemMode} MODE
                </strong>
              </div>
              <div>
                <span>ESP32 Physical Link</span>
                <strong style={{ color: isOnline ? 'var(--v0-green)' : 'var(--v0-red)' }}>
                  {isOnline ? 'ONLINE' : 'OFFLINE'}
                </strong>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
              <button
                className={`primary-action ${systemMode === 'DEMO' ? 'active' : ''}`}
                style={{ flex: 1, padding: '9px', background: systemMode === 'DEMO' ? '#075de0' : 'rgba(5, 28, 56, 0.6)' }}
                onClick={async () => {
                  await setSystemMode('DEMO');
                  announce('Switched to DEMO MODE (Simulation active)');
                }}
              >
                DEMO MODE
              </button>
              <button
                className={`primary-action ${systemMode === 'HARDWARE' ? 'active' : ''}`}
                style={{ flex: 1, padding: '9px', background: systemMode === 'HARDWARE' ? '#075de0' : 'rgba(5, 28, 56, 0.6)' }}
                onClick={async () => {
                  await setSystemMode('HARDWARE');
                  announce('Switched to HARDWARE MODE (Real ESP32 & Camera)');
                }}
              >
                HARDWARE MODE
              </button>
            </div>

            <p style={{ fontSize: '11px', color: '#8da4c5', marginTop: '12px', lineHeight: 1.4 }}>
              <strong>DEMO MODE:</strong> Autonomous simulation with physics-based telemetry and synthetic optical stream.<br />
              <strong>HARDWARE MODE:</strong> Directly binds to real ESP32 sensors & ESP32-CAM optical node. Strict zero fake values policy when offline.
            </p>
          </Panel>

          {/* ESP32-CAM Discovery & mDNS Panel */}
          <Panel title="ESP32-CAM Dynamic Discovery" icon={Wifi}>
            <div className="status-rows">
              <div>
                <span>Target Hostname</span>
                <strong>{cameraState.hostname}</strong>
              </div>
              <div>
                <span>Discovered IP</span>
                <strong style={{ color: cameraState.status === 'ONLINE' ? 'var(--v0-green)' : 'var(--v0-gold)' }}>
                  {cameraState.ip || 'Auto-Resolving...'}
                </strong>
              </div>
              <div>
                <span>Discovery State</span>
                <strong style={{ textTransform: 'uppercase' }}>{cameraState.status}</strong>
              </div>
              <div>
                <span>Discovery Protocol</span>
                <strong>mDNS / LAN Multicast (Port 80)</strong>
              </div>
              <div>
                <span>Backend MJPEG Proxy</span>
                <strong style={{ color: 'var(--v0-cyan)' }}>/api/v1/camera/stream</strong>
              </div>
            </div>

            <button 
              className="primary-action wide"
              onClick={handleScanDevices}
              disabled={isScanning}
            >
              <RefreshCw size={14} className={isScanning ? 'animate-spin' : ''} />
              {isScanning ? 'Scanning Network...' : 'Scan / Rediscover ESP32-CAM'}
            </button>

            {/* Manual Fallback URL Input */}
            <div style={{ marginTop: '14px', paddingTop: '10px', borderTop: '1px solid rgba(43, 158, 255, 0.2)' }}>
              <label style={{ fontSize: '11px', color: '#a0c4e8', display: 'block', marginBottom: '6px' }}>
                Manual Camera IP Fallback (Optional):
              </label>
              <div style={{ display: 'flex', gap: '6px' }}>
                <input
                  type="text"
                  value={manualIp}
                  onChange={(e) => setManualIp(e.target.value)}
                  placeholder="e.g. 192.168.1.120"
                  style={{
                    flex: 1,
                    background: 'rgba(3, 22, 45, 0.8)',
                    border: '1px solid rgba(27, 143, 233, 0.45)',
                    borderRadius: '6px',
                    color: '#fff',
                    padding: '6px 10px',
                    fontSize: '11.5px',
                    outline: 'none'
                  }}
                />
                <button
                  onClick={handleSaveManualConfig}
                  style={{
                    background: '#075de0',
                    border: '1px solid #17befe',
                    color: '#fff',
                    padding: '6px 12px',
                    borderRadius: '6px',
                    fontSize: '11px',
                    cursor: 'pointer'
                  }}
                >
                  <Save size={13} style={{ marginRight: '4px' }} /> Save
                </button>
              </div>
              {saveNotice && (
                <p style={{ fontSize: '10.5px', color: 'var(--v0-green)', marginTop: '4px' }}>
                  {saveNotice}
                </p>
              )}
            </div>
          </Panel>

          {/* Hardware Peripherals Diagnostic */}
          <Panel title="Peripherals & Actuators" icon={Cpu}>
            <div className="status-rows">
              <div>
                <span>Pan Mount Servo</span>
                <strong>GPIO 18 · PWM 50Hz</strong>
              </div>
              <div>
                <span>Tilt Mount Servo</span>
                <strong>GPIO 19 · PWM 50Hz</strong>
              </div>
              <div>
                <span>DHT22 Humidity / Temp</span>
                <strong>GPIO 4 · 1-Wire</strong>
              </div>
              <div>
                <span>BMP280 Barometer</span>
                <strong>I2C 0x76 (SDA 21, SCL 22)</strong>
              </div>
              <div>
                <span>BH1750 Light Lux</span>
                <strong>I2C 0x23 (SDA 21, SCL 22)</strong>
              </div>
              <div>
                <span>Analog Rain Sensor</span>
                <strong>ADC1 CH6 (GPIO 34)</strong>
              </div>
            </div>
          </Panel>
        </section>
      )}

      {activeTab === 'General' && (
        <section className="page-grid settings-layout">
          <Panel title="General Preferences" icon={Settings}>
            <div className="status-rows">
              <div>
                <span>Application Theme</span>
                <strong>Dark (Astronomical Space)</strong>
              </div>
              <div>
                <span>Language</span>
                <strong>English (International)</strong>
              </div>
              <div>
                <span>Coordinate Frame</span>
                <strong>Horizontal (Azimuth / Elevation)</strong>
              </div>
              <div>
                <span>Scientific Units</span>
                <strong>Metric (km, °C, hPa, lux)</strong>
              </div>
              <div>
                <span>Default Landing Page</span>
                <strong>Home Dashboard</strong>
              </div>
            </div>
          </Panel>
        </section>
      )}

      {activeTab === 'Notifications' && (
        <section className="page-grid settings-layout">
          <Panel title="Alerts & Notification Channels" icon={Bell}>
            <div className="toggle-rows">
              <div>
                <span>Critical Safety Interlocks</span>
                <i><b /></i>
              </div>
              <div>
                <span>Solar Flare Inferences (Class C/M)</span>
                <i><b /></i>
              </div>
              <div>
                <span>Sensor Degradation Warnings</span>
                <i><b /></i>
              </div>
              <div>
                <span>Camera Disconnection Alarms</span>
                <i><b /></i>
              </div>
            </div>
          </Panel>
        </section>
      )}

      {activeTab === 'About' && (
        <section className="page-grid settings-layout">
          <Panel title="About Solar Sentry" icon={Info}>
            <div style={{ padding: '10px 0', fontSize: '12px', lineHeight: 1.6, color: '#c4dbf8' }}>
              <h3 style={{ color: '#fff', fontSize: '16px', margin: '0 0 6px' }}>Solar Sentry v1.0.0</h3>
              <p>
                An autonomous cyber-physical solar tracking and space-weather observation platform.
                Featuring dual-axis kinematic mount control, multi-sensor environmental telemetry fusion,
                dynamic ESP32-CAM optical vision pipeline, and Agent 8 Explainable AI decision engine.
              </p>
              <div className="status-rows" style={{ marginTop: '14px' }}>
                <div>
                  <span>Architecture</span>
                  <strong>Cyber-Physical IoT + FastAPI + React</strong>
                </div>
                <div>
                  <span>Lead Developer</span>
                  <strong>Sanjay V. S.</strong>
                </div>
                <div>
                  <span>Release Branch</span>
                  <strong style={{ color: 'var(--v0-green)' }}>main</strong>
                </div>
              </div>
            </div>
          </Panel>
        </section>
      )}
    </>
  );
};
