export type EdgeSystemState =
  | 'BOOT'
  | 'SELF_CHECK'
  | 'STANDBY'
  | 'OBSERVE'
  | 'WAIT'
  | 'SCAN'
  | 'SUSPEND'
  | 'FAULT'
  | 'SAFE'
  | 'DEGRADED';

export interface SensorStatus {
  dht22: boolean;
  bh1750: boolean;
  bmp280: boolean;
  rain: boolean;
}

export interface SensorTelemetry {
  device_id: string;
  timestamp: string;
  uptime_seconds: number;
  temperature: number; // Celsius (DHT22 / BMP280 fallback)
  humidity: number;    // % (DHT22)
  pressure: number;    // hPa (BMP280)
  lux: number;         // Lux (BH1750)
  rain_raw: number;    // 12-bit ADC (0-4095)
  rain_detected: boolean;
  pan: number;         // Degrees (0-180)
  tilt: number;        // Degrees (0-180)
  state: EdgeSystemState;
  health: number;      // 0-100% computed locally
  wifi_rssi: number;   // dBm
  camera_online: boolean;
  camera_ip?: string;
  sensor_status: SensorStatus;
  firmware_version: string;
}

export interface TelemetryPoint {
  timestamp: string;
  temperature: number;
  humidity: number;
  pressure: number;
  lux: number;
  rain_raw: number;
  pan: number;
  tilt: number;
  ors: number;
}
