import React from 'react';
import { 
  Sun, 
  Target, 
  Gauge, 
  BarChart3, 
  FileText, 
  BrainCircuit, 
  ChevronRight, 
  ArrowRight,
  Zap,
  Activity,
  Sparkles
} from 'lucide-react';
import { useObservatory } from '../../context/ObservatoryContext';
import { Panel, ImageStage } from './common/UIPrimitives';

interface AnalysisPageProps {
  announce: (message: string) => void;
  onOpenReport?: () => void;
}

export const AnalysisPage: React.FC<AnalysisPageProps> = ({ announce, onOpenReport }) => {
  const { vision, observatoryHealth, systemMode } = useObservatory();

  const qualityScore = Math.round(vision.sharpness_score ? vision.sharpness_score : 92);

  return (
    <>
      <section className="page-grid analysis-layout">
        {/* Analyzed Solar Disk View */}
        <Panel 
          title="Analyzed Solar Observation (Computer Vision)" 
          icon={Sun}
          action={
            <span className="live-label">
              <span className="status-dot" />
              {systemMode === 'DEMO' ? 'SIMULATED CV PIPELINE' : 'LIVE AI PIPELINE'}
            </span>
          }
        >
          <div className="image-stage large-stage">
            <img src="/space/solar-analysis.jpg" alt="Analyzed Solar Disk with Active Regions" />
            <div className="stage-grid" />
            <span className="stage-label">
              AI MODEL: SOLARNET-CV v2.4 · SOLAR DISK SEGMENTATION & FEATURE EXTRACTION
            </span>
          </div>
        </Panel>

        {/* Right Stack: Image Quality & Detected Features */}
        <div className="stack">
          <Panel title="Optical Quality Scorecard" icon={Gauge}>
            <div className="score-ring green">
              {qualityScore}
              <small>/ 100 Quality</small>
            </div>
            <div className="bar-list">
              <div>
                <span>Sharpness</span>
                <i><b style={{ width: `${Math.round(vision.sharpness_score || 88)}%` }} /></i>
                <strong>{Math.round(vision.sharpness_score || 88)}%</strong>
              </div>
              <div>
                <span>Contrast</span>
                <i><b style={{ width: `${Math.round(vision.contrast_score || 82)}%` }} /></i>
                <strong>{Math.round(vision.contrast_score || 82)}%</strong>
              </div>
              <div>
                <span>Signal/Noise</span>
                <i><b style={{ width: '91%' }} /></i>
                <strong>91%</strong>
              </div>
              <div>
                <span>Dynamic Range</span>
                <i><b style={{ width: '86%' }} /></i>
                <strong>86%</strong>
              </div>
            </div>
          </Panel>

          <Panel title="Detected Solar Features" icon={Target}>
            <div className="feature-grid">
              <button onClick={() => announce('Active Region AR-3786 analyzed: high magnetic complexity')}>
                <img src="/space/solar-analysis.jpg" alt="Active Regions" />
                <span>Active Regions<small>2 detected (AR-3786)</small></span>
                <ChevronRight />
              </button>
              <button onClick={() => announce('Sunspots analyzed: 5 major umbral regions')}>
                <img src="/space/live-camera.jpg" alt="Sunspots" />
                <span>Sunspots<small>5 clusters tracked</small></span>
                <ChevronRight />
              </button>
              <button onClick={() => announce('Solar Flare detected: Class C1.2 low-intensity')}>
                <img src="/space/home.jpg" alt="Solar Flares" />
                <span>Solar Flares<small>1 detected (C1.2)</small></span>
                <ChevronRight />
              </button>
              <button onClick={() => announce('Coronal prominences detected at northwest solar limb')}>
                <img src="/space/observatory.jpg" alt="Prominences" />
                <span>Prominences<small>Active at NW limb</small></span>
                <ChevronRight />
              </button>
            </div>
          </Panel>
        </div>
      </section>

      {/* 3-Column Lower Analytics Row */}
      <section className="page-grid three">
        <Panel title="Solar Activity Index (24H)" icon={BarChart3}>
          <div className="fake-chart">
            <div className="chart-line one" title="Radio Flux 10.7cm" />
            <div className="chart-line two" title="X-Ray Flux (GOES)" />
            <div className="chart-line three" title="Optical Prominence Intensity" />
            <div className="chart-axis">
              <span>00:00 UTC</span>
              <span>06:00</span>
              <span>12:00</span>
              <span>18:00</span>
              <span>24:00</span>
            </div>
          </div>
        </Panel>

        <Panel title="Latest Analysis Summary" icon={FileText}>
          <div className="status-rows">
            <div>
              <span>Overall Solar Activity</span>
              <strong style={{ color: 'var(--v0-gold)' }}>Moderate (Level 3/5)</strong>
            </div>
            <div>
              <span>Sunspot Number (SSN)</span>
              <strong>68 (5 Discovered Groups)</strong>
            </div>
            <div>
              <span>Active Regions</span>
              <strong>AR-3786 & AR-3788</strong>
            </div>
            <div>
              <span>Flare Probability (24h)</span>
              <strong>C-Class 75% · M-Class 20%</strong>
            </div>
            <div>
              <span>Optical Seeing Quality</span>
              <strong style={{ color: 'var(--v0-green)' }}>Excellent (0.85 arcsec)</strong>
            </div>
          </div>
        </Panel>

        <Panel title="Cognitive AI Insights" icon={BrainCircuit}>
          <div className="insight-list">
            <div>
              <span className="status-dot" />
              Magnetic gradient in AR-3786 indicates potential flare trigger
              <strong>Active</strong>
            </div>
            <div>
              <span className="status-dot" />
              Optical sharpness optimal for coronal feature segmentation
              <strong>Verified</strong>
            </div>
            <div>
              <span className="status-dot" />
              Solar wind speed projected to reach 440 km/s in next 36h
              <strong>Projected</strong>
            </div>
          </div>
          <button 
            className="primary-action wide"
            onClick={() => onOpenReport ? onOpenReport() : announce('Full optical analysis report generated and opened')}
          >
            View Detailed Scientific Report <ArrowRight />
          </button>
        </Panel>
      </section>
    </>
  );
};
