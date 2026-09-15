import { SensorTelemetry } from '../types/telemetry';
import { CommandPayload, CommandResult } from '../types/command';
import { AnomalyAlert } from '../types/alerts';
import { MissionTimelineItem, MissionTarget, ReplayFrame } from '../types/mission';

const API_BASE = '/api/v1';

export class ObservatoryApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
  }

  async getLiveTelemetry(): Promise<SensorTelemetry> {
    const res = await fetch(`${this.baseUrl}/telemetry/live`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch live telemetry`);
    return res.json();
  }

  async getTelemetryHistory(range: '15m' | '1h' | '6h' | '24h' = '1h'): Promise<SensorTelemetry[]> {
    const res = await fetch(`${this.baseUrl}/telemetry/history?range=${range}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch historical telemetry`);
    return res.json();
  }

  async dispatchCommand(command: CommandPayload): Promise<CommandResult> {
    const res = await fetch(`${this.baseUrl}/device/command`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(command),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: Command dispatch failed`);
    return res.json();
  }

  async acknowledgeAlert(alertId: string): Promise<{ status: string }> {
    const res = await fetch(`${this.baseUrl}/alerts/${alertId}/ack`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: Alert ack failed`);
    return res.json();
  }

  async getActiveMission(): Promise<{ target: MissionTarget; timeline: MissionTimelineItem[] }> {
    const res = await fetch(`${this.baseUrl}/mission/active`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch active mission`);
    return res.json();
  }

  async getReplaySession(sessionId: string): Promise<ReplayFrame[]> {
    const res = await fetch(`${this.baseUrl}/replay/${sessionId}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch replay session`);
    return res.json();
  }

  async getSystemStatus(): Promise<{
    project: string;
    mode: 'DEMO' | 'HARDWARE';
    system_mode: string;
    status: string;
    device_connected: boolean;
    active_device_id: string;
    camera_status: any;
    hardware_verified: boolean;
  }> {
    const res = await fetch(`${this.baseUrl}/system/status`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch system status`);
    return res.json();
  }

  async switchSystemMode(mode: 'DEMO' | 'HARDWARE'): Promise<{ status: string; mode: string; message: string }> {
    const res = await fetch(`${this.baseUrl}/system/mode`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode })
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to switch system mode`);
    return res.json();
  }

  async captureCameraFrame(condition?: string): Promise<{
    status: string;
    raw_image_data: string;
    processed_image_data: string;
    quality_score: number;
    scorecard: Record<string, number>;
    vision_analysis: any;
  }> {
    const query = condition ? `?condition=${encodeURIComponent(condition)}` : '';
    const res = await fetch(`${this.baseUrl}/camera/capture${query}`, { method: 'POST' });
    if (!res.ok) throw new Error(`HTTP ${res.status}: Camera capture failed`);
    return res.json();
  }

  async calibrateCamera(params: {
    brightness: number;
    contrast: number;
    gamma: number;
    sharpness: number;
    saturation: number;
    noise_reduction: number;
    apply_clahe: boolean;
    clahe_clip_limit: number;
    normalize_hist: boolean;
    invert_colors: boolean;
    rotation_deg: number;
  }): Promise<{
    status: string;
    raw_image_data: string;
    processed_image_data: string;
    quality_score: number;
    scorecard: Record<string, number>;
    vision_analysis: any;
  }> {
    const res = await fetch(`${this.baseUrl}/camera/calibrate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params)
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: Calibration failed`);
    return res.json();
  }

  async getCameraStatus(): Promise<any> {
    const res = await fetch(`${this.baseUrl}/camera/status`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch camera status`);
    return res.json();
  }

  async configureCameraUrl(esp32CamUrl: string): Promise<any> {
    const res = await fetch(`${this.baseUrl}/camera/config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ esp32_cam_url: esp32CamUrl })
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: Camera URL config failed`);
    return res.json();
  }

  async discoverCamera(fallbackIp?: string): Promise<any> {
    const query = fallbackIp ? `?fallback_ip=${encodeURIComponent(fallbackIp)}` : '';
    const res = await fetch(`${this.baseUrl}/camera/discover${query}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Camera discovery failed`);
    return res.json();
  }

  getCameraStreamUrl(): string {
    return `${this.baseUrl}/camera/stream`;
  }
}

export const observatoryApi = new ObservatoryApiClient();

