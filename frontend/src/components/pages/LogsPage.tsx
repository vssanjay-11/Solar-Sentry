import React, { useState } from 'react';
import { 
  Database, 
  Timer, 
  Check, 
  BarChart3, 
  SlidersHorizontal, 
  Search, 
  FileText, 
  ArrowRight, 
  ChevronRight, 
  Download,
  Filter
} from 'lucide-react';
import { useObservatory } from '../../context/ObservatoryContext';
import { Panel, Stat } from './common/UIPrimitives';

interface LogsPageProps {
  announce: (message: string) => void;
}

export const LogsPage: React.FC<LogsPageProps> = ({ announce }) => {
  const { eventLog } = useObservatory();

  const [filterType, setFilterType] = useState<'ALL' | 'INFO' | 'WARN' | 'ACTUATOR' | 'EDGE'>('ALL');

  const filteredLogs = filterType === 'ALL'
    ? eventLog
    : eventLog.filter(e => e.level === filterType || e.category === filterType);

  const handleExport = () => {
    const jsonStr = JSON.stringify(eventLog, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `solar-sentry-telemetry-logs-${Date.now()}.json`;
    a.click();
    announce('Telemetry and event logs exported as JSON file');
  };

  return (
    <>
      {/* Top Storage & Records Metrics Row */}
      <section className="metrics-row">
        <Stat 
          icon={Database} 
          label="Total Database Records" 
          value="248,671" 
          detail="+12,459 appended today" 
        />
        <Stat 
          icon={Timer} 
          label="Telemetry Data Range" 
          value="01 Nov – Present" 
          detail="Continuous logging stream" 
        />
        <Stat 
          icon={Database} 
          label="Storage Allocated" 
          value="12.4 GB" 
          detail="of 100 GB dedicated SSD" 
        />
        <Stat 
          icon={Check} 
          label="Last Cloud Backup" 
          value="Successful" 
          detail="Automatic snapshot verified" 
        />
      </section>

      {/* 3-Column Logs Layout */}
      <section className="page-grid logs-layout">
        {/* Data Trends Chart */}
        <Panel title="Data Ingestion Trends" icon={BarChart3}>
          <div className="fake-chart">
            <div className="chart-line one" title="Sensory Telemetry (I2C)" />
            <div className="chart-line two" title="Vision Frames (MJPEG)" />
            <div className="chart-line three" title="AI Decisions (Agent 8)" />
            <div className="chart-axis">
              <span>00:00</span>
              <span>06:00</span>
              <span>12:00</span>
              <span>18:00</span>
              <span>24:00</span>
            </div>
          </div>
        </Panel>

        {/* Data Distribution Ring */}
        <Panel title="Data Type Distribution" icon={Database}>
          <div className="score-ring purple">
            248K
            <small>Total Records</small>
          </div>
          <div className="status-rows">
            <div>
              <span>Optical Frames & Snapshots</span>
              <strong>45% (112K)</strong>
            </div>
            <div>
              <span>Sensor Fusion Telemetry</span>
              <strong>25% (62K)</strong>
            </div>
            <div>
              <span>System & Hardware Events</span>
              <strong>15% (37K)</strong>
            </div>
            <div>
              <span>AI Inferences & XAI Traces</span>
              <strong>15% (37K)</strong>
            </div>
          </div>
        </Panel>

        {/* Quick Filter Control */}
        <Panel title="Telemetry Filters" icon={SlidersHorizontal}>
          <div className="status-rows">
            <div>
              <span>Log Category</span>
              <strong style={{ color: 'var(--v0-cyan)' }}>{filterType}</strong>
            </div>
            <div>
              <span>Source Node</span>
              <strong>ESP32 DevKit & Cam</strong>
            </div>
            <div>
              <span>Log Level</span>
              <strong>INFO, WARN, CRITICAL</strong>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '6px', marginTop: '12px', flexWrap: 'wrap' }}>
            {(['ALL', 'INFO', 'WARN', 'ACTUATOR', 'EDGE'] as const).map((lvl) => (
              <button
                key={lvl}
                onClick={() => {
                  setFilterType(lvl);
                  announce(`Filtered by ${lvl}`);
                }}
                style={{
                  padding: '4px 8px',
                  borderRadius: '5px',
                  fontSize: '10.5px',
                  background: filterType === lvl ? '#0868dc' : 'rgba(4, 28, 56, 0.65)',
                  border: '1px solid rgba(23, 190, 254, 0.35)',
                  color: filterType === lvl ? '#fff' : '#adc8e8',
                  cursor: 'pointer'
                }}
              >
                {lvl}
              </button>
            ))}
          </div>

          <button className="primary-action wide" onClick={handleExport}>
            <Download size={14} /> Export Telemetry Log
          </button>
        </Panel>
      </section>

      {/* Persisted Data Logs Table */}
      <Panel 
        title="Persisted Telemetry & System Event Records" 
        icon={FileText}
        action={
          <button className="text-action" onClick={handleExport}>
            Export JSON <Download size={13} />
          </button>
        }
      >
        <div className="data-table">
          {filteredLogs.map((evt) => (
            <div key={evt.id}>
              <span>
                <strong>[{evt.timestamp}]</strong> [{evt.category}] {evt.message}
              </span>
              <b style={{ color: evt.level === 'WARN' ? 'var(--v0-gold)' : ((evt.level === 'ERROR' || evt.level === 'SAFETY') ? 'var(--v0-red)' : 'var(--v0-green)') }}>
                {evt.level}
              </b>
              <ChevronRight />
            </div>
          ))}
        </div>
      </Panel>
    </>
  );
};
