import React, { useState } from 'react';
import { ObservatoryProvider, useObservatory } from './context/ObservatoryContext';
import { Header } from './components/header/Header';
import { SystemStatePanel } from './components/panels/SystemStatePanel';
import { ReadinessGaugePanel } from './components/panels/ReadinessGaugePanel';
import { EnvironmentPanel } from './components/panels/EnvironmentPanel';
import { SensorHealthPanel } from './components/panels/SensorHealthPanel';
import { ObservatoryHealthPanel } from './components/panels/ObservatoryHealthPanel';
import { AnomalyAlertsPanel } from './components/panels/AnomalyAlertsPanel';
import { SolarVisionPanel } from './components/panels/SolarVisionPanel';
import { SolarAnalysisPanel } from './components/panels/SolarAnalysisPanel';
import { PredictionPanel } from './components/panels/PredictionPanel';
import { AIDecisionPanel } from './components/panels/AIDecisionPanel';
import { MissionControlPanel } from './components/panels/MissionControlPanel';
import { MissionTimelinePanel } from './components/panels/MissionTimelinePanel';
import { DigitalTwinPanel } from './components/panels/DigitalTwinPanel';
import { TelemetryGraphPanel } from './components/panels/TelemetryGraphPanel';
import { MissionReplayPanel } from './components/panels/MissionReplayPanel';
import { EventLogPanel } from './components/panels/EventLogPanel';
import { CommandControlPanel } from './components/panels/CommandControlPanel';
import { ExplainableAIModal } from './components/panels/ExplainableAIModal';
import { CameraVisionDeck } from './components/panels/CameraVisionDeck';
import { 
  Compass, 
  Activity, 
  Film, 
  Brain, 
  Terminal, 
  AlertOctagon, 
  Check,
  Camera,
  ShieldAlert
} from 'lucide-react';
import './styles/app.css';

type DashboardTab = 'OPERATIONS' | 'OPTICAL' | 'DIAGNOSTICS' | 'COGNITIVE' | 'REPLAY';

