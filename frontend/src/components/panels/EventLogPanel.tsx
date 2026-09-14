import React, { useState } from 'react';
import { useObservatory } from '../../context/ObservatoryContext';
import { Terminal, Search } from 'lucide-react';

type LevelFilter = 'ALL' | 'INFO' | 'WARN' | 'ERROR' | 'SAFETY' | 'AI';

export const EventLogPanel: React.FC = () => {
  const { eventLog } = useObservatory();
  const [filterLevel, setFilterLevel] = useState<LevelFilter>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const filteredLogs = eventLog.filter((item) => {
    if (filterLevel !== 'ALL' && item.level !== filterLevel) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      return (
        item.message.toLowerCase().includes(q) ||
        item.category.toLowerCase().includes(q) ||
        item.level.toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <div className="hud-panel">
      <div className="panel-header">
        <div className="panel-title">
          <Terminal size={14} />
          <span>Observatory Event Stream & Audit Log</span>
        </div>

        {/* Filter Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {/* Search Box */}
          <div style={{ display: 'flex', alignItems: 'center', background: 'var(--bg-deep)', padding: '2px 6px', borderRadius: 'var(--radius-xs)', border: '1px solid var(--border-dim)' }}>
            <Search size={11} color="var(--text-dim)" />
            <input
              type="text"
              placeholder="Search stream..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--text-bright)',
                fontFamily: 'var(--font-mono)',
                fontSize: '10px',
                outline: 'none',
                marginLeft: '4px',
                width: '100px'
              }}
            />
          </div>

          {/* Level Buttons */}
          <div style={{ display: 'flex', gap: '2px' }}>
            {(['ALL', 'INFO', 'WARN', 'ERROR', 'SAFETY', 'AI'] as const).map((lvl) => (
              <button
                key={lvl}
                onClick={() => setFilterLevel(lvl)}
                style={{
                  background: filterLevel === lvl ? 'var(--cyan-dim)' : 'var(--bg-deep)',
                  color: filterLevel === lvl ? '#000' : 'var(--text-muted)',
                  border: '1px solid var(--border-dim)',
                  padding: '2px 5px',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '9px',
                  borderRadius: '2px',
                  cursor: 'pointer',
                  fontWeight: filterLevel === lvl ? 800 : 400
                }}
              >
                {lvl}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="panel-body" style={{ padding: '8px' }}>
        <div className="event-terminal">
          {filteredLogs.map((log) => (
            <div key={log.id} className="terminal-line">
              <span className="ts">[{log.timestamp}]</span>
              <span className={`level-${log.level}`}>[{log.level}]</span>
              <span style={{ color: 'var(--text-dim)' }}>[{log.category}]</span>
              <span style={{ color: 'var(--text-bright)' }}>{log.message}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
