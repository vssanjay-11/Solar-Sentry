import React, { useState } from 'react';
import { useObservatory } from '../../context/ObservatoryContext';
import { Brain, HelpCircle, ChevronRight, CheckCircle2, AlertTriangle, XCircle } from 'lucide-react';
import { AIDecisionState } from '../../types/intelligence';

export const AIDecisionPanel: React.FC<{ onOpenXAIModal: () => void }> = ({ onOpenXAIModal }) => {
  const { aiDecision, aiConfidence, xai } = useObservatory();

  const getDecisionTheme = (decision: AIDecisionState) => {
    switch (decision) {
      case 'OBSERVE':
        return { color: 'var(--status-green)', border: 'var(--status-green)', bg: 'rgba(0, 255, 157, 0.12)' };
      case 'WAIT':
      case 'SCAN':
        return { color: 'var(--status-yellow)', border: 'var(--status-yellow)', bg: 'rgba(255, 183, 0, 0.12)' };
      case 'SUSPEND':
      case 'SAFE':
        return { color: 'var(--status-red)', border: 'var(--status-red)', bg: 'rgba(255, 42, 95, 0.15)' };
      default:
        return { color: 'var(--cyan-primary)', border: 'var(--cyan-primary)', bg: 'rgba(0, 229, 255, 0.12)' };
    }
  };

  const theme = getDecisionTheme(aiDecision);

  return (
    <div className="hud-panel">
      <div className="panel-header">
        <div className="panel-title">
          <Brain size={14} />
          <span>Cognitive Decision Engine (Agent 8)</span>
        </div>
        <button
          onClick={onOpenXAIModal}
          style={{
            background: 'var(--bg-panel-elevated)',
            border: '1px solid var(--cyan-dim)',
            color: 'var(--cyan-primary)',
            fontFamily: 'var(--font-mono)',
            fontSize: '10px',
            padding: '2px 8px',
            borderRadius: 'var(--radius-xs)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '4px'
          }}
        >
          <span>EXPLAIN</span>
          <ChevronRight size={11} />
        </button>
      </div>

      <div className="panel-body">
        <div className="ai-decision-box">
          <div className="ai-decision-header">
            <div>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-muted)', display: 'block' }}>
                AUTONOMOUS COGNITIVE ACTION:
              </span>
              <span className="ai-state-tag" style={{ color: theme.color }}>
                {aiDecision}
              </span>
            </div>

            <div style={{ textAlign: 'right' }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-muted)', display: 'block' }}>
                CONFIDENCE:
              </span>
              <span className="ai-confidence-pill">
                {(aiConfidence * 100).toFixed(0)}%
              </span>
            </div>
          </div>

          {/* Uncertainty Bar */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: 'var(--font-mono)', fontSize: '9px' }}>
              <span style={{ color: 'var(--text-dim)' }}>Confidence Distribution</span>
              <span style={{ color: 'var(--text-muted)' }}>
                Epistemic Uncertainty: {((1 - aiConfidence) * 100).toFixed(0)}%
              </span>
            </div>
            <div style={{ height: '4px', background: 'var(--bg-panel-elevated)', borderRadius: '2px', overflow: 'hidden' }}>
              <div
                style={{
                  height: '100%',
                  width: `${aiConfidence * 100}%`,
                  background: theme.color,
                  transition: 'width 0.4s ease'
                }}
              />
            </div>
          </div>

          {/* Explainable AI WHY Factors */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-muted)', fontWeight: 700 }}>
              EXPLAINABILITY TRACE (WHY):
            </span>
            <ul className="xai-why-list">
              {xai.why_factors.map((factor, idx) => (
                <li key={idx} className="xai-why-item">
                  <span style={{ color: 'var(--cyan-primary)', fontWeight: 700 }}>•</span>
                  <span>{factor}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};
