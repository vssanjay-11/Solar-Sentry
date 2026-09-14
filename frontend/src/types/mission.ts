import { SensorTelemetry } from './telemetry';
import { AIDecisionState, SolarVisionMetadata } from './intelligence';

export type MissionPhase =
  | 'INITIALIZATION'
  | 'CALIBRATION'
  | 'SLEW'
  | 'ACQUISITION'
  | 'TRACKING'
  | 'VERIFICATION'
  | 'STOW'
  | 'SUSPENDED';

export interface MissionTarget {
  id: string;
  name: string;
  solar_object: string;
  target_azimuth: number;   // 0-360 deg
  target_elevation: number; // 0-90 deg
  target_pan: number;       // 0-180 deg
  target_tilt: number;      // 0-180 deg
  tracking_error_deg: number;
}

export interface MissionTimelineItem {
  id: string;
  title: string;
  phase: MissionPhase;
  status: 'COMPLETED' | 'ACTIVE' | 'UPCOMING' | 'ABORTED';
  start_time: string;
  duration_minutes: number;
  description: string;
}

export interface ReplayFrame {
  timestamp: string;
  telemetry: SensorTelemetry;
  decision: AIDecisionState;
  decision_confidence: number;
  ors_score: number;
  vision: SolarVisionMetadata;
  notes: string;
}
