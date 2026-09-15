import React, { useState } from 'react';
import { 
  Orbit, 
  Check, 
  Timer, 
  Database, 
  Radio, 
  Target, 
  ChevronRight, 
  Zap, 
  X, 
  ShieldCheck,
  Compass,
  Play
} from 'lucide-react';
import { useObservatory } from '../../context/ObservatoryContext';
import { Panel, Stat, ImageStage } from './common/UIPrimitives';

interface MissionsPageProps {
  announce: (message: string) => void;
  filtered?: string[];
}

const DEFAULT_MISSIONS = [
  { id: 'SS-012', name: 'Active Region AR-3786 High-Res Optical Mapping', date: '27 Nov 2026, 02:00 PM', status: 'ACTIVE', progress: 78 },
  { id: 'SS-013', name: 'C-Class Flare Kinematic Velocity Tracking', date: '28 Nov 2026, 06:00 AM', status: 'SCHEDULED', progress: 0 },
  { id: 'SS-014', name: 'Coronal Loop Magnetic Topology Survey', date: '30 Nov 2026, 08:30 AM', status: 'PLANNED', progress: 0 },
  { id: 'SS-015', name: 'Synoptic Full-Disk Multi-Spectral Survey', date: '02 Dec 2026, 11:00 AM', status: 'PLANNED', progress: 0 },
];

export const MissionsPage: React.FC<MissionsPageProps> = ({ announce, filtered }) => {
  const { telemetry, missionTarget, sendCommand, triggerEmergencyStop } = useObservatory();

  const [selectedMission, setSelectedMission] = useState(DEFAULT_MISSIONS[0]);
  const [activeTab, setActiveTab] = useState<'Orbital' | 'Ground' | 'Telemetry'>('Orbital');
  const [isExecuting, setIsExecuting] = useState<boolean>(true);

  const displayList = filtered && filtered.length > 0
    ? DEFAULT_MISSIONS.filter(m => m.name.toLowerCase().includes(filtered[0]?.toLowerCase() || ''))
    : DEFAULT_MISSIONS;

  const handleStartMission = async () => {
    await sendCommand('OBSERVE');
    setIsExecuting(true);
    announce(`Mission [${selectedMission.id}] executed. Autonomous tracking engaged.`);
  };

  const handleParkMission = async () => {
    await sendCommand('PARK');
    setIsExecuting(false);
    announce(`Mission [${selectedMission.id}] parked at safe stow coordinates.`);
  };

  return (
    <>
      {/* Metrics Row */}
      <section className="metrics-row">
        <Stat 
          icon={Orbit} 
          label="Total Missions" 
          value="12" 
          detail="8 completed · 3 active · 1 planned" 
        />
        <Stat 
          icon={Check} 
          label="Mission Success Rate" 
          value="91.7%" 
          detail="11 / 12 Objectives verified" 
        />
        <Stat 
          icon={Timer} 
          label="Total Observation Time" 
          value="1,248 hrs" 
          detail="Continuous autonomous tracking" 
        />
        <Stat 
          icon={Database} 
          label="Scientific Data Collected" 
          value="3.6 TB" 
          detail="Frames, raw telemetry & XAI logs" 
        />
      </section>

      {/* Main Missions 3-Column Layout */}
      <section className="page-grid missions-layout">
        {/* Upcoming & Scheduled Missions List */}
        <Panel title="Mission Manifest" icon={Orbit}>
          <div className="mission-list">
            {displayList.map((m) => (
              <button
                key={m.id}
                className="mission-row"
                style={{
                  borderColor: selectedMission.id === m.id ? '#17befe' : undefined,
                  background: selectedMission.id === m.id ? 'rgba(10, 60, 115, 0.65)' : undefined
                }}
                onClick={() => {
                  setSelectedMission(m);
                  announce(`Selected mission ${m.id}: ${m.name}`);
                }}
              >
                <img src="/space/missions.jpg" alt="Mission Thumb" />
                <span>
                  <strong>{m.id} · {m.name}</strong>
                  <small>{m.date}</small>
                </span>
                <b>{m.status}</b>
                <ChevronRight />
              </button>
            ))}
          </div>
        </Panel>

        {/* Live Mission Tracking View */}
        <Panel title="Live Mission Trajectory Tracking" icon={Radio}>
          <div className="image-stage medium-stage">
            <img src="/space/missions.jpg" alt="Satellite Orbital Tracking Path" />
            <div className="stage-grid" />
            <span className="stage-label">
              ORBITAL TRACKING: SS-012 · TARGET: {missionTarget.name || 'AR-3786'} · KINEMATICS: AZ {telemetry.pan.toFixed(1)}° / EL {telemetry.tilt.toFixed(1)}°
            </span>
          </div>

          <div className="tab-row">
            {(['Orbital', 'Ground', 'Telemetry'] as const).map((tab) => (
              <button
                key={tab}
                className={activeTab === tab ? 'active' : ''}
                onClick={() => setActiveTab(tab)}
              >
                {tab} View
              </button>
            ))}
          </div>
        </Panel>

        {/* Mission Details & Controls */}
        <Panel title="Mission Details & Dispatch" icon={Target}>
          <div className="status-rows">
            <div>
              <span>Mission Target</span>
              <strong>{missionTarget.name || selectedMission.name}</strong>
            </div>
            <div>
              <span>Status</span>
              <strong style={{ color: isExecuting ? 'var(--v0-green)' : 'var(--v0-gold)' }}>
                {isExecuting ? 'ACTIVE TRACKING' : 'STANDBY / PARKED'}
              </strong>
            </div>
            <div>
              <span>Dual-Axis Coordinates</span>
              <strong>Pan {telemetry.pan.toFixed(1)}° · Tilt {telemetry.tilt.toFixed(1)}°</strong>
            </div>
            <div>
              <span>Data Collected</span>
              <strong>482 GB (Optical & Sensor)</strong>
            </div>
            <div>
              <span>Target Coordinates</span>
              <strong>RA 14h 22m · Dec +19° 42'</strong>
            </div>
          </div>

          <div className="control-actions" style={{ marginTop: '14px' }}>
            <button className="primary-action" onClick={handleStartMission}>
              <Play size={14} /> Start
            </button>
            <button onClick={handleParkMission}>
              <X size={14} /> Park
            </button>
            <button className="danger-action" onClick={() => triggerEmergencyStop()}>
              <ShieldCheck size={14} /> E-Stop
            </button>
          </div>
        </Panel>
      </section>
    </>
  );
};
