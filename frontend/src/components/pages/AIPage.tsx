import React, { useState } from 'react';
import { 
  BrainCircuit, 
  Sparkles, 
  BarChart3, 
  Gauge, 
  ArrowRight, 
  Send, 
  CheckCircle,
  Cpu,
  Bot
} from 'lucide-react';
import { useObservatory } from '../../context/ObservatoryContext';
import { Panel, ImageStage } from './common/UIPrimitives';

interface AIPageProps {
  announce: (message: string) => void;
  onOpenXAIModal?: () => void;
}

export const AIPage: React.FC<AIPageProps> = ({ announce, onOpenXAIModal }) => {
  const { aiDecision, aiConfidence, xai, predictions } = useObservatory();

  const [query, setQuery] = useState<string>('');
  const [assistantReply, setAssistantReply] = useState<string | null>(null);

  const handleAsk = (questionText: string) => {
    setQuery(questionText);
    announce(`AI Agent reasoning on: "${questionText}"`);

    if (questionText.toLowerCase().includes('flare')) {
      setAssistantReply('SolarNet model evaluation: AR-3786 displays beta-gamma magnetic complexity. Flare probability is 75% for C-class and 20% for M-class in the next 24 hours. Earth-directed CME risk remains low.');
    } else if (questionText.toLowerCase().includes('sunspot')) {
      setAssistantReply('Analysis of current optical frame reveals 5 distinct sunspot groups with umbral area exceeding 420 millionths of the solar hemisphere. Penumbral boundaries are stable.');
    } else if (questionText.toLowerCase().includes('impact')) {
      setAssistantReply('Geomagnetic disturbance index Kp projected at 2-3 (Quiet to Unsettled). Ionospheric HF radio propagation conditions are nominal over equatorial and mid-latitude bands.');
    } else {
      setAssistantReply(`Agent 8 Cognitive Engine: Overall solar activity is Moderate. ORS Readiness Score is optimal. The autonomous tracking mount is actively centered on prime target Active Region 3786.`);
    }
  };

  return (
    <>
      <section className="page-grid ai-layout">
        {/* Hero AI Neural Cosmic Nexus Panel */}
        <Panel title="Intelligence Beyond Observation" icon={BrainCircuit}>
          <div className="image-stage large-stage">
            <img 
              src="/space/ai-insights.jpg" 
              alt="AI Autonomous Neural Cosmic Nexus over Solar System" 
            />
            <div className="stage-grid" />
            <span className="stage-label">
              AGENT 8 COGNITIVE DECISION ENGINE · REASONING TRACE: {aiDecision} · CONFIDENCE: {(aiConfidence * 100).toFixed(1)}%
            </span>
          </div>
        </Panel>

        {/* Interactive Solar AI Assistant */}
        <Panel title="Solar Sentry AI Assistant" icon={Sparkles}>
          <div className="assistant-box" style={{ gap: '10px' }}>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && query.trim() && handleAsk(query)}
              placeholder="Ask anything about solar activity or observatory status..."
              style={{
                background: 'transparent',
                border: 'none',
                color: '#ffffff',
                width: '100%',
                outline: 'none',
                fontSize: '12px'
              }}
            />
            <button 
              onClick={() => query.trim() && handleAsk(query)}
              style={{ background: 'transparent', border: 0, color: '#17befe', cursor: 'pointer', display: 'flex', alignItems: 'center' }}
            >
              <Send size={15} />
            </button>
          </div>

          {assistantReply && (
            <div style={{
              margin: '12px 0',
              padding: '12px',
              background: 'rgba(5, 35, 70, 0.75)',
              border: '1px solid rgba(23, 190, 254, 0.45)',
              borderRadius: '8px',
              fontSize: '12px',
              lineHeight: 1.45,
              color: '#e6f3ff'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px', color: '#17befe', fontWeight: 600 }}>
                <Bot size={15} /> Agent 8 Response:
              </div>
              {assistantReply}
            </div>
          )}

          <div className="quick-list">
            {[
              'Summarize today’s solar activity',
              'Any signs of upcoming solar flares?',
              'Analyze the latest sunspot image',
              'What is the space weather impact on Earth?'
            ].map((item) => (
              <button key={item} onClick={() => handleAsk(item)}>
                {item}
                <ArrowRight />
              </button>
            ))}
          </div>

          <button 
            className="primary-action wide"
            onClick={() => onOpenXAIModal ? onOpenXAIModal() : announce('Explainable AI (XAI) modal opened')}
          >
            Open Explainable AI (XAI) Modal
          </button>
        </Panel>
      </section>

      {/* 3-Column AI Model Diagnostics Row */}
      <section className="page-grid three">
        {/* Real Reasoning Trace Insights */}
        <Panel title="Cognitive Reasoning Traces" icon={BrainCircuit}>
          <div className="insight-list">
            {xai.why_factors && xai.why_factors.length > 0 ? (
              xai.why_factors.slice(0, 4).map((f, i) => (
                <div key={i}>
                  <span className="status-dot" />
                  {f}
                  <strong>Active</strong>
                </div>
              ))
            ) : (
              <>
                <div>
                  <span className="status-dot" />
                  High optical clarity (contrast 0.88) verifies good seeing
                  <strong>Optimal</strong>
                </div>
                <div>
                  <span className="status-dot" />
                  Rain sensor ADC normal: no weather hazard detected
                  <strong>Safe</strong>
                </div>
                <div>
                  <span className="status-dot" />
                  Sunspot AR-3786 selected as highest priority science target
                  <strong>Target</strong>
                </div>
              </>
            )}
          </div>
        </Panel>

        {/* Activity Forecast Horizions */}
        <Panel title="Activity Forecast (Predictions)" icon={BarChart3}>
          <div className="fake-chart">
            <div className="chart-line one" />
            <div className="chart-line two" />
            <div className="chart-line three" />
            <div className="chart-axis">
              <span>+15 min</span>
              <span>+30 min</span>
              <span>+45 min</span>
              <span>+60 min</span>
            </div>
          </div>
        </Panel>

        {/* Model Performance */}
        <Panel title="Neural Model Performance" icon={Gauge}>
          <div className="score-ring">
            94
            <small>% accuracy</small>
          </div>
          <div className="status-rows">
            <div>
              <span>SolarNet-CV v2.4</span>
              <strong style={{ color: 'var(--v0-green)' }}>Operational · 18ms</strong>
            </div>
            <div>
              <span>FlarePredict Ensemble</span>
              <strong style={{ color: 'var(--v0-green)' }}>Operational · 34ms</strong>
            </div>
            <div>
              <span>CME-Detect Vision</span>
              <strong style={{ color: 'var(--v0-green)' }}>Operational · 22ms</strong>
            </div>
          </div>
        </Panel>
      </section>
    </>
  );
};
