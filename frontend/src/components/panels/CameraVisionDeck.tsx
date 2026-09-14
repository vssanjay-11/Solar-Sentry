import React, { useState, useEffect, useCallback } from 'react';
import { useObservatory } from '../../context/ObservatoryContext';
import { observatoryApi } from '../../services/api';
import {
  Camera,
  Sliders,
  Sparkles,
  RotateCw,
  RefreshCw,
  ExternalLink,
  ShieldAlert,
  Sun,
  Activity,
  CheckCircle2,
  AlertTriangle
} from 'lucide-react';

export const CameraVisionDeck: React.FC = () => {
  const { systemMode, isOnline } = useObservatory();

  // Active view: 'processed' vs 'raw' vs 'split'
  const [viewMode, setViewMode] = useState<'processed' | 'raw' | 'split'>('processed');
  const [loading, setLoading] = useState<boolean>(false);
  const [capturing, setCapturing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Frames
  const [rawFrame, setRawFrame] = useState<string | null>(null);
  const [procFrame, setProcFrame] = useState<string | null>(null);
  const [scorecard, setScorecard] = useState<Record<string, number>>({
    overall_quality_score: 88.5,
    composite_score: 88.5,
    sharpness: 91.2,
    contrast: 85.0,
    exposure_quality: 94.0,
    dynamic_range: 82.0,
    noise_level: 12.4,
    clipped_black_pct: 1.2,
    clipped_white_pct: 0.8
  });
  const [visionAnalysis, setVisionAnalysis] = useState<any>({
    disk_detected: true,
    sunspot_count: 3,
    confidence: 0.94,
    obstruction_score: 0.04
  });

  // Calibration parameters state
  const [params, setParams] = useState({
    brightness: 5,
    contrast: 1.2,
    gamma: 1.05,
    sharpness: 25.0,
    saturation: 105.0,
    noise_reduction: 2,
    apply_clahe: true,
    clahe_clip_limit: 2.0,
    normalize_hist: false,
    invert_colors: false,
    rotation_deg: 0
  });

  // Diagnostic URL
  const [cameraUrl, setCameraUrl] = useState<string>('http://192.168.1.120');

  // Load initial frame on mount
  const captureFrame = useCallback(async (condition?: string) => {
    setCapturing(true);
    setError(null);
    try {
      const data = await observatoryApi.captureCameraFrame(condition);
      setRawFrame(data.raw_image_data);
      setProcFrame(data.processed_image_data);
      if (data.scorecard) setScorecard(data.scorecard);
      if (data.vision_analysis) setVisionAnalysis(data.vision_analysis);
    } catch (err: any) {
      console.warn('Live capture error:', err);
      setError(err.message || 'Frame capture failed');
    } finally {
      setCapturing(false);
    }
  }, []);

  // Recalibrate current frame with updated params
  const applyCalibration = useCallback(async (newParams = params) => {
    setLoading(true);
    setError(null);
    try {
      const data = await observatoryApi.calibrateCamera(newParams);
      if (data.raw_image_data) setRawFrame(data.raw_image_data);
      if (data.processed_image_data) setProcFrame(data.processed_image_data);
      if (data.scorecard) setScorecard(data.scorecard);
      if (data.vision_analysis) setVisionAnalysis(data.vision_analysis);
    } catch (err: any) {
      console.warn('Calibration error:', err);
      setError(err.message || 'Calibration application failed');
    } finally {
      setLoading(false);
    }
  }, [params]);

  // Fetch camera diagnostics URL
  useEffect(() => {
    observatoryApi.getCameraStatus().then((info) => {
      if (info && info.camera_url) {
        setCameraUrl(info.camera_url);
      }
    }).catch(() => {});
    captureFrame();
  }, [captureFrame]);

  // Handle Preset Buttons
  const setPresetAuto = () => {
    const auto = {
      brightness: 5,
      contrast: 1.25,
      gamma: 1.05,
      sharpness: 30.0,
      saturation: 110.0,
      noise_reduction: 2,
      apply_clahe: true,
      clahe_clip_limit: 2.2,
      normalize_hist: false,
      invert_colors: false,
      rotation_deg: 0
    };
    setParams(auto);
    applyCalibration(auto);
  };

  const setPresetHighContrast = () => {
    const hc = {
      brightness: -10,
      contrast: 1.8,
      gamma: 0.9,
      sharpness: 50.0,
      saturation: 90.0,
      noise_reduction: 1,
      apply_clahe: true,
      clahe_clip_limit: 3.5,
      normalize_hist: true,
      invert_colors: false,
      rotation_deg: 0
    };
    setParams(hc);
    applyCalibration(hc);
  };

  const resetDefaults = () => {
    const def = {
      brightness: 0,
      contrast: 1.0,
      gamma: 1.0,
      sharpness: 0.0,
      saturation: 100.0,
      noise_reduction: 0,
      apply_clahe: false,
      clahe_clip_limit: 2.0,
      normalize_hist: false,
      invert_colors: false,
      rotation_deg: 0
    };
    setParams(def);
    applyCalibration(def);
  };

  const overallScore = scorecard.composite_score ?? scorecard.overall_quality_score ?? 85.0;

  return (
    <div className="camera-vision-deck panel" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Header Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: '32px',
            height: '32px',
            borderRadius: '6px',
            background: 'rgba(0, 229, 255, 0.15)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            border: '1px solid var(--cyan-primary)'
          }}>
            <Camera size={18} style={{ color: 'var(--cyan-primary)' }} />
          </div>
          <div>
            <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 600, letterSpacing: '0.5px' }}>
              OPTICAL SENTRY & VISION DECK
            </h3>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              ESP32-CAM Raw Acquisition, Digital CLAHE & Astronomical Quality Scorecard
            </span>
          </div>
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          {/* View Mode Toggle */}
          <div className="btn-group" style={{ display: 'flex', background: 'rgba(0,0,0,0.3)', borderRadius: '6px', padding: '2px', border: '1px solid var(--border-color)' }}>
            <button
              className={`btn btn-sm ${viewMode === 'processed' ? 'btn-primary' : 'btn-ghost'}`}
              onClick={() => setViewMode('processed')}
              style={{ fontSize: '0.75rem', padding: '4px 10px' }}
            >
              Calibrated Feed
            </button>
            <button
              className={`btn btn-sm ${viewMode === 'raw' ? 'btn-primary' : 'btn-ghost'}`}
              onClick={() => setViewMode('raw')}
              style={{ fontSize: '0.75rem', padding: '4px 10px' }}
            >
              Raw Sensor
            </button>
            <button
              className={`btn btn-sm ${viewMode === 'split' ? 'btn-primary' : 'btn-ghost'}`}
              onClick={() => setViewMode('split')}
              style={{ fontSize: '0.75rem', padding: '4px 10px' }}
            >
              Split View
            </button>
          </div>

          {/* Capture Trigger */}
          <button
            className="btn btn-sm btn-primary"
            onClick={() => captureFrame()}
            disabled={capturing || (systemMode === 'HARDWARE' && !isOnline)}
            style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem' }}
          >
            <RefreshCw size={14} className={capturing ? 'spin' : ''} />
            {capturing ? 'Acquiring...' : 'Capture Frame'}
          </button>

          {/* Open Camera Device (Diagnostic UI) */}
          <a
            href={cameraUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-sm btn-outline"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '0.8rem',
              borderColor: 'var(--amber-primary)',
              color: 'var(--amber-primary)',
              textDecoration: 'none'
            }}
            title="Open ESP32-CAM native web portal directly in browser for hardware diagnostic streaming"
          >
            <ExternalLink size={14} />
            Open Camera Device
          </a>
        </div>
      </div>

      {/* Hardware Offline Alert Banner */}
      {systemMode === 'HARDWARE' && !isOnline && (
        <div style={{
          background: 'rgba(255, 77, 77, 0.1)',
          border: '1px solid var(--red-alert)',
          borderRadius: '6px',
          padding: '10px 14px',
          display: 'flex',
          alignItems: 'center',
          gap: '12px'
        }}>
          <ShieldAlert size={20} style={{ color: 'var(--red-alert)' }} />
          <div style={{ fontSize: '0.82rem' }}>
            <strong>HARDWARE MODE ACTIVE — ESP32-CAM OFFLINE:</strong> Ensure ESP32-CAM module is powered on and connected to the local Wi-Fi network at <code>{cameraUrl}</code>. Live feed will resume once camera heartbeat is detected.
          </div>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div style={{
          background: 'rgba(255, 170, 0, 0.1)',
          border: '1px solid var(--amber-primary)',
          borderRadius: '6px',
          padding: '8px 12px',
          fontSize: '0.8rem',
          color: 'var(--amber-primary)'
        }}>
          Notice: {error}
        </div>
      )}

      {/* Main Grid: Frame Display & Controls */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(320px, 1.4fr) minmax(300px, 1fr)', gap: '16px' }}>
        {/* Left: Viewport View */}
        <div style={{
          background: '#04070c',
          borderRadius: '8px',
          border: '1px solid var(--border-color)',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column'
        }}>
          <div style={{
            padding: '8px 12px',
            background: 'rgba(255, 255, 255, 0.03)',
            borderBottom: '1px solid var(--border-color)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            fontSize: '0.78rem'
          }}>
            <span style={{ color: 'var(--text-muted)' }}>
              MODE: <strong style={{ color: 'var(--cyan-primary)' }}>{viewMode.toUpperCase()}</strong>
            </span>
            <span style={{ color: 'var(--text-muted)' }}>
              STATUS: <strong style={{ color: overallScore >= 75 ? 'var(--green-nominal)' : 'var(--amber-primary)' }}>
                {overallScore >= 75 ? 'OPTIMAL DISK RESOLVED' : 'ACCEPTABLE SEEING'}
              </strong>
            </span>
          </div>

          <div style={{
            flex: 1,
            minHeight: '340px',
            position: 'relative',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: '#000',
            padding: '8px'
          }}>
            {viewMode === 'split' ? (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', width: '100%', height: '100%' }}>
                <div style={{ position: 'relative', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                  <span style={{ position: 'absolute', top: 6, left: 8, fontSize: '0.7rem', background: 'rgba(0,0,0,0.6)', padding: '2px 6px', borderRadius: '4px', zIndex: 2 }}>RAW SENSOR</span>
                  {rawFrame ? (
                    <img src={rawFrame} alt="Raw Frame" style={{ width: '100%', height: 'auto', borderRadius: '4px', objectFit: 'contain' }} />
                  ) : (
                    <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem', margin: 'auto' }}>Awaiting Raw Frame...</div>
                  )}
                </div>
                <div style={{ position: 'relative', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                  <span style={{ position: 'absolute', top: 6, left: 8, fontSize: '0.7rem', background: 'rgba(0,0,0,0.6)', padding: '2px 6px', borderRadius: '4px', zIndex: 2, color: 'var(--cyan-primary)' }}>ENHANCED</span>
                  {procFrame ? (
                    <img src={procFrame} alt="Processed Frame" style={{ width: '100%', height: 'auto', borderRadius: '4px', objectFit: 'contain' }} />
                  ) : (
                    <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem', margin: 'auto' }}>Awaiting Processed Frame...</div>
                  )}
                </div>
              </div>
            ) : viewMode === 'raw' ? (
              rawFrame ? (
                <img src={rawFrame} alt="Raw Feed" style={{ maxWidth: '100%', maxHeight: '420px', borderRadius: '4px', objectFit: 'contain' }} />
              ) : (
                <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Awaiting Raw Camera Feed...</div>
              )
            ) : (
              procFrame ? (
                <img src={procFrame} alt="Processed Feed" style={{ maxWidth: '100%', maxHeight: '420px', borderRadius: '4px', objectFit: 'contain' }} />
              ) : (
                <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Awaiting Calibrated Feed...</div>
              )
            )}

            {/* Overlaid Score Badge */}
            <div style={{
              position: 'absolute',
              bottom: 12,
              right: 12,
              background: 'rgba(6, 11, 19, 0.85)',
              backdropFilter: 'blur(4px)',
              border: '1px solid var(--border-color)',
              borderRadius: '6px',
              padding: '6px 12px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              fontSize: '0.75rem'
            }}>
              <span style={{ color: 'var(--text-muted)' }}>SCORE:</span>
              <strong style={{
                color: overallScore >= 80 ? 'var(--green-nominal)' : overallScore >= 50 ? 'var(--amber-primary)' : 'var(--red-alert)',
                fontSize: '0.95rem'
              }}>
                {overallScore.toFixed(1)} / 100
              </strong>
            </div>
          </div>

          {/* Quick Condition Simulation Switcher (DEMO mode) */}
          {systemMode === 'DEMO' && (
            <div style={{
              padding: '8px 12px',
              background: 'rgba(255, 255, 255, 0.02)',
              borderTop: '1px solid var(--border-color)',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              flexWrap: 'wrap',
              fontSize: '0.75rem'
            }}>
              <span style={{ color: 'var(--text-muted)' }}>Inject Solar Preset:</span>
              <button className="btn btn-xs btn-outline" onClick={() => captureFrame('clear')}>Clear Sun</button>
              <button className="btn btn-xs btn-outline" onClick={() => captureFrame('cloudy')}>Passing Clouds</button>
              <button className="btn btn-xs btn-outline" onClick={() => captureFrame('heavy_clouds')}>Heavy Occlusion</button>
              <button className="btn btn-xs btn-outline" onClick={() => captureFrame('overexposed')}>Flare/Overexp</button>
              <button className="btn btn-xs btn-outline" onClick={() => captureFrame('blurry')}>Defocus</button>
            </div>
          )}
        </div>

        {/* Right: Optical Scorecard & Calibration Controls */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {/* Quality Scorecard Card */}
          <div style={{
            background: 'rgba(0, 229, 255, 0.03)',
            borderRadius: '8px',
            border: '1px solid var(--border-color)',
            padding: '12px 16px'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Activity size={16} style={{ color: 'var(--cyan-primary)' }} />
                <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>IMAGE QUALITY SCORECARD</span>
              </div>
              <span style={{
                fontSize: '0.75rem',
                padding: '2px 8px',
                borderRadius: '4px',
                background: overallScore >= 80 ? 'rgba(0, 230, 118, 0.15)' : 'rgba(255, 170, 0, 0.15)',
                color: overallScore >= 80 ? 'var(--green-nominal)' : 'var(--amber-primary)',
                fontWeight: 600
              }}>
                {overallScore >= 80 ? 'EXCELLENT' : overallScore >= 60 ? 'MODERATE' : 'POOR'}
              </span>
            </div>

            {/* Scorecard Metric Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', fontSize: '0.75rem' }}>
              <div className="metric-box" style={{ background: 'rgba(0,0,0,0.3)', padding: '6px 8px', borderRadius: '4px' }}>
                <div style={{ color: 'var(--text-muted)' }}>Sharpness</div>
                <div style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--cyan-primary)' }}>
                  {(scorecard.sharpness ?? 0).toFixed(1)}
                </div>
              </div>

              <div className="metric-box" style={{ background: 'rgba(0,0,0,0.3)', padding: '6px 8px', borderRadius: '4px' }}>
                <div style={{ color: 'var(--text-muted)' }}>Contrast</div>
                <div style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--cyan-primary)' }}>
                  {(scorecard.contrast ?? 0).toFixed(1)}
                </div>
              </div>

              <div className="metric-box" style={{ background: 'rgba(0,0,0,0.3)', padding: '6px 8px', borderRadius: '4px' }}>
                <div style={{ color: 'var(--text-muted)' }}>Exposure</div>
                <div style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--cyan-primary)' }}>
                  {(scorecard.exposure_quality ?? 0).toFixed(1)}
                </div>
              </div>

              <div className="metric-box" style={{ background: 'rgba(0,0,0,0.3)', padding: '6px 8px', borderRadius: '4px' }}>
                <div style={{ color: 'var(--text-muted)' }}>Dynamic Range</div>
                <div style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-main)' }}>
                  {(scorecard.dynamic_range ?? 0).toFixed(1)}
                </div>
              </div>

              <div className="metric-box" style={{ background: 'rgba(0,0,0,0.3)', padding: '6px 8px', borderRadius: '4px' }}>
                <div style={{ color: 'var(--text-muted)' }}>Noise Level</div>
                <div style={{ fontSize: '0.95rem', fontWeight: 600, color: (scorecard.noise_level ?? 0) < 20 ? 'var(--green-nominal)' : 'var(--amber-primary)' }}>
                  {(scorecard.noise_level ?? 0).toFixed(1)}
                </div>
              </div>

              <div className="metric-box" style={{ background: 'rgba(0,0,0,0.3)', padding: '6px 8px', borderRadius: '4px' }}>
                <div style={{ color: 'var(--text-muted)' }}>Sunspots</div>
                <div style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--amber-primary)' }}>
                  {visionAnalysis.sunspot_count ?? 0}
                </div>
              </div>
            </div>
          </div>

          {/* Interactive Calibration Sliders */}
          <div style={{
            background: 'rgba(255, 255, 255, 0.02)',
            borderRadius: '8px',
            border: '1px solid var(--border-color)',
            padding: '12px 16px',
            display: 'flex',
            flexDirection: 'column',
            gap: '10px'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Sliders size={16} style={{ color: 'var(--amber-primary)' }} />
                <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>CALIBRATION & ENHANCEMENT</span>
              </div>
              <div style={{ display: 'flex', gap: '6px' }}>
                <button
                  className="btn btn-xs btn-outline"
                  onClick={setPresetAuto}
                  title="Apply astronomical auto-enhancement"
                >
                  <Sparkles size={12} style={{ marginRight: '4px' }} />
                  Auto
                </button>
                <button
                  className="btn btn-xs btn-outline"
                  onClick={setPresetHighContrast}
                  title="Enhance sunspot feature contrast"
                >
                  Sunspots
                </button>
                <button
                  className="btn btn-xs btn-ghost"
                  onClick={resetDefaults}
                  title="Reset to neutral sensor values"
                >
                  Reset
                </button>
              </div>
            </div>

            {/* Sliders Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', fontSize: '0.74rem' }}>
              {/* Brightness */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)' }}>
                  <span>Brightness</span>
                  <span>{params.brightness}</span>
                </div>
                <input
                  type="range"
                  min="-60"
                  max="60"
                  value={params.brightness}
                  onChange={(e) => {
                    const next = { ...params, brightness: Number(e.target.value) };
                    setParams(next);
                  }}
                  onMouseUp={() => applyCalibration()}
                  style={{ width: '100%' }}
                />
              </div>

              {/* Contrast */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)' }}>
                  <span>Contrast</span>
                  <span>{params.contrast.toFixed(2)}x</span>
                </div>
                <input
                  type="range"
                  min="0.5"
                  max="2.5"
                  step="0.05"
                  value={params.contrast}
                  onChange={(e) => {
                    const next = { ...params, contrast: Number(e.target.value) };
                    setParams(next);
                  }}
                  onMouseUp={() => applyCalibration()}
                  style={{ width: '100%' }}
                />
              </div>

              {/* Gamma */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)' }}>
                  <span>Gamma</span>
                  <span>{params.gamma.toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min="0.4"
                  max="2.0"
                  step="0.05"
                  value={params.gamma}
                  onChange={(e) => {
                    const next = { ...params, gamma: Number(e.target.value) };
                    setParams(next);
                  }}
                  onMouseUp={() => applyCalibration()}
                  style={{ width: '100%' }}
                />
              </div>

              {/* Sharpness / Unsharp Mask */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)' }}>
                  <span>Sharpness</span>
                  <span>{params.sharpness.toFixed(0)}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={params.sharpness}
                  onChange={(e) => {
                    const next = { ...params, sharpness: Number(e.target.value) };
                    setParams(next);
                  }}
                  onMouseUp={() => applyCalibration()}
                  style={{ width: '100%' }}
                />
              </div>
            </div>

            {/* CLAHE & Invert Toggles */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              paddingTop: '6px',
              borderTop: '1px solid var(--border-color)',
              fontSize: '0.75rem'
            }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={params.apply_clahe}
                  onChange={(e) => {
                    const next = { ...params, apply_clahe: e.target.checked };
                    setParams(next);
                    applyCalibration(next);
                  }}
                />
                <span>Adaptive CLAHE Equalization</span>
              </label>

              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={params.invert_colors}
                  onChange={(e) => {
                    const next = { ...params, invert_colors: e.target.checked };
                    setParams(next);
                    applyCalibration(next);
                  }}
                />
                <span>Invert (Solar Negative)</span>
              </label>

              <button
                className="btn btn-xs btn-ghost"
                onClick={() => {
                  const nextDeg = (params.rotation_deg + 90) % 360;
                  const next = { ...params, rotation_deg: nextDeg };
                  setParams(next);
                  applyCalibration(next);
                }}
                title="Rotate image 90 degrees"
                style={{ display: 'flex', alignItems: 'center', gap: '4px' }}
              >
                <RotateCw size={12} />
                {params.rotation_deg}°
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
