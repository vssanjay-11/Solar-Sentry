import React, { useRef, useEffect } from 'react';
import { useObservatory } from '../../context/ObservatoryContext';
import { Eye, Crosshair, Camera } from 'lucide-react';

export const SolarVisionPanel: React.FC = () => {
  const { vision, telemetry } = useObservatory();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Render optical solar disk simulation and computer vision overlays
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;

    // Clear black sky background
    ctx.fillStyle = '#030508';
    ctx.fillRect(0, 0, width, height);

    // Subtle star field background
    ctx.fillStyle = '#ffffff33';
    for (let i = 0; i < 25; i++) {
      const sx = (Math.sin(i * 99) * 0.5 + 0.5) * width;
      const sy = (Math.cos(i * 33) * 0.5 + 0.5) * height;
      ctx.fillRect(sx, sy, 1, 1);
    }

    const cx = vision.center_x * (width / 640);
    const cy = vision.center_y * (height / 480);
    const r = vision.radius_px * (width / 640);

    if (vision.disk_detected && telemetry.state !== 'SUSPEND') {
      // Solar Corona / Glow
      const coronaGradient = ctx.createRadialGradient(cx, cy, r * 0.8, cx, cy, r * 1.6);
      coronaGradient.addColorStop(0, 'rgba(255, 170, 0, 0.4)');
      coronaGradient.addColorStop(0.5, 'rgba(255, 120, 0, 0.15)');
      coronaGradient.addColorStop(1, 'rgba(0, 0, 0, 0)');
      ctx.fillStyle = coronaGradient;
      ctx.beginPath();
      ctx.arc(cx, cy, r * 1.6, 0, Math.PI * 2);
      ctx.fill();

      // Solar Photosphere Disk with Limb Darkening
      const diskGradient = ctx.createRadialGradient(cx, cy, 0, cx, cy, r);
      diskGradient.addColorStop(0, '#fff4cc');
      diskGradient.addColorStop(0.6, '#ffaa00');
      diskGradient.addColorStop(0.9, '#e66000');
      diskGradient.addColorStop(1, '#661100'); // Limb darkening edge
      ctx.fillStyle = diskGradient;
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.fill();

      // Draw Sunspots
      vision.sunspots.forEach((spot) => {
        const spotX = spot.x * (width / 640);
        const spotY = spot.y * (height / 480);
        const spotRadius = Math.max(3, Math.sqrt(spot.area_px) * 0.8);

        // Penumbra
        ctx.fillStyle = 'rgba(70, 30, 0, 0.8)';
        ctx.beginPath();
        ctx.arc(spotX, spotY, spotRadius * 1.5, 0, Math.PI * 2);
        ctx.fill();

        // Umbra (dark center)
        ctx.fillStyle = '#110500';
        ctx.beginPath();
        ctx.arc(spotX, spotY, spotRadius * 0.8, 0, Math.PI * 2);
        ctx.fill();

        // AI Bounding Box & Label
        ctx.strokeStyle = 'var(--cyan-primary)';
        ctx.lineWidth = 1;
        const boxSize = spotRadius * 3.5;
        ctx.strokeRect(spotX - boxSize / 2, spotY - boxSize / 2, boxSize, boxSize);

        ctx.fillStyle = 'var(--cyan-primary)';
        ctx.font = '9px monospace';
        ctx.fillText(spot.id, spotX - boxSize / 2, spotY - boxSize / 2 - 3);
      });

      // AI Solar Disk Detection Circle
      ctx.strokeStyle = 'rgba(0, 229, 255, 0.7)';
      ctx.lineWidth = 1.5;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.stroke();
      ctx.setLineDash([]);

      // Disk Center Crosshair
      ctx.strokeStyle = 'var(--cyan-primary)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(cx - 10, cy); ctx.lineTo(cx + 10, cy);
      ctx.moveTo(cx, cy - 10); ctx.lineTo(cx, cy + 10);
      ctx.stroke();

    } else {
      // Disk not detected or stowed
      ctx.fillStyle = '#ff2a5f';
      ctx.font = '12px monospace';
      ctx.textAlign = 'center';
      ctx.fillText(
        telemetry.state === 'SUSPEND' ? 'OPTICAL SHUTTER CLOSED [STOWED]' : 'NO SOLAR DISK RESOLVED',
        width / 2,
        height / 2
      );
    }

    // Grid Reticle and Corner HUD Brackets
    ctx.strokeStyle = 'rgba(0, 229, 255, 0.25)';
    ctx.lineWidth = 1;
    // Corners
    const m = 12; const cl = 16;
    ctx.beginPath();
    // Top-Left
    ctx.moveTo(m, m + cl); ctx.lineTo(m, m); ctx.lineTo(m + cl, m);
    // Top-Right
    ctx.moveTo(width - m - cl, m); ctx.lineTo(width - m, m); ctx.lineTo(width - m, m + cl);
    // Bottom-Left
    ctx.moveTo(m, height - m - cl); ctx.lineTo(m, height - m); ctx.lineTo(m + cl, height - m);
    // Bottom-Right
    ctx.moveTo(width - m - cl, height - m); ctx.lineTo(width - m, height - m); ctx.lineTo(width - m, height - m - cl);
    ctx.stroke();

  }, [vision, telemetry.state]);

  return (
    <div className="hud-panel">
      <div className="panel-header">
        <div className="panel-title">
          <Camera size={14} />
          <span>Optical Viewport (ESP32-CAM)</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontFamily: 'var(--font-mono)', fontSize: '10px' }}>
          <span style={{ color: vision.disk_detected ? 'var(--status-green)' : 'var(--status-red)', fontWeight: 700 }}>
            {vision.disk_detected ? 'DISK ACQUIRED' : 'NO TARGET'}
          </span>
        </div>
      </div>

      <div className="panel-body" style={{ padding: 0 }}>
        <div className="camera-viewport">
          <canvas ref={canvasRef} width={480} height={320} />

          {/* Bottom Telemetry Overlay Strip */}
          <div className="camera-stats-bar">
            <span>RES: 640x480 RAW</span>
            <span>EXP: {vision.exposure_ms} ms</span>
            <span>SHARPNESS: {vision.sharpness_score.toFixed(1)}</span>
            <span>CONTRAST: {vision.contrast_score.toFixed(1)}</span>
          </div>
        </div>
      </div>
    </div>
  );
};
