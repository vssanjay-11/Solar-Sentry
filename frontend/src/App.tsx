import React, { useState, useEffect, useMemo } from 'react';
import { ObservatoryProvider, useObservatory } from './context/ObservatoryContext';
import { 
  Home, 
  Camera, 
  Sun, 
  Telescope, 
  Orbit, 
  Layers3, 
  BrainCircuit, 
  Activity, 
  Database, 
  Settings,
  Search, 
  Wifi, 
  Bell, 
  Menu, 
  X, 
  AlertOctagon, 
  Check, 
  ShieldAlert, 
  Sparkles 
} from 'lucide-react';
import { HomePage } from './components/pages/HomePage';
import { CameraPage } from './components/pages/CameraPage';
import { AnalysisPage } from './components/pages/AnalysisPage';
import { ObservatoryPage } from './components/pages/ObservatoryPage';
import { MissionsPage } from './components/pages/MissionsPage';
import { DigitalTwinPage } from './components/pages/DigitalTwinPage';
import { AIPage } from './components/pages/AIPage';
import { HealthPage } from './components/pages/HealthPage';
import { LogsPage } from './components/pages/LogsPage';
import { SettingsPage } from './components/pages/SettingsPage';
import { ExplainableAIModal } from './components/panels/ExplainableAIModal';
import { ImageStage } from './components/pages/common/UIPrimitives';
import './styles/app.css';

type PageTab = 
  | 'Home' 
  | 'Live Camera' 
  | 'Solar Analysis' 
  | 'Observatory' 
  | 'Missions' 
  | 'Digital Twin' 
  | 'AI Insights' 
  | 'System Health' 
  | 'Data Logs' 
  | 'Settings';

interface NavItem {
  label: PageTab;
  icon: React.ComponentType<{ className?: string; size?: number }>;
  imageClass: string;
  tagline: string;
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Home', icon: Home, imageClass: 'environment-home', tagline: 'Real-time Autonomous Solar Observatory Platform' },
  { label: 'Live Camera', icon: Camera, imageClass: 'environment-camera', tagline: 'High-Resolution Dynamic ESP32-CAM Optical Vision Stream' },
  { label: 'Solar Analysis', icon: Sun, imageClass: 'environment-analysis', tagline: 'Computer Vision Segmentation & Solar Feature Analysis' },
  { label: 'Observatory', icon: Telescope, imageClass: 'environment-observatory', tagline: 'Ground Observatory Instruments & Celestial Tracking' },
  { label: 'Missions', icon: Orbit, imageClass: 'environment-missions', tagline: 'Orbital Trajectories & Autonomous Solar Tracking' },
  { label: 'Digital Twin', icon: Layers3, imageClass: 'environment-twin', tagline: 'Dual-Axis Kinematics & 3D Heliophysics Simulation' },
  { label: 'AI Insights', icon: BrainCircuit, imageClass: 'environment-ai', tagline: 'Agent 8 Cognitive Inferences & Explainable AI Traces' },
  { label: 'System Health', icon: Activity, imageClass: 'environment-health', tagline: 'Real-Time Edge Subsystem Diagnostics & Watchdog' },
  { label: 'Data Logs', icon: Database, imageClass: 'environment-logs', tagline: 'Persisted Telemetry History & System Audit Records' },
  { label: 'Settings', icon: Settings, imageClass: 'environment-settings', tagline: 'Hardware Configuration, mDNS Discovery & System Settings' }
];

