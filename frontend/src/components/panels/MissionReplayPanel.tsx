import React from 'react';
import { useObservatory } from '../../context/ObservatoryContext';
import { Play, Pause, RotateCcw, FastForward, Film } from 'lucide-react';

export const MissionReplayPanel: React.FC = () => {
  const {
    isReplayActive,
    setIsReplayActive,
    replayFrames,
    replayIndex,
    setReplayIndex,
    isReplayPlaying,
    setIsReplayPlaying,
    replaySpeed,
    setReplaySpeed
  } = useObservatory();

  const currentFrame = replayFrames[replayIndex];

  return (
    <div className="hud-panel">
      <div className="panel-header">
        <div className="panel-title">
          <Film size={14} />
          <span>Mission Flight Recorder & Session Replay</span>
        </div>
        <button
          onClick={() => setIsReplayActive(!isReplayActive)}
          style={{
            background: isReplayActive ? 'var(--status-red)' : 'var(--bg-panel-elevated)',
            border: '1px solid var(--border-mid)',
            color: '#fff',
            fontFamily: 'var(--font-mono)',
            fontSize: '10px',
            padding: '2px 8px',
            borderRadius: 'var(--radius-xs)',
            cursor: 'pointer'
          }}
        >
          {isReplayActive ? 'DISENGAGE REPLAY' : 'ENGAGE REPLAY'}
        </button>
      </div>

      <div className="panel-body">
        {/* Scrubber & Player Controls */}
        <div className="replay-bar">
          <button
            className="replay-btn"
            onClick={() => setIsReplayPlaying(!isReplayPlaying)}
            disabled={!isReplayActive}
          >
            {isReplayPlaying ? <Pause size={12} /> : <Play size={12} />}
            <span>{isReplayPlaying ? 'PAUSE' : 'PLAY'}</span>
          </button>

          <button
            className="replay-btn"
            onClick={() => setReplayIndex(0)}
            disabled={!isReplayActive}
            title="Rewind to start"
          >
            <RotateCcw size={12} />
          </button>

          {/* Scrub Slider */}
          <input
            type="range"
            min="0"
            max={replayFrames.length - 1}
            value={replayIndex}
            onChange={(e) => setReplayIndex(Number(e.target.value))}
            disabled={!isReplayActive}
            className="replay-scrubber"
          />

          {/* Speed Selectors */}
          <div style={{ display: 'flex', gap: '3px' }}>
            {[1, 2, 5, 10].map((spd) => (
              <button
                key={spd}
                className="replay-btn"
                onClick={() => setReplaySpeed(spd)}
                disabled={!isReplayActive}
                style={{
                  background: replaySpeed === spd ? 'var(--solar-gold)' : 'var(--bg-deep)',
                  color: replaySpeed === spd ? '#000' : 'var(--text-bright)',
                  fontWeight: replaySpeed === spd ? 800 : 400
                }}
              >
                {spd}x
              </button>
            ))}
          </div>
        </div>

        {/* Frame Context Metadata */}
        {currentFrame && (
          <div
            style={{
              background: 'var(--bg-deep)',
              border: '1px solid var(--border-dim)',
              borderRadius: 'var(--radius-xs)',
              padding: '8px 10px',
              display: 'flex',
              flexDirection: 'column',
              gap: '4px',
              fontFamily: 'var(--font-mono)',
              fontSize: '10px'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)' }}>
              <span>FRAME {replayIndex + 1} OF {replayFrames.length}</span>
              <span style={{ color: 'var(--solar-gold)' }}>{new Date(currentFrame.timestamp).toLocaleString()}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>State: <strong>{currentFrame.telemetry.state}</strong></span>
              <span>Decision: <strong>{currentFrame.decision}</strong> ({Math.round(currentFrame.decision_confidence * 100)}%)</span>
              <span>ORS: <strong>{currentFrame.ors_score}</strong></span>
              <span>Pose: <strong>({currentFrame.telemetry.pan}°, {currentFrame.telemetry.tilt}°)</strong></span>
            </div>
            <div style={{ color: 'var(--text-standard)', fontStyle: 'italic', marginTop: '2px' }}>
              "{currentFrame.notes}"
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
