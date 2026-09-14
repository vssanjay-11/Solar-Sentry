export type AlertSeverity = 'INFO' | 'WARNING' | 'CRITICAL';

export interface AnomalyAlert {
  alert_id: string;
  timestamp: string;
  severity: AlertSeverity;
  type: string;
  message: string;
  acknowledged: boolean;
  source: 'EDGE' | 'AI_FUSION' | 'VISION' | 'COMMS';
  metric_name?: string;
  anomaly_score?: number;
}

export interface EventLogEntry {
  id: string;
  timestamp: string;
  level: 'INFO' | 'WARN' | 'ERROR' | 'SAFETY' | 'AI';
  category: 'EDGE' | 'ACTUATOR' | 'VISION' | 'COGNITIVE' | 'NETWORK';
  message: string;
}
