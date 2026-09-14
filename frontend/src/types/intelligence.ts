export type AIDecisionState = 'OBSERVE' | 'WAIT' | 'SUSPEND' | 'SAFE' | 'SCAN';

export interface ORSFactors {
  solar_elevation: number;       // 0-100
  atmospheric_seeing: number;    // 0-100
  cloud_transparency: number;    // 0-100
  sensor_health: number;         // 0-100
  tracking_stability: number;    // 0-100
}

export type TrendDirection = 'INCREASING' | 'STABLE' | 'SLIGHT_DECLINE' | 'DEGRADING' | 'UNCERTAIN';

export interface PredictionHorizon {
  horizon_minutes: number;
  score: number; // 0-100
  trend: TrendDirection;
  confidence_lower: number; // 0-100
  confidence_upper: number; // 0-100
}

export interface ObservatoryHealth {
  overall: number;       // 0-100
  edge_hardware: number; // 0-100
  optical_vision: number;// 0-100
  network_comms: number; // 0-100
  anomaly_score: number; // 0.0 - 1.0 (Isolation Forest)
  is_anomaly: boolean;
}

export interface SunspotFeature {
  id: string;
  x: number;
  y: number;
  area_px: number;
  intensity_ratio: number;
}

export interface SolarVisionMetadata {
  timestamp: string;
  image_url: string;
  disk_detected: boolean;
  center_x: number;
  center_y: number;
  radius_px: number;
  limb_darkening_coeff: number;
  sunspots: SunspotFeature[];
  cloud_occlusion_percent: number;
  sharpness_score: number;
  contrast_score: number;
  exposure_ms: number;
}

export interface FeatureAttribution {
  feature: string;
  weight: number; // -1.0 to +1.0
  impact: 'POSITIVE' | 'NEGATIVE' | 'NEUTRAL';
  description: string;
}

export interface MetricDelta {
  metric: string;
  current: number;
  threshold: number;
  unit: string;
  ok: boolean;
}

export interface XAIExplanation {
  decision: AIDecisionState;
  confidence: number; // 0.0 to 1.0 (e.g. 0.91)
  why_factors: string[];
  feature_weights: FeatureAttribution[];
  threshold_deltas: MetricDelta[];
  uncertainty_reason?: string;
}