const DashboardMain: React.FC = () => {
  const [activeTab, setActiveTab] = useState<PageTab>('Home');
  const [search, setSearch] = useState<string>('');
  const [notice, setNotice] = useState<string>('All systems nominal');
  const [cameraOpen, setCameraOpen] = useState<boolean>(false);
  const [isXAIModalOpen, setIsXAIModalOpen] = useState<boolean>(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState<boolean>(false);
  const [pointer, setPointer] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [currentTime, setCurrentTime] = useState<string>(new Date().toLocaleTimeString());
  const [currentDate, setCurrentDate] = useState<string>(
    new Date().toLocaleDateString('en-US', { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' })
  );

  const { 
    systemMode, 
    setSystemMode, 
    isOnline, 
    alerts, 
    acknowledgeAlert, 
    cameraState 
  } = useObservatory();

  // Pointer position for parallax
  useEffect(() => {
    const handlePointer = (event: PointerEvent) => {
      setPointer({
        x: (event.clientX / window.innerWidth - 0.5) * 2,
        y: (event.clientY / window.innerHeight - 0.5) * 2
      });
    };
    window.addEventListener('pointermove', handlePointer, { passive: true });
    return () => window.removeEventListener('pointermove', handlePointer);
  }, []);

  // Live Clock
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date().toLocaleTimeString());
      setCurrentDate(
        new Date().toLocaleDateString('en-US', { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' })
      );
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const announce = (message: string) => {
    setNotice(message);
    window.setTimeout(() => setNotice('All systems nominal'), 3200);
  };

  const currentNav = NAV_ITEMS.find((item) => item.label === activeTab) || NAV_ITEMS[0];
  const criticalAlert = alerts.find((a) => a.severity === 'CRITICAL');
  const isHardwareOffline = systemMode === 'HARDWARE' && !isOnline;

  return (
    <main 
      className={`sentry-shell ${currentNav.imageClass}`}
      style={{
        '--pointer-x': `${pointer.x}`,
        '--pointer-y': `${pointer.y}`
      } as React.CSSProperties}
    >
      {/* 
        Astronomical Space Backdrop 
        - High-resolution photorealistic space images
        - Animated nebula & stars drift
        - ZERO astronaut visuals or classes
      */}
      <div className="space-backdrop" aria-hidden="true">
        <div className="space-nebula" />
        <div className="space-stars" />
        <div className="space-orbit" />
        <div className="space-dust" />
      </div>

      {/* Left Navigation Sidebar */}
      <aside className="sidebar">
        <div className="brand-block">
          <div className="brand-mark">
            Solar <span>Sentry</span>
          </div>
          <p>Observe <b>·</b> Protect <b>·</b> Explore</p>
        </div>

        <button 
          className="mobile-menu" 
          aria-label="Toggle navigation menu"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
        >
          {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
        </button>

        <nav className={`primary-nav ${mobileMenuOpen ? 'mobile-open' : ''}`} aria-label="Primary navigation">
          {NAV_ITEMS.map(({ label, icon: IconComponent }) => (
            <button
              key={label}
              className={`nav-item ${activeTab === label ? 'active' : ''}`}
              onClick={() => {
                setActiveTab(label);
                setMobileMenuOpen(false);
                announce(`${label} page selected`);
              }}
            >
              <IconComponent size={17} />
              <span>{label}</span>
            </button>
          ))}
        </nav>

        <blockquote>
          “Beyond our atmosphere lies a universe of possibilities.”
        </blockquote>
      </aside>

      {/* Main Dashboard Content Area */}
      <div className="dashboard-content">
        {/* Top Header Bar */}
        <header className="topbar">
          <label className="search-box">
            <Search />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={`Search ${activeTab.toLowerCase()}, missions, telemetry...`}
            />
          </label>

          <div className="date-readout">
            <span>{currentDate}</span>
            <span>{currentTime}</span>
          </div>

          {/* Mode Switch (DEMO vs HARDWARE) */}
          <div className="mode-switch">
            {(['DEMO', 'HARDWARE'] as const).map((mode) => (
              <button
                key={mode}
                className={`${systemMode === mode ? 'selected' : ''} ${systemMode === 'DEMO' && mode === 'DEMO' ? 'demo-selected' : ''}`}
                onClick={async () => {
                  await setSystemMode(mode);
                  announce(`${mode} mode activated`);
                }}
              >
                {mode === 'HARDWARE' && <span className="toggle-dot" />}
                {mode}
              </button>
            ))}
          </div>

          <span title="Observatory Network Mesh Online" style={{ display: 'flex', alignItems: 'center' }}>
            <Wifi className="wifi-icon" />
          </span>

          {/* System Status Button */}
          <button 
            className="system-status"
            onClick={() => {
              announce('Running immediate system diagnostic...');
              setActiveTab('System Health');
            }}
          >
            <span className={`status-dot ${isHardwareOffline ? 'offline' : ''}`} />
            <span>
              <strong>
                {systemMode === 'DEMO' 
                  ? 'Demo Simulation' 
                  : (isHardwareOffline ? 'Hardware Offline' : 'Hardware Online')}
              </strong>
              <small>{notice}</small>
            </span>
            <Bell />
          </button>
        </header>

        {/* Critical Safety Interlock Banner */}
        {criticalAlert && (
          <div className="critical-alert-banner" style={{
            margin: '12px 0 0',
            padding: '10px 14px',
            background: 'rgba(255, 77, 77, 0.16)',
            border: '1px solid var(--v0-red)',
            borderRadius: '8px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--v0-red)', fontSize: '12px' }}>
              <AlertOctagon size={18} />
              <strong>[CRITICAL SAFETY INTERLOCK]:</strong>
              <span style={{ color: '#fff' }}>{criticalAlert.message}</span>
            </div>
            <button
              onClick={() => acknowledgeAlert(criticalAlert.alert_id)}
              style={{
                background: 'var(--v0-red)',
                border: 0,
                color: '#fff',
                borderRadius: '4px',
                padding: '4px 10px',
                fontSize: '11px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px'
              }}
            >
              <Check size={12} /> Acknowledge
            </button>
          </div>
        )}

        {/* Persistent Hardware Offline Notice in HARDWARE mode */}
        {isHardwareOffline && (
          <div style={{
            marginTop: '12px',
            background: 'rgba(255, 77, 77, 0.12)',
            border: '1px solid var(--v0-red)',
            borderRadius: '8px',
            padding: '10px 16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '12px',
            fontSize: '12px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <ShieldAlert size={18} style={{ color: 'var(--v0-red)', flexShrink: 0 }} />
              <div>
                <strong style={{ color: 'var(--v0-red)' }}>LIVE HARDWARE MODE — ESP32 DEVICE OFFLINE:</strong> Awaiting physical ESP32 controller connection on local network/serial port. Data fabrication is strictly prohibited.
              </div>
            </div>
            <button
              onClick={() => setSystemMode('DEMO')}
              style={{
                background: 'rgba(255, 185, 28, 0.25)',
                border: '1px solid var(--v0-gold)',
                color: '#ffda6a',
                padding: '4px 10px',
                borderRadius: '4px',
                fontSize: '11px',
                cursor: 'pointer',
                whiteSpace: 'nowrap'
              }}
            >
              Switch to DEMO MODE
            </button>
          </div>
        )}

        {/* Page Heading Section */}
        <section className="page-heading">
          <div>
            <p className="kicker">Solar Sentry Observatory</p>
            <h1>{activeTab}</h1>
            <p>{currentNav.tagline}</p>
          </div>
          <div className="hero-quote">
            <em>Observe the Sun today</em><br />
            <strong>for a safer tomorrow.</strong>
          </div>
        </section>

        {/* 10 Individual Page Views */}
        {activeTab === 'Home' && (
          <HomePage 
            announce={announce} 
            onNavigateToTab={(tab) => setActiveTab(tab as PageTab)} 
          />
        )}
        {activeTab === 'Live Camera' && (
          <CameraPage 
            announce={announce} 
            setCameraOpen={setCameraOpen} 
          />
        )}
        {activeTab === 'Solar Analysis' && (
          <AnalysisPage 
            announce={announce} 
            onOpenReport={() => setIsXAIModalOpen(true)} 
          />
        )}
        {activeTab === 'Observatory' && (
          <ObservatoryPage 
            announce={announce} 
          />
        )}
        {activeTab === 'Missions' && (
          <MissionsPage 
            announce={announce} 
            filtered={search ? [search] : undefined} 
          />
        )}
        {activeTab === 'Digital Twin' && (
          <DigitalTwinPage 
            announce={announce} 
          />
        )}
        {activeTab === 'AI Insights' && (
          <AIPage 
            announce={announce} 
            onOpenXAIModal={() => setIsXAIModalOpen(true)} 
          />
        )}
        {activeTab === 'System Health' && (
          <HealthPage 
            announce={announce} 
          />
        )}
        {activeTab === 'Data Logs' && (
          <LogsPage 
            announce={announce} 
          />
        )}
        {activeTab === 'Settings' && (
          <SettingsPage 
            announce={announce} 
          />
        )}

        {/* Global Footer */}
        <footer className="dashboard-footer">
          <span />
          Solar Sentry · Observe. Protect. Explore.
          <span />
        </footer>
      </div>

      {/* Full-Screen Camera Modal */}
      {cameraOpen && (
        <div className="modal-backdrop" onClick={() => setCameraOpen(false)}>
          <div className="camera-modal" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
            <div className="panel-heading">
              <h2>Live Camera Feed (Full Resolution)</h2>
              <button onClick={() => setCameraOpen(false)} aria-label="Close modal">
                <X size={20} />
              </button>
            </div>
            <img 
              src={cameraState.status === 'ONLINE' ? cameraState.streamUrl : '/space/live-camera.jpg'} 
              alt="Live Solar Camera Full Feed" 
            />
            <p>
              <span>Solar Sentry CAM-01 ({cameraState.hostname})</span>
              <span className="live-label">
                <span className={`status-dot ${cameraState.status !== 'ONLINE' ? 'offline' : ''}`} />
                {cameraState.status}
              </span>
            </p>
          </div>
        </div>
      )}

      {/* Explainable AI Modal */}
      <ExplainableAIModal
        isOpen={isXAIModalOpen}
        onClose={() => setIsXAIModalOpen(false)}
      />
    </main>
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