const DashboardMain: React.FC = () => {
  const [activeTab, setActiveTab] = useState<DashboardTab>('OPERATIONS');
  const [isXAIModalOpen, setIsXAIModalOpen] = useState<boolean>(false);
  const { alerts, acknowledgeAlert, systemMode, isOnline } = useObservatory();


  // Filter critical alerts for top banner
  const criticalAlert = alerts.find((a) => a.severity === 'CRITICAL');

  return (
    <div className="app-container">
      {/* Top Header */}
      <Header />

      {/* Critical Floating Alert Banner */}
      {criticalAlert && (
        <div className="critical-alert-banner">
          <div className="alert-message-content">
            <AlertOctagon size={18} color="var(--status-red)" />
            <span style={{ fontWeight: 800, color: 'var(--status-red)' }}>[CRITICAL SAFETY INTERLOCK]:</span>
            <span style={{ color: 'var(--text-bright)' }}>{criticalAlert.message}</span>
          </div>
          <button
            className="btn-ack"
            onClick={() => acknowledgeAlert(criticalAlert.alert_id)}
          >
            <Check size={12} style={{ marginRight: '4px' }} />
            ACKNOWLEDGE & DISMISS
          </button>
        </div>
      )}

      {/* Navigation Tab Bar */}
      <nav className="nav-tab-bar">
        <button
          className={`nav-tab ${activeTab === 'OPERATIONS' ? 'active' : ''}`}
          onClick={() => setActiveTab('OPERATIONS')}
        >
          <Compass size={14} />
          <span>MISSION OPERATIONS</span>
        </button>

        <button
          className={`nav-tab ${activeTab === 'OPTICAL' ? 'active' : ''}`}
          onClick={() => setActiveTab('OPTICAL')}
        >
          <Camera size={14} />
          <span>OPTICAL & VISION</span>
        </button>

        <button
          className={`nav-tab ${activeTab === 'DIAGNOSTICS' ? 'active' : ''}`}
          onClick={() => setActiveTab('DIAGNOSTICS')}
        >
          <Activity size={14} />
          <span>SENSORS & HEALTH</span>
        </button>

        <button
          className={`nav-tab ${activeTab === 'COGNITIVE' ? 'active' : ''}`}
          onClick={() => setActiveTab('COGNITIVE')}
        >
          <Brain size={14} />
          <span>COGNITIVE AI & PREDICTIONS</span>
        </button>

        <button
          className={`nav-tab ${activeTab === 'REPLAY' ? 'active' : ''}`}
          onClick={() => setActiveTab('REPLAY')}
        >
          <Film size={14} />
          <span>SESSION REPLAY & AUDIT LOG</span>
        </button>
      </nav>

      {/* Persistent Hardware Offline Notice when in HARDWARE mode */}
      {systemMode === 'HARDWARE' && !isOnline && (
        <div style={{
          margin: '0 20px 12px 20px',
          background: 'rgba(255, 77, 77, 0.12)',
          border: '1px solid var(--red-alert)',
          borderRadius: '6px',
          padding: '10px 16px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '12px',
          fontSize: '0.82rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <ShieldAlert size={18} style={{ color: 'var(--red-alert)', flexShrink: 0 }} />
            <div>
              <strong style={{ color: 'var(--red-alert)' }}>LIVE HARDWARE MODE — ESP32 DEVICE OFFLINE:</strong> Real telemetry & camera feed are awaiting physical ESP32 connection. Data fabrication is strictly disabled in hardware mode.
            </div>
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Switch to <strong>DEMO</strong> in the top header to run autonomous simulations.
          </span>
        </div>
      )}

      {/* Main Content Area */}
      <main className="dashboard-content">
        {activeTab === 'OPTICAL' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <CameraVisionDeck />
            <div className="grid-bottom-row">
              <SolarAnalysisPanel />
              <DigitalTwinPanel />
            </div>
          </div>
        )}

        {activeTab === 'OPERATIONS' && (

          <>
            {/* Top Row: Core State, ORS Gauge, Microclimate, AI Decision */}
            <div className="grid-top-row">
              <SystemStatePanel />
              <ReadinessGaugePanel />
              <EnvironmentPanel />
              <AIDecisionPanel onOpenXAIModal={() => setIsXAIModalOpen(true)} />
            </div>

            {/* Middle Row: Digital Twin (kinematics), Vision Feed (ESP32-CAM), Mission Control */}
            <div className="grid-middle-row">
              <DigitalTwinPanel />
              <SolarVisionPanel />
              <MissionControlPanel />
            </div>

            {/* Bottom Row: Historical Telemetry Graph, Actuator Jog/Flight Controls */}
            <div className="grid-bottom-row">
              <TelemetryGraphPanel />
              <CommandControlPanel />
            </div>
          </>
        )}

        {activeTab === 'DIAGNOSTICS' && (
          <>
            <div className="grid-top-row">
              <SystemStatePanel />
              <ObservatoryHealthPanel />
              <SensorHealthPanel />
              <AnomalyAlertsPanel />
            </div>

            <div className="grid-bottom-row">
              <EnvironmentPanel />
              <CommandControlPanel />
            </div>
          </>
        )}

        {activeTab === 'COGNITIVE' && (
          <>
            <div className="grid-top-row">
              <ReadinessGaugePanel />
              <AIDecisionPanel onOpenXAIModal={() => setIsXAIModalOpen(true)} />
              <PredictionPanel />
              <SolarAnalysisPanel />
            </div>

            <div className="grid-bottom-row">
              <SolarVisionPanel />
              <MissionTimelinePanel />
            </div>
          </>
        )}

        {activeTab === 'REPLAY' && (
          <>
            <MissionReplayPanel />
            <div className="grid-bottom-row">
              <TelemetryGraphPanel />
              <EventLogPanel />
            </div>
          </>
        )}
      </main>

      {/* Explainable AI Modal */}
      <ExplainableAIModal
        isOpen={isXAIModalOpen}
        onClose={() => setIsXAIModalOpen(false)}
      />
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <ObservatoryProvider>
      <DashboardMain />
    </ObservatoryProvider>
  );
};

export default App;
