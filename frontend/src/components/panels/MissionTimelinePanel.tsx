import React from 'react';
import { useObservatory } from '../../context/ObservatoryContext';
import { Clock, CheckCircle2, PlayCircle, CircleDashed } from 'lucide-react';
import { MissionTimelineItem } from '../../types/mission';

export const MissionTimelinePanel: React.FC = () => {
  const { missionTimeline } = useObservatory();

  const getStatusBadge = (item: MissionTimelineItem) => {
    switch (item.status) {
      case 'COMPLETED':
        return (
          <span style={{ display: 'flex', alignItems: 'center', gap: '3px', color: 'var(--status-green)', fontSize: '9px', fontWeight: 700 }}>
            <CheckCircle2 size={11} /> COMPLETED
          </span>
        );
      case 'ACTIVE':
        return (
          <span style={{ display: 'flex', alignItems: 'center', gap: '3px', color: 'var(--cyan-primary)', fontSize: '9px', fontWeight: 800 }}>
            <PlayCircle size={11} /> ACTIVE NOW
          </span>
        );
      default:
        return (
          <span style={{ display: 'flex', alignItems: 'center', gap: '3px', color: 'var(--text-dim)', fontSize: '9px' }}>
            <CircleDashed size={11} /> UPCOMING
          </span>
        );
    }
  };

  return (
    <div className="hud-panel">
      <div className="panel-header">
        <div className="panel-title">
          <Clock size={14} />
          <span>Mission Execution Timeline</span>
        </div>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-muted)' }}>
          AGENT 9 PLANNER SCHEDULE
        </span>
      </div>

      <div className="panel-body">
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {missionTimeline.map((item, idx) => (
            <div
              key={item.id}
              style={{
                background: item.status === 'ACTIVE' ? 'rgba(0, 229, 255, 0.08)' : 'var(--bg-deep)',
                border: `1px solid ${item.status === 'ACTIVE' ? 'var(--cyan-dim)' : 'var(--border-dim)'}`,
                borderLeft: `3px solid ${item.status === 'ACTIVE' ? 'var(--cyan-primary)' : item.status === 'COMPLETED' ? 'var(--status-green)' : 'var(--border-mid)'}`,
                borderRadius: 'var(--radius-xs)',
                padding: '8px 10px',
                display: 'flex',
                flexDirection: 'column',
                gap: '2px',
                fontFamily: 'var(--font-mono)'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ color: 'var(--text-dim)', fontSize: '9px' }}>0{idx + 1}.</span>
                  <span style={{ color: 'var(--text-bright)', fontSize: '11px', fontWeight: 600 }}>{item.title}</span>
                </div>
                {getStatusBadge(item)}
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '9px', color: 'var(--text-muted)' }}>
                <span>{item.description}</span>
                <span style={{ color: 'var(--text-dim)' }}>
                  {item.start_time} ({item.duration_minutes}m)
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
