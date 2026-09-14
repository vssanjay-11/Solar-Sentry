import React, { useRef, useEffect } from 'react';
import { useObservatory } from '../../context/ObservatoryContext';
import { Compass, Move } from 'lucide-react';

export const DigitalTwinPanel: React.FC = () => {
  const { telemetry, missionTarget } = useObservatory();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;

    // Clear
    ctx.fillStyle = '#060a12';
    ctx.fillRect(0, 0, width, height);

    // Coordinate origin at center-bottom
    const ox = width / 2;
    const oy = height * 0.72;

    // Draw isometric / 3D grid plane
    ctx.strokeStyle = 'rgba(0, 229, 255, 0.08)';
    ctx.lineWidth = 1;
    for (let i = -6; i <= 6; i++) {
      ctx.beginPath();
      ctx.moveTo(ox + i * 22, oy - 20);
      ctx.lineTo(ox + i * 36, oy + 50);
      ctx.stroke();

      ctx.beginPath();
      ctx.moveTo(ox - 160 + i * 10, oy + i * 7);
      ctx.lineTo(ox + 160 - i * 10, oy + i * 7);
      ctx.stroke();
    }

    // Compass circle on base
    ctx.strokeStyle = 'rgba(0, 229, 255, 0.2)';
    ctx.beginPath();
    ctx.ellipse(ox, oy, 70, 24, 0, 0, Math.PI * 2);
    ctx.stroke();

    // Azimuth cardinal markers
    ctx.fillStyle = 'var(--text-dim)';
    ctx.font = '9px monospace';
    ctx.textAlign = 'center';
    ctx.fillText('N (0°)', ox, oy - 28);
    ctx.fillText('S (180°)', ox, oy + 32);
    ctx.fillText('W (90°)', ox - 78, oy + 3);
    ctx.fillText('E (270°)', ox + 78, oy + 3);

    // 1. Base Pedestal
    ctx.fillStyle = '#162235';
    ctx.strokeStyle = '#273b5c';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.ellipse(ox, oy - 8, 48, 16, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    // 2. Pan Turntable (Rotates around Y-axis based on pan angle 0-180°)
    // Map pan 0-180 to visual angle (-60deg to +60deg)
    const panNorm = (telemetry.pan - 90) / 90; // -1.0 to +1.0
    const panAngle = panNorm * (Math.PI / 3);

    const turntableHeight = 14;
    ctx.fillStyle = '#1e304d';
    ctx.strokeStyle = 'var(--cyan-primary)';
    ctx.beginPath();
    ctx.ellipse(ox, oy - 14, 38, 12, panAngle, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    // 3. Dual-Axis Fork Arms
    const forkHeight = 55;
    const armSpacing = 28;
    const armLeftX = ox - armSpacing * Math.cos(panAngle);
    const armLeftY = (oy - 14) - armSpacing * Math.sin(panAngle) * 0.3;
    const armRightX = ox + armSpacing * Math.cos(panAngle);
    const armRightY = (oy - 14) + armSpacing * Math.sin(panAngle) * 0.3;

    ctx.strokeStyle = '#385580';
    ctx.lineWidth = 5;
    // Left Fork
    ctx.beginPath();
    ctx.moveTo(armLeftX, armLeftY);
    ctx.lineTo(armLeftX, armLeftY - forkHeight);
    ctx.stroke();
    // Right Fork
    ctx.beginPath();
    ctx.moveTo(armRightX, armRightY);
    ctx.lineTo(armRightX, armRightY - forkHeight);
    ctx.stroke();

    // 4. Tilt Pivot & Telescope Tube
    const pivotX = ox;
    const pivotY = oy - 14 - forkHeight;

    // Tilt angle 0-180: 0° is stowed flat down, 90° is zenith pointing straight up
    const tiltRad = (telemetry.tilt / 180) * Math.PI; // 0 (stowed) to PI (back)
    const barrelLength = 65;
    const barrelRadius = 14;

    // Direction vector of optical tube
    const dirX = Math.sin(tiltRad) * Math.sin(panAngle);
    const dirY = -Math.sin(tiltRad) * Math.cos(panAngle) * 0.4 - Math.cos(tiltRad);

    const tubeEndX = pivotX + dirX * barrelLength;
    const tubeEndY = pivotY + dirY * barrelLength;
    const tubeBackX = pivotX - dirX * (barrelLength * 0.4);
    const tubeBackY = pivotY - dirY * (barrelLength * 0.4);

    // Draw Optical Tube Barrel
    ctx.strokeStyle = '#ffaa00';
    ctx.lineWidth = barrelRadius;
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.moveTo(tubeBackX, tubeBackY);
    ctx.lineTo(tubeEndX, tubeEndY);
    ctx.stroke();
    ctx.lineCap = 'butt';

    // Boresight Laser Line (Aiming Ray)
    ctx.strokeStyle = 'rgba(0, 255, 157, 0.7)';
    ctx.lineWidth = 1.5;
    ctx.setLineDash([5, 5]);
    ctx.beginPath();
    ctx.moveTo(tubeEndX, tubeEndY);
    ctx.lineTo(tubeEndX + dirX * 90, tubeEndY + dirY * 90);
    ctx.stroke();
    ctx.setLineDash([]);

    // 5. Sun Target Vector Representation
    // Draw Sun Icon in Sky
    const sunSkyX = width * 0.78;
    const sunSkyY = height * 0.22;
    
    // Sun Rays
    ctx.strokeStyle = 'rgba(255, 170, 0, 0.3)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(pivotX, pivotY);
    ctx.lineTo(sunSkyX, sunSkyY);
    ctx.stroke();

    // Sun disk in sky
    const sunGlow = ctx.createRadialGradient(sunSkyX, sunSkyY, 4, sunSkyX, sunSkyY, 24);
    sunGlow.addColorStop(0, '#fff4b8');
    sunGlow.addColorStop(0.4, '#ffaa00');
    sunGlow.addColorStop(1, 'transparent');
    ctx.fillStyle = sunGlow;
    ctx.beginPath();
    ctx.arc(sunSkyX, sunSkyY, 24, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = '#ffaa00';
    ctx.font = '9px monospace';
    ctx.fillText(`SOL (Az: ${missionTarget.target_azimuth}°, El: ${missionTarget.target_elevation}°)`, sunSkyX, sunSkyY + 34);

  }, [telemetry.pan, telemetry.tilt, missionTarget]);

  return (
    <div className="hud-panel">
      <div className="panel-header">
        <div className="panel-title">
          <Compass size={14} />
          <span>Digital Twin • Dual-Axis Tracker</span>
        </div>
        <div style={{ display: 'flex', gap: '8px', fontFamily: 'var(--font-mono)', fontSize: '10px' }}>
          <span style={{ color: 'var(--cyan-primary)' }}>PAN: {telemetry.pan}°</span>
          <span style={{ color: 'var(--solar-gold)' }}>TILT: {telemetry.tilt}°</span>
        </div>
      </div>

      <div className="panel-body" style={{ padding: 0 }}>
        <div className="twin-canvas-wrapper">
          <canvas ref={canvasRef} width={480} height={260} />

          <div className="twin-overlay-stats">
            <span style={{ color: 'var(--text-bright)', fontWeight: 700 }}>SERVO KINEMATICS</span>
            <span style={{ color: 'var(--cyan-primary)' }}>Pan Angle: {telemetry.pan}° (0-180°)</span>
            <span style={{ color: 'var(--solar-gold)' }}>Tilt Angle: {telemetry.tilt}° (0-180°)</span>
            <span style={{ color: 'var(--status-green)' }}>
              Tracking Error: {missionTarget.tracking_error_deg}°
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
