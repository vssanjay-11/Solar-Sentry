import React from 'react';
import { 
  Telescope, 
  Radio, 
  FileText, 
  Camera, 
  Activity, 
  Target, 
  Compass, 
  CheckCircle,
  Eye
} from 'lucide-react';
import { useObservatory } from '../../context/ObservatoryContext';
import { Panel, Stat, ImageStage } from './common/UIPrimitives';

interface ObservatoryPageProps {
  announce: (message: string) => void;
}

export const ObservatoryPage: React.FC<ObservatoryPageProps> = ({ announce }) => {
  const { telemetry, cameraState, eventLog, systemMode } = useObservatory();

  return (
    <>
      {/* Top Observatory Dome & Deep Sky Hero View */}
      <Panel 
        title="Celestial Observatory View" 
        icon={Telescope}
        action={
          <span className="live-label">
            <span className="status-dot" />
            {systemMode === 'DEMO' ? 'VIRTUAL SKY VIEW' : 'PHYSICAL DOME ONLINE'}
          </span>
        }
      >
        <div className="image-stage observatory-stage">
          <img 
            src="/space/observatory.jpg" 
            alt="Solar Sentry Observatory Telescope Under Deep Space Sky" 
          />
          <div className="stage-grid" />
          <span className="stage-label">
            SOLAR SENTRY GROUND OBSERVATION DOME #1 · DUAL-AXIS CELESTIAL ALIGNMENT · AZ {telemetry.pan.toFixed(1)}° / ALT {telemetry.tilt.toFixed(1)}°
          </span>
        </div>
      </Panel>

      {/* Middle 3-Column Instrument & Observation Grid */}
      <section className="page-grid three">
        {/* Observatory Instruments List */}
        <Panel title="Observatory Instruments" icon={Telescope}>
          <div className="instrument-list">
            <button onClick={() => announce('Solar H-Alpha Telescope active')}>
              <img src="/space/observatory.jpg" alt="Solar Telescope" />
              <strong>Solar Telescope</strong>
              <span className="live-label"><span className="status-dot" />Operational</span>
            </button>
            <button onClick={() => announce('Wide Field Synoptic Camera online')}>
              <img src="/space/live-camera.jpg" alt="Wide Field Camera" />
              <strong>Wide Field Cam</strong>
              <span className="live-label"><span className="status-dot" />Online</span>
            </button>
            <button onClick={() => announce('High-resolution Optical Spectrograph active')}>
              <img src="/space/solar-analysis.jpg" alt="Spectrograph" />
              <strong>Spectrograph</strong>
              <span className="live-label"><span className="status-dot" />Calibrated</span>
            </button>
          </div>
        </Panel>

        {/* Live Observation Feed Stage */}
        <Panel 
          title="Live Optical Feed" 
          icon={Radio}
          action={
            <span className="live-label">
              <span className={`status-dot ${cameraState.status !== 'ONLINE' ? 'offline' : ''}`} />
              {cameraState.status}
            </span>
          }
        >
          <div className="image-stage medium-stage">
            <img 
              src={cameraState.status === 'ONLINE' ? cameraState.streamUrl : '/space/live-camera.jpg'} 
              alt="Live Solar Sentry Camera Stream" 
            />
            <div className="stage-grid" />
            <span className="stage-label">
              {cameraState.status === 'ONLINE' ? `FEED: ${cameraState.hostname}` : 'SIMULATED OPTICAL FEED'}
            </span>
          </div>
        </Panel>

        {/* Real Observation Log */}
        <Panel title="Observation Log" icon={FileText}>
          <div className="status-rows">
            {eventLog.slice(0, 4).map((evt) => (
              <div key={evt.id}>
                <span title={evt.message}>
                  <span className="status-dot" />
                  {evt.timestamp} · {evt.category}
                </span>
                <strong style={{ fontSize: '11px', maxWidth: '140px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {evt.message}
                </strong>
              </div>
            ))}
          </div>
        </Panel>
      </section>

      {/* Bottom Metrics Row */}
      <section className="page-grid three">
        <Stat 
          icon={Camera} 
          label="Images Captured Today" 
          value="247" 
          detail="Automated 30-sec interval time-lapse" 
        />
        <Stat 
          icon={Activity} 
          label="Events Detected" 
          value="12" 
          detail="Umbral shifts, coronal loops & C1 flares" 
        />
        <Stat 
          icon={Target} 
          label="Objects Tracked" 
          value="5" 
          detail="Sun center, AR-3786, AR-3788, Prominence NW" 
        />
      </section>
    </>
  );
};
