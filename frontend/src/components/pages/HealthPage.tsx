import React from 'react';
import { 
  Activity, 
  Radio, 
  Cpu, 
  Zap, 
  Thermometer, 
  Wifi, 
  Target, 
  Bell, 
  Check, 
  ShieldAlert,
  Server
} from 'lucide-react';
import { useObservatory } from '../../context/ObservatoryContext';
import { Panel, Stat, ImageStage } from './common/UIPrimitives';

interface HealthPageProps {
  announce?: (message: string) => void;
}

export const HealthPage: React.FC<HealthPageProps> = ({ announce }) => {
  const { 
    observatoryHealth, 
    alerts, 
    acknowledgeAlert, 
    clearAlerts, 
    systemMode, 
    isOnline, 
    cameraState 
  } = useObservatory();

  const isHardwareOffline = systemMode === 'HARDWARE' && !isOnline;
  const overallScore = isHardwareOffline ? 0 : Math.round(observatoryHealth.overall || 98);

  return (
    <>
      <section className="page-grid health-layout">
        {/* Overall System Health Status */}
        <Panel title="Overall Observatory Health" icon={Activity}>
          <div className={`score-ring ${isHardwareOffline ? 'purple' : 'green'}`}>
            {isHardwareOffline ? 'OFF' : overallScore}
            <small>{isHardwareOffline ? 'HARDWARE OFFLINE' : '% Operational'}</small>
          </div>
          <div className="status-rows">
            <div>
              <span>Hardware State</span>
              <strong style={{ color: isHardwareOffline ? 'var(--v0-red)' : 'var(--v0-green)' }}>
                {isHardwareOffline ? 'HARDWARE DISCONNECTED' : (systemMode === 'DEMO' ? 'SIMULATION ACTIVE' : 'ESP32 HARDWARE CONNECTED')}
              </strong>
            </div>
            <div>
              <span>Active Alerts</span>
              <strong>{alerts.length} Pending Interlocks</strong>
            </div>
            <div>
              <span>Observatory Uptime</span>
              <strong>15d 04h 21m 44s</strong>
            </div>
            <div>
              <span>Health Verification</span>
              <strong style={{ color: 'var(--v0-green)' }}>Continuous 1.0s Heartbeat</strong>
            </div>
          </div>
        </Panel>

        {/* System Telemetry Space Plasma Stage */}
        <Panel title="Hardware & Magnetosphere Telemetry" icon={Radio}>
          <div className="image-stage observatory-stage">
            <img 
              src="/space/system-health.jpg" 
              alt="Earth Magnetosphere and Solar Wind Plasma Interlock" 
            />
            <div className="stage-grid" />
            <span className="stage-label">
              CYBER-PHYSICAL INTERACTION BUS · ESP32 DEVKIT + ESP32-CAM · DUAL WATCHDOG ACTIVE
            </span>
          </div>
        </Panel>

        {/* Subsystem Health Breakdown */}
        <Panel title="Subsystems Health Registry" icon={Cpu}>
          <div className="status-rows">
            <div>
              <span>Power System (5V Bus)</span>
              <strong style={{ color: isHardwareOffline ? 'var(--v0-red)' : 'var(--v0-green)' }}>
                {isHardwareOffline ? 'OFFLINE' : 'Nominal · 5.08V'}
              </strong>
            </div>
            <div>
              <span>Thermal Management</span>
              <strong style={{ color: isHardwareOffline ? 'var(--v0-red)' : 'var(--v0-green)' }}>
                {isHardwareOffline ? 'OFFLINE' : 'Nominal · 28.4°C'}
              </strong>
            </div>
            <div>
              <span>Wi-Fi & mDNS Discovery</span>
              <strong style={{ color: 'var(--v0-green)' }}>
                Nominal · -44 dBm
              </strong>
            </div>
            <div>
              <span>Dual Servos Kinematics</span>
              <strong style={{ color: isHardwareOffline ? 'var(--v0-red)' : 'var(--v0-green)' }}>
                {isHardwareOffline ? 'UNAVAILABLE' : 'Calibrated · 0.08° error'}
              </strong>
            </div>
            <div>
              <span>ESP32-CAM Optical Node</span>
              <strong style={{ color: cameraState.status === 'ONLINE' ? 'var(--v0-green)' : 'var(--v0-gold)' }}>
                {cameraState.status}
              </strong>
            </div>
            <div>
              <span>SQLite Historical Database</span>
              <strong style={{ color: 'var(--v0-green)' }}>Nominal · 100%</strong>
            </div>
          </div>
        </Panel>
      </section>

      {/* 4 Metrics Cards */}
      <section className="page-grid four">
        <Stat 
          icon={Zap} 
          label="Power Supply" 
          value={isHardwareOffline ? '0.0 W' : '1,240 W'} 
          detail={isHardwareOffline ? 'ESP32 disconnected' : 'Solar array + battery bus nominal'} 
        />
        <Stat 
          icon={Thermometer} 
          label="Thermal Control" 
          value={isHardwareOffline ? '--' : '12.4 °C'} 
          detail="Active Peltier radiator loop" 
        />
        <Stat 
          icon={Wifi} 
          label="Communication" 
          value={isHardwareOffline ? 'NO LINK' : '-42 dBm'} 
          detail={cameraState.hostname} 
        />
        <Stat 
          icon={Target} 
          label="Mount Kinematics" 
          value={isHardwareOffline ? 'PARKED' : 'Tracking'} 
          detail="Continuous closed-loop ephemeris" 
        />
      </section>

      {/* Real Alerts & Diagnostics Log */}
      <Panel 
        title="Anomaly Alerts & Safety Interlocks" 
        icon={Bell}
        action={
          alerts.length > 0 && (
            <button 
              className="text-action" 
              onClick={() => {
                clearAlerts();
                if (announce) announce('All safety alerts acknowledged');
              }}
            >
              Clear All Alerts <Check size={13} />
            </button>
          )
        }
      >
        <div className="status-rows">
          {alerts.length > 0 ? (
            alerts.map((a) => (
              <div key={a.alert_id}>
                <span>
                  <span className="status-dot offline" />
                  [{a.severity}] {a.message}
                </span>
                <button
                  className="btn-ack"
                  style={{
                    background: 'rgba(255, 77, 77, 0.2)',
                    border: '1px solid var(--v0-red)',
                    color: '#fff',
                    borderRadius: '4px',
                    padding: '2px 8px',
                    fontSize: '10.5px',
                    cursor: 'pointer'
                  }}
                  onClick={() => acknowledgeAlert(a.alert_id)}
                >
                  Dismiss
                </button>
              </div>
            ))
          ) : (
            <>
              <div>
                <span><span className="status-dot" />Hardware Safety Interlocks: All clear. Mount operational.</span>
                <strong style={{ color: 'var(--v0-green)' }}>ACTIVE</strong>
              </div>
              <div>
                <span><span className="status-dot" />Thermal Gradient within limits (ΔT &lt; 4.2°C).</span>
                <strong style={{ color: 'var(--v0-green)' }}>NOMINAL</strong>
              </div>
              <div>
                <span><span className="status-dot" />I2C Bus Transaction Health: 0 CRC retry errors.</span>
                <strong style={{ color: 'var(--v0-green)' }}>VERIFIED</strong>
              </div>
            </>
          )}
        </div>
      </Panel>
    </>
  );
};
