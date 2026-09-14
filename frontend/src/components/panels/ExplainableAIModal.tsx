import React from 'react';
import { useObservatory } from '../../context/ObservatoryContext';
import { Brain, X, CheckCircle2, AlertTriangle, ArrowRight } from 'lucide-react';

export const ExplainableAIModal: React.FC<{ isOpen: boolean; onClose: () => void }> = ({ isOpen, onClose }) => {
  const { xai, aiDecision, aiConfidence } = useObservatory();

  if (!isOpen) return null;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(5, 8, 14, 0.85)',
        backdropFilter: 'blur(6px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000
      }}
    >
      <div
        style={{
          width: '640px',
          maxHeight: '85vh',
          background: 'var(--bg-panel)',
          border: '1px solid var(--border-glow)',
          borderRadius: 'var(--radius-md)',
          boxShadow: 'var(--shadow-panel)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden'
        }}
      >
        {/* Modal Header */}
        <div className="panel-header">
          <div className="panel-title">
            <Brain size={16} />
            <span>Explainable AI (XAI) • Cognitive Trace Diagnostics</span>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center'
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Body */}
        <div style={{ padding: '16px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Top Decision Summary */}
          <div style={{ background: 'var(--bg-deep)', padding: '12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-dim)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-muted)' }}>SELECTED COGNITIVE POLICY:</span>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '20px', fontWeight: 800, color: 'var(--cyan-primary)' }}>
                {aiDecision}
              </div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-muted)' }}>CERTAINTY / CONFIDENCE:</span>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '20px', fontWeight: 800, color: 'var(--text-bright)' }}>
                {(aiConfidence * 100).toFixed(1)}%
              </div>
            </div>
          </div>

          {/* Feature Attribution Weights */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-bright)', fontWeight: 700 }}>
              FEATURE ATTRIBUTION WEIGHTS (SHAP / GRADIENT SALIENCY)
            </span>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {xai.feature_weights.map((fw) => (
                <div
                  key={fw.feature}
                  style={{
                    background: 'var(--bg-deep)',
                    padding: '8px 10px',
                    borderRadius: 'var(--radius-xs)',
                    border: '1px solid var(--border-dim)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '4px'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: 'var(--font-mono)', fontSize: '10px' }}>
                    <span style={{ color: 'var(--text-bright)', fontWeight: 600 }}>{fw.feature}</span>
                    <span style={{ color: fw.weight >= 0 ? 'var(--status-green)' : 'var(--status-red)', fontWeight: 700 }}>
                      {fw.weight > 0 ? `+${fw.weight.toFixed(2)}` : fw.weight.toFixed(2)}
                    </span>
                  </div>

                  <div style={{ height: '4px', background: 'var(--bg-panel-elevated)', borderRadius: '2px', position: 'relative' }}>
                    <div
                      style={{
                        position: 'absolute',
                        left: fw.weight < 0 ? `${50 + fw.weight * 50}%` : '50%',
                        width: `${Math.abs(fw.weight) * 50}%`,
                        height: '100%',
                        background: fw.weight >= 0 ? 'var(--status-green)' : 'var(--status-red)',
                        borderRadius: '2px'
                      }}
                    />
                  </div>

                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-dim)' }}>
                    {fw.description}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Operational Safety Threshold Deltas */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-bright)', fontWeight: 700 }}>
              SAFETY ENVELOPE BOUNDARY DELTAS
            </span>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
              {xai.threshold_deltas.map((td) => (
                <div
                  key={td.metric}
                  style={{
                    background: 'var(--bg-deep)',
                    padding: '8px 10px',
                    borderRadius: 'var(--radius-xs)',
                    border: `1px solid ${td.ok ? 'var(--border-dim)' : 'var(--status-red)'}`,
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '2px',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '10px'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)' }}>
                    <span>{td.metric}</span>
                    {td.ok ? <CheckCircle2 size={11} color="var(--status-green)" /> : <AlertTriangle size={11} color="var(--status-red)" />}
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                    <span style={{ fontSize: '13px', fontWeight: 700, color: td.ok ? 'var(--text-bright)' : 'var(--status-red)' }}>
                      {typeof td.current === 'number' ? td.current.toFixed(1) : td.current} {td.unit}
                    </span>
                    <span style={{ fontSize: '9px', color: 'var(--text-dim)' }}>
                      Limit: {td.threshold} {td.unit}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
