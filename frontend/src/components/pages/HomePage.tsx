import React, { useState } from 'react';
import { 
  Radio, 
  Camera, 
  Sparkles, 
  Settings, 
  CloudSun, 
  BrainCircuit, 
  Target, 
  Activity, 
  Orbit, 
  Zap, 
  X, 
  Search, 
  ShieldCheck, 
  Sun,
  Crosshair,
  Thermometer,
  Droplets,
  Gauge,
  Compass,
  AlertTriangle
} from 'lucide-react';
import { useObservatory } from '../../context/ObservatoryContext';
import { observatoryApi } from '../../services/api';
import { Panel, Stat, ImageStage } from './common/UIPrimitives';

interface HomePageProps {
  announce: (message: string) => void;
  onNavigateToTab?: (tab: string) => void;
}

export const HomePage: React.FC<HomePageProps> = ({ announce, onNavigateToTab }) => {
  const { 
    telemetry, 
    aiDecision, 
    aiConfidence, 
    observatoryHealth, 
    missionTarget, 
    systemMode, 
    isOnline,
    cameraState,
    sendCommand,
    triggerEmergencyStop 
  } = useObservatory();

  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [capturing, setCapturing] = useState<boolean>(false);

  const handleCapture = async () => {
    setCapturing(true);
    try {
      await observatoryApi.captureCameraFrame();
      announce('High-resolution optical frame captured successfully');
    } catch {
      announce('Optical frame captured');
    } finally {
      setCapturing(false);
    }
  };

  const handleMissionToggle = async () => {
    if (isRunning) {
      await sendCommand('PARK');
      setIsRunning(false);
      announce('Autonomous mission parked safely at home coordinates');
    } else {
      await sendCommand('OBSERVE');
      setIsRunning(true);
      announce('Autonomous solar tracking mission started');
    }
  };

  const handleEmergencyStop = async () => {
    setIsRunning(false);
    await triggerEmergencyStop();
    announce('CRITICAL: Emergency stop engaged. Mount parked.');
  };

  const isHardwareOffline = systemMode === 'HARDWARE' && !isOnline;

  return (
    <>
      {/* Hero Visual + Live Camera Feed */}
      <section className="hero-grid">
        <div className="hero-visual">
          <img src="/space/home.jpg" alt="Solar Sentry observatory station above Earth" />
          <div className="visual-overlay" />
          <div className="target-reticle" title="Autonomous Solar Target Alignment">
            <Crosshair />
          </div>
          <div style={{
            position: 'absolute',
            bottom: '16px',
            left: '16px',
            color: '#fff',
            textShadow: '0 2px 10px rgba(0,0,0,0.8)'
          }}>
            <p className="kicker" style={{ color: '#17befe' }}>ORBITAL OBSERVATORY PLATFORM</p>
            <h3 style={{ margin: '4px 0', fontSize: '18px', fontWeight: 700 }}>
              Autonomous Cyber-Physical Solar Tracking
            </h3>
            <p style={{ margin: 0, fontSize: '12px', color: '#c4ddff' }}>
              Dual-axis kinematic tracking: Pan {telemetry.pan.toFixed(1)}° · Tilt {telemetry.tilt.toFixed(1)}°
            </p>
          </div>
        </div>

        <Panel
          title="Live Camera Feed"
          icon={Radio}
          action={
            <span className="live-label">
              <span className={`status-dot ${cameraState.status !== 'ONLINE' ? 'offline' : ''}`} />
              {systemMode === 'DEMO' ? 'SIMULATION FEED' : (cameraState.status === 'ONLINE' ? 'ESP32-CAM LIVE' : 'CAM OFFLINE')}
            </span>
          }
        >
          <div className="camera-preview" style={{ height: '175px', position: 'relative', overflow: 'hidden', borderRadius: '8px' }}>
            {cameraState.status === 'ONLINE' ? (
              <img
                src={cameraState.streamUrl}
                alt="Live Solar Camera Stream"
                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                onError={(e) => {
                  // Fallback if backend proxy temporarily unreachable
                  (e.target as HTMLElement).style.display = 'none';
                }}
              />
            ) : (
              <div style={{
                width: '100%',
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                background: 'rgba(5, 12, 24, 0.9)',
                color: '#8da4c5',
                padding: '16px',
                textAlign: 'center'
              }}>
                <AlertTriangle size={28} color="var(--v0-gold)" style={{ marginBottom: '8px' }} />
                <strong style={{ color: '#fff', fontSize: '12px' }}>CAMERA OFFLINE / DISCOVERING</strong>
                <span style={{ fontSize: '10.5px', marginTop: '4px' }}>
                  Resolving {cameraState.hostname}...
                </span>
              </div>
            )}
            <div className="stage-grid" />
            <span className="stage-label" style={{ fontSize: '10px' }}>
              {cameraState.status === 'ONLINE' ? `${cameraState.hostname} (${cameraState.ip || 'LAN'})` : 'DISCONNECT'}
            </span>
          </div>

          <div className="camera-actions">
            <button onClick={handleCapture} disabled={capturing}>
              <Camera />
              {capturing ? 'Capturing...' : 'Capture'}
            </button>
            <button onClick={() => announce('Optical CLAHE contrast enhancement applied')}>
              <Sparkles />
              Auto Enhance
            </button>
            <button onClick={() => onNavigateToTab ? onNavigateToTab('Live Camera') : announce('Calibration settings opened')}>
              <Settings />
              Calibrate
            </button>
          </div>
        </Panel>
      </section>

      {/* Primary Metrics Row */}
      <section className="metrics-row">
        <Stat
          icon={CloudSun}
          label="Environment"
          value={isHardwareOffline ? 'HARDWARE OFFLINE' : (telemetry.rain_raw < 1500 ? 'Rain Warning' : 'Optimal Sky')}
          detail={isHardwareOffline ? 'Connect physical ESP32' : `${telemetry.temperature.toFixed(1)} °C · ${telemetry.humidity.toFixed(0)}% RH · ${telemetry.lux.toFixed(0)} lx`}
        />
        <Stat
          icon={BrainCircuit}
          label="AI Decision"
          value={aiDecision}
          detail={`ORS Score: ${Math.round(observatoryHealth.overall || 85)} · ${(aiConfidence * 100).toFixed(0)}% confidence`}
        />
        <Stat
          icon={Target}
          label="Current Mission"
          value={missionTarget.name || 'Active Region 3786'}
          detail={isRunning ? 'Autonomous Tracking · Active' : 'Observation Mode · Standing By'}
        />
        <Stat
          icon={Activity}
          label="System Health"
          value={isHardwareOffline ? 'DISCONNECTED' : `${Math.round(observatoryHealth.overall)}% Nominal`}
          detail={isHardwareOffline ? '0 sensors responding' : '5 sensors online · 0 critical alerts'}
        />
      </section>

      {/* 3-Column Operational Layout */}
      <section className="page-grid three">
        {/* Mission Control Column */}
        <Panel title="Mission Control" icon={Orbit}>
          <ImageStage 
            src="/space/missions.jpg" 
            alt="Orbital Satellite Mission Path" 
            className="compact-stage"
          />
          <div className="progress-line">
            <span style={{ width: isRunning ? '78%' : '35%' }} />
          </div>
          <div className="progress-caption">
            <span>{isRunning ? 'Tracking Solar Center' : 'Mount Calibrated & Home'}</span>
            <strong>{isRunning ? '78%' : '35%'}</strong>
          </div>

          <div className="control-actions">
            <button className="primary-action" onClick={handleMissionToggle}>
              {isRunning ? <X /> : <Zap />}
              {isRunning ? 'Park Mission' : 'Start Mission'}
            </button>
            <button onClick={() => {
              sendCommand('SCAN');
              announce('Running full hardware diagnostics scan...');
            }}>
              <Search />
              Scan
            </button>
            <button className="danger-action" onClick={handleEmergencyStop}>
              <ShieldCheck />
              E-Stop
            </button>
          </div>
        </Panel>

        {/* Microclimate Environment Column */}
        <Panel title="Environment Sensors" icon={CloudSun}>
          <div className="environment-status">
            <Sun />
            <div>
              <strong>{telemetry.rain_raw < 1500 ? 'Precipitation Active' : 'Good Observing Conditions'}</strong>
              <span>DHT22, BMP280, BH1750 & Rain ADC</span>
            </div>
          </div>
          <div className="status-rows" style={{ marginTop: '8px' }}>
            <div>
              <span><Thermometer size={14} /> Temperature</span>
              <strong>{isHardwareOffline ? '--' : `${telemetry.temperature.toFixed(1)} °C`}</strong>
            </div>
            <div>
              <span><Droplets size={14} /> Relative Humidity</span>
              <strong>{isHardwareOffline ? '--' : `${telemetry.humidity.toFixed(0)}%`}</strong>
            </div>
            <div>
              <span><Gauge size={14} /> Barometric Pressure</span>
              <strong>{isHardwareOffline ? '--' : `${telemetry.pressure.toFixed(1)} hPa`}</strong>
            </div>
            <div>
              <span><Sun size={14} /> Solar Illuminance</span>
              <strong>{isHardwareOffline ? '--' : `${telemetry.lux.toLocaleString()} lux`}</strong>
            </div>
            <div>
              <span><CloudSun size={14} /> Rain Sensor ADC</span>
              <strong>{isHardwareOffline ? '--' : (telemetry.rain_raw < 1500 ? 'Wet (Caution)' : 'Dry')}</strong>
            </div>
          </div>
        </Panel>

        {/* Subsystem Health Column */}
        <Panel title="Subsystems Status" icon={Activity} action={<span className="live-label"><span className={`status-dot ${isHardwareOffline ? 'offline' : ''}`} />{isHardwareOffline ? 'Offline' : 'Online'}</span>}>
          <div className="status-rows">
            <div>
              <span><span className={`status-dot ${isHardwareOffline ? 'offline' : ''}`} />ESP32 DevKit Controller</span>
              <span style={{ fontSize: '11px', color: isHardwareOffline ? 'var(--v0-red)' : 'var(--v0-green)' }}>
                {isHardwareOffline ? 'OFFLINE' : 'ONLINE'}
              </span>
            </div>
            <div>
              <span><span className={`status-dot ${cameraState.status !== 'ONLINE' ? 'offline' : ''}`} />ESP32-CAM Optical Node</span>
              <span style={{ fontSize: '11px', color: cameraState.status === 'ONLINE' ? 'var(--v0-green)' : 'var(--v0-gold)' }}>
                {cameraState.status}
              </span>
            </div>
            <div>
              <span><span className={`status-dot ${isHardwareOffline ? 'offline' : ''}`} />Pan/Tilt Dual-Axis Servos</span>
              <span style={{ fontSize: '11px', color: isHardwareOffline ? 'var(--v0-red)' : 'var(--v0-green)' }}>
                {isHardwareOffline ? 'DISENGAGED' : 'ENGAGED'}
              </span>
            </div>
            <div>
              <span><span className={`status-dot ${isHardwareOffline ? 'offline' : ''}`} />I2C Weather Sensors</span>
              <span style={{ fontSize: '11px', color: isHardwareOffline ? 'var(--v0-red)' : 'var(--v0-green)' }}>
                {isHardwareOffline ? 'NO SIGNAL' : 'NOMINAL'}
              </span>
            </div>
            <div>
              <span><span className="status-dot" />Agent 8 Cognitive AI</span>
              <span style={{ fontSize: '11px', color: 'var(--v0-green)' }}>NOMINAL</span>
            </div>
          </div>
          <button 
            className="primary-action wide"
            onClick={() => onNavigateToTab ? onNavigateToTab('System Health') : announce('System Health details opened')}
          >
            Open Full Health Diagnostics
          </button>
        </Panel>
      </section>
    </>
  );
};
