import { SensorTelemetry, EdgeSystemState, TelemetryPoint } from '../types/telemetry';
import { CommandPayload, CommandResult } from '../types/command';
import { AIDecisionState, ORSFactors, PredictionHorizon, ObservatoryHealth, SolarVisionMetadata, XAIExplanation } from '../types/intelligence';
import { MissionTarget, MissionTimelineItem, ReplayFrame } from '../types/mission';
import { AnomalyAlert, EventLogEntry } from '../types/alerts';

export type SimulationScenarioId = 
  | 'CLEAR_SKY_OPTIMAL'
  | 'SUDDEN_RAIN_ALARM'
  | 'CLOUD_TRANSIT'
  | 'SENSOR_DRIFT_DEGRADED'
  | 'COMMS_LOSS_FAILSAFE'
  | 'RAPID_SOLAR_FLARE_ALERT'
  | 'HIGH_WIND_GUST_STOW'
  | 'THERMAL_OVERHEAT_THROTTLE'
  | 'DUST_SOILING_EVALUATION'
  | 'SOLAR_ECLIPSE_TRACKING';

export interface SimulationScenarioMeta {
  id: SimulationScenarioId;
  name: string;
  description: string;
  expectedState: EdgeSystemState;
  expectedDecision: AIDecisionState;
}

export const SIMULATION_SCENARIOS: SimulationScenarioMeta[] = [
  {
    id: 'CLEAR_SKY_OPTIMAL',
    name: '1. Clear Sky Optimal Tracking',
    description: 'Direct solar line-of-sight, ORS 92%, nominal disk resolution, sunspot cluster AR3664 resolved.',
    expectedState: 'OBSERVE',
    expectedDecision: 'OBSERVE'
  },
  {
    id: 'CLOUD_TRANSIT',
    name: '2. Cloud Transit & Quality Dip',
    description: 'Cirrus cloud cover transiting solar disk, illuminance drops, decision shifts to WAIT with explainability.',
    expectedState: 'WAIT',
    expectedDecision: 'WAIT'
  },
  {
    id: 'SUDDEN_RAIN_ALARM',
    name: '3. Sudden Precipitation Alarm',
    description: 'Rain sensor ADC trips <2000, hardware auto-stows pan/tilt (90, 0), emergency SUSPEND state forced.',
    expectedState: 'SUSPEND',
    expectedDecision: 'SUSPEND'
  },
  {
    id: 'SENSOR_DRIFT_DEGRADED',
    name: '4. Sensor Disagreement & Anomaly',
    description: 'BMP280 vs DHT22 temperature divergence, Isolation Forest flags anomaly, system enters DEGRADED mode.',
    expectedState: 'DEGRADED',
    expectedDecision: 'SCAN'
  },
  {
    id: 'COMMS_LOSS_FAILSAFE',
    name: '5. Communication Loss Failsafe',
    description: 'Simulates 30s heartbeat timeout. Edge safety state machine triggers SAFE mode with hardware parking.',
    expectedState: 'SAFE',
    expectedDecision: 'SAFE'
  },
  {
    id: 'RAPID_SOLAR_FLARE_ALERT',
    name: '6. Rapid Solar Flare Optical Spike',
    description: 'Sudden optical flux and extreme contrast surge around active region AR3664, trigger high-rate cadence.',
    expectedState: 'OBSERVE',
    expectedDecision: 'OBSERVE'
  },
  {
    id: 'HIGH_WIND_GUST_STOW',
    name: '7. High Wind Gust & Safety Stow',
    description: 'Barometric fluctuation and turbulence exceed threshold; dual-axis servos lock in minimum drag pose (90, 0).',
    expectedState: 'SAFE',
    expectedDecision: 'SAFE'
  },
  {
    id: 'THERMAL_OVERHEAT_THROTTLE',
    name: '8. Enclosure Thermal Overheat',
    description: 'Enclosure temperature exceeds 48°C; duty cycle throttled to prevent sensor drift and CMOS sensor noise.',
    expectedState: 'DEGRADED',
    expectedDecision: 'WAIT'
  },
  {
    id: 'DUST_SOILING_EVALUATION',
    name: '9. Optical Deck Soiling & Dust Drift',
    description: 'Uniform attenuation and contrast reduction across field of view; vision pipeline flags cleaning recommendation.',
    expectedState: 'OBSERVE',
    expectedDecision: 'SCAN'
  },
  {
    id: 'SOLAR_ECLIPSE_TRACKING',
    name: '10. Solar Eclipse Transit Tracking',
    description: 'Curved lunar occlusion transits disk; high seeing quality maintained while illuminance drops progressively.',
    expectedState: 'OBSERVE',
    expectedDecision: 'OBSERVE'
  }
];

export class ObservatorySimulator {
  private currentScenario: SimulationScenarioId = 'CLEAR_SKY_OPTIMAL';
  private uptimeSeconds = 4820;
  private pan = 90;
  private tilt = 48;
  private stepCount = 0;

  // Scenario state overrides
  public setScenario(scenario: SimulationScenarioId): void {
    this.currentScenario = scenario;
    if (scenario === 'SUDDEN_RAIN_ALARM' || scenario === 'COMMS_LOSS_FAILSAFE' || scenario === 'HIGH_WIND_GUST_STOW') {
      this.pan = 90;
      this.tilt = 0; // Stowed
    } else if (scenario === 'CLEAR_SKY_OPTIMAL' || scenario === 'RAPID_SOLAR_FLARE_ALERT' || scenario === 'SOLAR_ECLIPSE_TRACKING') {
      this.pan = 92;
      this.tilt = 51;
    }
  }


  public getScenario(): SimulationScenarioId {
    return this.currentScenario;
  }

  public tick(): {
    telemetry: SensorTelemetry;
    decision: AIDecisionState;
    ors_score: number;
    ors_factors: ORSFactors;
    health: ObservatoryHealth;
    predictions: Record<'horizon_15m' | 'horizon_30m' | 'horizon_60m', PredictionHorizon>;
    xai: XAIExplanation;
    vision: SolarVisionMetadata;
    alerts: AnomalyAlert[];
    event?: EventLogEntry;
  } {
    this.uptimeSeconds += 1;
    this.stepCount += 1;
    const nowIso = new Date().toISOString();

    let state: EdgeSystemState = 'OBSERVE';
    let decision: AIDecisionState = 'OBSERVE';
    let confidence = 0.94;
    let ors = 91;
    let temp = 27.8;
    let humidity = 43.5;
    let pressure = 1013.8;
    let lux = 52400;
    let rainRaw = 3880;
    let rainDetected = false;
    let overallHealth = 99;
    let anomalyScore = 0.03;
    let isAnomaly = false;
    let dht22Ok = true;
    let bh1750Ok = true;
    let bmp280Ok = true;
    let rainOk = true;
    let cameraOnline = true;
    let cloudOcclusion = 0.0;
    let sharpness = 92.4;
    let contrast = 95.1;

    let whyFactors: string[] = [
      'Solar disk clearly resolved at high SNR',
      'Illuminance (52,400 Lux) exceeds direct solar threshold (>40k)',
      'Relative humidity stable at 43.5% (optical safety limit: <75%)',
      'Pointing error within tolerance (< 0.5° deviation)'
    ];

    let featureWeights: import('../types/intelligence').FeatureAttribution[] = [
      { feature: 'Direct Solar Lux', weight: 0.85, impact: 'POSITIVE' as const, description: 'High clear-sky irradiance' },
      { feature: 'Atmospheric Seeing', weight: 0.72, impact: 'POSITIVE' as const, description: 'Stable thermal boundary layer' },
      { feature: 'Cloud Occlusion', weight: -0.05, impact: 'NEUTRAL' as const, description: '0% cloud transit' },
      { feature: 'Precipitation Risk', weight: -0.02, impact: 'NEUTRAL' as const, description: 'Dry sensor matrix' },
    ];

    const alerts: AnomalyAlert[] = [];

    // Scenario specific behaviors
    if (this.currentScenario === 'CLEAR_SKY_OPTIMAL') {
      state = 'OBSERVE';
      decision = 'OBSERVE';
      confidence = 0.94;
      ors = 92;
      lux = 52000 + Math.sin(this.stepCount * 0.1) * 800;
      this.pan = 92 + Math.sin(this.stepCount * 0.05) * 0.8;
      this.tilt = 51 + Math.cos(this.stepCount * 0.05) * 0.6;
    } else if (this.currentScenario === 'CLOUD_TRANSIT') {
      state = 'WAIT';
      decision = 'WAIT';
      confidence = 0.91;
      ors = 48;
      humidity = 68.2 + Math.sin(this.stepCount * 0.2) * 4.0;
      lux = 14200 + Math.sin(this.stepCount * 0.2) * 2000;
      cloudOcclusion = 64.5;
      sharpness = 42.1;
      contrast = 51.0;
      anomalyScore = 0.22;
      whyFactors = [
        'Cloud transit detected: illuminance dropped by 72%',
        'Humidity increasing rapidly (+15.4% over 10 min window)',
        'Optical image contrast degraded below scientific threshold',
        '15-min predictive model forecasts sub-threshold ORS (<50)'
      ];
      featureWeights = [
        { feature: 'Cloud Transit', weight: -0.88, impact: 'NEGATIVE' as const, description: 'Direct solar disk obstructed' },
        { feature: 'Humidity Surge', weight: -0.65, impact: 'NEGATIVE' as const, description: 'Approaching dew-point condensation threshold' },
        { feature: 'Optical Contrast', weight: -0.58, impact: 'NEGATIVE' as const, description: 'Limb darkening fit blurred' }
      ];
      alerts.push({
        alert_id: `alt-cloud-${this.stepCount}`,
        timestamp: nowIso,
        severity: 'WARNING',
        type: 'CLOUD_OCCLUSION_EXCURSION',
        message: 'Solar disk obscured by cloud transit (64.5% occlusion). Observation paused.',
        acknowledged: false,
        source: 'VISION'
      });
    } else if (this.currentScenario === 'SUDDEN_RAIN_ALARM') {
      state = 'SUSPEND';
      decision = 'SUSPEND';
      confidence = 0.99;
      ors = 8;
      rainRaw = 1240; // ADC tripped
      rainDetected = true;
      humidity = 94.2;
      lux = 4100;
      this.pan = 90;
      this.tilt = 0; // Emergency stowed
      overallHealth = 70;
      anomalyScore = 0.89;
      isAnomaly = true;
      cloudOcclusion = 98.0;
      whyFactors = [
        'CRITICAL SAFETY OVERRIDE: Rain sensor triggered (ADC 1240 < 2000)',
        'Dual-axis servos automatically stowed to storm-safe park (90°, 0°)',
        'Red indicator LED locked solid; observation suspended indefinitely',
        'Rule Hierarchy: SAFETY > OBSERVATION OBJECTIVE'
      ];
      featureWeights = [
        { feature: 'Rain ADC Trip', weight: -0.99, impact: 'NEGATIVE' as const, description: 'Precipitation liquid detected on optical deck' },
        { feature: 'Relative Humidity', weight: -0.92, impact: 'NEGATIVE' as const, description: 'Atmospheric saturation >90%' }
      ];
      alerts.push({
        alert_id: `alt-rain-${this.stepCount}`,
        timestamp: nowIso,
        severity: 'CRITICAL',
        type: 'PRECIPITATION_EMERGENCY_OVERRIDE',
        message: 'Rain sensor ADC tripped (1240). Edge firmware auto-stowed actuators to (90, 0).',
        acknowledged: false,
        source: 'EDGE'
      });
    } else if (this.currentScenario === 'SENSOR_DRIFT_DEGRADED') {
      state = 'DEGRADED';
      decision = 'SCAN';
      confidence = 0.76;
      ors = 61;
      temp = 36.4; // Drifted from nominal
      bmp280Ok = false; // Disagreement flag
      overallHealth = 82;
      anomalyScore = 0.74;
      isAnomaly = true;
      whyFactors = [
        'Multimodal Sensor Fusion: BMP280 temperature disagrees with DHT22 by +8.6°C',
        'Isolation Forest anomaly detector triggered (score 0.74 > threshold 0.50)',
        'System entered DEGRADED state; fallback single-sensor validation active',
        'Observation restricted to secondary calibration targets'
      ];
      featureWeights = [
        { feature: 'Thermal Consistency', weight: -0.74, impact: 'NEGATIVE' as const, description: 'Sensor cross-validation divergence' },
        { feature: 'Isolation Forest', weight: -0.68, impact: 'NEGATIVE' as const, description: 'High out-of-distribution anomaly score' }
      ];
      alerts.push({
        alert_id: `alt-drift-${this.stepCount}`,
        timestamp: nowIso,
        severity: 'WARNING',
        type: 'SENSOR_FUSION_DISAGREEMENT',
        message: 'BMP280 / DHT22 temperature cross-validation failure (>8°C divergence). Running in DEGRADED mode.',
        acknowledged: false,
        source: 'AI_FUSION'
      });
    } else if (this.currentScenario === 'COMMS_LOSS_FAILSAFE') {
      state = 'SAFE';
      decision = 'SAFE';
      confidence = 0.98;
      ors = 15;
      overallHealth = 65;
      this.pan = 90;
      this.tilt = 0;
      cameraOnline = false;
      whyFactors = [
        'Watchdog Safety Trigger: Central backend heartbeat timeout (>30 seconds)',
        'Edge autonomous state machine entered SAFE fail-safe mode',
        'Actuators locked at mechanical home pose (90°, 0°)',
        'Awaiting operator acknowledgment or comms restoration'
      ];
      featureWeights = [
        { feature: 'Comms Heartbeat', weight: -0.98, impact: 'NEGATIVE' as const, description: 'WebSocket/HTTP telemetry pipe timeout' }
      ];
      alerts.push({
        alert_id: `alt-comms-${this.stepCount}`,
        timestamp: nowIso,
        severity: 'CRITICAL',
        type: 'HEARTBEAT_TIMEOUT_SAFE_PARK',
        message: 'Backend comms heartbeat lost for >30s. Edge autonomously engaged SAFE parking.',
        acknowledged: false,
        source: 'COMMS'
      });
    } else if (this.currentScenario === 'RAPID_SOLAR_FLARE_ALERT') {
      state = 'OBSERVE';
      decision = 'OBSERVE';
      confidence = 0.96;
      ors = 94;
      lux = 68000 + Math.sin(this.stepCount * 0.3) * 1500;
      sharpness = 96.0;
      contrast = 98.2;
      whyFactors = [
        'RAPID SOLAR FLARE DETECTED: Optical flux surge around AR3664',
        'Penumbra gradients sharpening; active flare cadence triggered (1 frame/sec)',
        'Observation quality optimal (ORS 94%); SNR peak',
        'Solar tracking precision stable within 0.15°'
      ];
      featureWeights = [
        { feature: 'Flare Radiance', weight: 0.95, impact: 'POSITIVE' as const, description: 'Elevated extreme UV & optical flux' },
        { feature: 'Contrast Index', weight: 0.88, impact: 'POSITIVE' as const, description: 'Sunspot umbra/penumbra gradient peak' }
      ];
      alerts.push({
        alert_id: `alt-flare-${this.stepCount}`,
        timestamp: nowIso,
        severity: 'INFO',
        type: 'SOLAR_FLARE_RAPID_CADENCE',
        message: 'Optical flare signature confirmed around AR3664. Cadence elevated to 1 Hz.',
        acknowledged: false,
        source: 'VISION'
      });
    } else if (this.currentScenario === 'HIGH_WIND_GUST_STOW') {
      state = 'SAFE';
      decision = 'SAFE';
      confidence = 0.95;
      ors = 20;
      pressure = 998.2 + Math.sin(this.stepCount * 0.4) * 6.5; // Turbulent barometric dips
      this.pan = 90;
      this.tilt = 0; // Mechanical storm stow
      overallHealth = 85;
      whyFactors = [
        'Barometric turbulence detected: delta pressure rate > 3 hPa/min',
        'Dual-axis tracker locked into low-drag safety stow (90°, 0°)',
        'Wind shear protection interlock engaged',
        'Observation paused until atmospheric gradient stabilizes'
      ];
      featureWeights = [
        { feature: 'Barometric Gradient', weight: -0.92, impact: 'NEGATIVE' as const, description: 'Rapid pressure oscillation' }
      ];
      alerts.push({
        alert_id: `alt-wind-${this.stepCount}`,
        timestamp: nowIso,
        severity: 'WARNING',
        type: 'HIGH_WIND_SAFETY_STOW',
        message: 'Barometric turbulence exceeds threshold. Tracker moved to storm stow.',
        acknowledged: false,
        source: 'EDGE'
      });
    } else if (this.currentScenario === 'THERMAL_OVERHEAT_THROTTLE') {
      state = 'DEGRADED';
      decision = 'WAIT';
      confidence = 0.82;
      ors = 42;
      temp = 49.6; // Overheat
      overallHealth = 68;
      anomalyScore = 0.65;
      isAnomaly = true;
      whyFactors = [
        'Enclosure thermal monitor warning: 49.6°C exceeds 45.0°C nominal limit',
        'CMOS sensor thermal dark-current noise elevated',
        'Observation cadence throttled to 0.1 Hz to allow heatsink dissipation',
        'Decision engine holds WAIT until internal temperature decreases < 42°C'
      ];
      featureWeights = [
        { feature: 'Thermal Load', weight: -0.85, impact: 'NEGATIVE' as const, description: 'Core ESP32-CAM junction temp elevated' }
      ];
      alerts.push({
        alert_id: `alt-thermal-${this.stepCount}`,
        timestamp: nowIso,
        severity: 'WARNING',
        type: 'THERMAL_OVERHEAT_THROTTLE',
        message: 'Enclosure temperature reached 49.6°C. Imaging duty cycle throttled.',
        acknowledged: false,
        source: 'EDGE'
      });
    } else if (this.currentScenario === 'DUST_SOILING_EVALUATION') {
      state = 'OBSERVE';
      decision = 'SCAN';
      confidence = 0.88;
      ors = 66;
      sharpness = 64.0;
      contrast = 70.2;
      whyFactors = [
        'Aperture soiling index: 28% transmission loss detected vs reference baseline',
        'Optical limb darkening gradient attenuated by surface dust',
        'Autonomous scan scheduled across calibration points to compute dust distribution',
        'Preventative maintenance flag dispatched to operator log'
      ];
      featureWeights = [
        { feature: 'Aperture Transmission', weight: -0.52, impact: 'NEGATIVE' as const, description: 'Uniform particulate attenuation' }
      ];
      alerts.push({
        alert_id: `alt-dust-${this.stepCount}`,
        timestamp: nowIso,
        severity: 'INFO',
        type: 'APERTURE_DUST_EVALUATION',
        message: 'Optical deck dust soiling detected. Autonomous recalibration scan scheduled.',
        acknowledged: false,
        source: 'AI_FUSION'
      });
    } else if (this.currentScenario === 'SOLAR_ECLIPSE_TRACKING') {
      state = 'OBSERVE';
      decision = 'OBSERVE';
      confidence = 0.98;
      ors = 88;
      lux = 18500; // Natural solar eclipse attenuation
      cloudOcclusion = 0.0; // Clear sky
      sharpness = 97.5;
      contrast = 98.0;
      whyFactors = [
        'SOLAR ECLIPSE TRANSIT IN PROGRESS: Lunar limb occulting solar disk',
        'Atmospheric clarity pristine; 0% cloud occlusion',
        'Diffraction-limited optical limb tracking active on lunar boundary',
        'Decision engine sustains OBSERVE mode with exposure compensation'
      ];
      featureWeights = [
        { feature: 'Atmospheric Seeing', weight: 0.92, impact: 'POSITIVE' as const, description: 'Extremely clear coronal seeing conditions' },
        { feature: 'Limb Contrast', weight: 0.94, impact: 'POSITIVE' as const, description: 'Sharp lunar knife-edge profile' }
      ];
      alerts.push({
        alert_id: `alt-eclipse-${this.stepCount}`,
        timestamp: nowIso,
        severity: 'INFO',
        type: 'ECLIPSE_TRANSIT_TRACKING',
        message: 'Lunar limb transit tracking active. Atmospheric seeing 98%.',
        acknowledged: false,
        source: 'VISION'
      });
    }


    const telemetry: SensorTelemetry = {
      device_id: 'esp32-sentry-01',
      timestamp: nowIso,
      uptime_seconds: this.uptimeSeconds,
      temperature: Number(temp.toFixed(1)),
      humidity: Number(humidity.toFixed(1)),
      pressure: Number(pressure.toFixed(1)),
      lux: Math.round(lux),
      rain_raw: Math.round(rainRaw),
      rain_detected: rainDetected,
      pan: Math.round(this.pan),
      tilt: Math.round(this.tilt),
      state,
      health: overallHealth,
      wifi_rssi: -61,
      camera_online: cameraOnline,
      camera_ip: '192.168.1.120',
      sensor_status: {
        dht22: dht22Ok,
        bh1750: bh1750Ok,
        bmp280: bmp280Ok,
        rain: rainOk
      },
      firmware_version: '1.0.0'
    };

    const ors_factors: ORSFactors = {
      solar_elevation: state === 'SUSPEND' || state === 'SAFE' ? 10 : 88,
      atmospheric_seeing: cloudOcclusion > 40 ? 35 : 86,
      cloud_transparency: Math.round(100 - cloudOcclusion),
      sensor_health: overallHealth,
      tracking_stability: state === 'OBSERVE' ? 96 : 40
    };

    const health: ObservatoryHealth = {
      overall: overallHealth,
      edge_hardware: overallHealth,
      optical_vision: cameraOnline ? (cloudOcclusion > 50 ? 55 : 94) : 0,
      network_comms: state === 'SAFE' ? 40 : 98,
      anomaly_score: Number(anomalyScore.toFixed(2)),
      is_anomaly: isAnomaly
    };

    const predictions: Record<'horizon_15m' | 'horizon_30m' | 'horizon_60m', PredictionHorizon> = {
      horizon_15m: {
        horizon_minutes: 15,
        score: Math.max(5, Math.min(99, ors + (decision === 'OBSERVE' ? -2 : -10))),
        trend: decision === 'OBSERVE' ? 'STABLE' : 'SLIGHT_DECLINE',
        confidence_lower: Math.max(0, ors - 8),
        confidence_upper: Math.min(100, ors + 6)
      },
      horizon_30m: {
        horizon_minutes: 30,
        score: Math.max(5, Math.min(99, ors + (decision === 'OBSERVE' ? -5 : -15))),
        trend: decision === 'OBSERVE' ? 'STABLE' : 'DEGRADING',
        confidence_lower: Math.max(0, ors - 14),
        confidence_upper: Math.min(100, ors + 8)
      },
      horizon_60m: {
        horizon_minutes: 60,
        score: Math.max(5, Math.min(99, ors - 12)),
        trend: 'UNCERTAIN',
        confidence_lower: Math.max(0, ors - 22),
        confidence_upper: Math.min(100, ors + 12)
      }
    };

    const xai: XAIExplanation = {
      decision,
      confidence,
      why_factors: whyFactors,
      feature_weights: featureWeights,
      threshold_deltas: [
        { metric: 'Ambient Humidity', current: humidity, threshold: 75.0, unit: '%', ok: humidity < 75 },
        { metric: 'Solar Illuminance', current: lux, threshold: 40000, unit: 'Lux', ok: lux >= 40000 },
        { metric: 'Rain Raw ADC', current: rainRaw, threshold: 2000, unit: 'ADC', ok: rainRaw > 2000 },
        { metric: 'Cloud Occlusion', current: cloudOcclusion, threshold: 25.0, unit: '%', ok: cloudOcclusion < 25 }
      ]
    };

    const vision: SolarVisionMetadata = {
      timestamp: nowIso,
      image_url: '/mock_sun.jpg',
      disk_detected: state !== 'SUSPEND' && state !== 'SAFE' && cloudOcclusion < 80,
      center_x: 320 + Math.sin(this.stepCount * 0.1) * 3,
      center_y: 240 + Math.cos(this.stepCount * 0.1) * 2,
      radius_px: 138,
      limb_darkening_coeff: 0.62,
      sunspots: [
        { id: 'AR3664-A', x: 295, y: 220, area_px: 64, intensity_ratio: 0.68 },
        { id: 'AR3664-B', x: 335, y: 260, area_px: 42, intensity_ratio: 0.74 }
      ],
      cloud_occlusion_percent: cloudOcclusion,
      sharpness_score: sharpness,
      contrast_score: contrast,
      exposure_ms: 12
    };

    return {
      telemetry,
      decision,
      ors_score: ors,
      ors_factors,
      health,
      predictions,
      xai,
      vision,
      alerts
    };
  }

  public executeCommand(command: CommandPayload): CommandResult {
    if (command.command === 'EMERGENCY_STOP' || (command.command === 'SET_STATE' && command.target_state === 'SUSPEND')) {
      this.pan = 90;
      this.tilt = 0;
      this.currentScenario = 'SUDDEN_RAIN_ALARM';
      return {
        command_id: command.command_id,
        status: 'SUCCESS',
        message: 'EMERGENCY STOP EXECUTED: Actuators stowed to safe home (90, 0). State locked to SUSPEND.',
        current_pan: 90,
        current_tilt: 0,
        current_state: 'SUSPEND',
        timestamp: new Date().toISOString()
      };
    }

    if (command.command === 'PARK') {
      this.pan = 90;
      this.tilt = 0;
      return {
        command_id: command.command_id,
        status: 'SUCCESS',
        message: 'Park command executed. Dual-axis tracker stowed to (90, 0).',
        current_pan: 90,
        current_tilt: 0,
        current_state: 'STANDBY',
        timestamp: new Date().toISOString()
      };
    }

    if (command.command === 'SET_SERVO') {
      const newPan = Math.max(0, Math.min(180, command.pan ?? this.pan));
      const newTilt = Math.max(0, Math.min(180, command.tilt ?? this.tilt));
      this.pan = newPan;
      this.tilt = newTilt;
      return {
        command_id: command.command_id,
        status: 'SUCCESS',
        message: `Servos slewed to Pan: ${newPan}°, Tilt: ${newTilt}° at speed ${command.speed ?? 100}%.`,
        current_pan: newPan,
        current_tilt: newTilt,
        current_state: 'OBSERVE',
        timestamp: new Date().toISOString()
      };
    }

    if (command.command === 'OBSERVE') {
      this.currentScenario = 'CLEAR_SKY_OPTIMAL';
      this.pan = 92;
      this.tilt = 51;
      return {
        command_id: command.command_id,
        status: 'SUCCESS',
        message: 'Observation sequence engaged. Solar tracking active.',
        current_pan: 92,
        current_tilt: 51,
        current_state: 'OBSERVE',
        timestamp: new Date().toISOString()
      };
    }

    if (command.command === 'SCAN') {
      return {
        command_id: command.command_id,
        status: 'SUCCESS',
        message: 'Active scanning raster initiated across azimuth grid.',
        current_pan: 90,
        current_tilt: 45,
        current_state: 'SCAN',
        timestamp: new Date().toISOString()
      };
    }

    return {
      command_id: command.command_id,
      status: 'SUCCESS',
      message: `Command ${command.command} executed.`,
      current_pan: Math.round(this.pan),
      current_tilt: Math.round(this.tilt),
      current_state: 'STANDBY',
      timestamp: new Date().toISOString()
    };
  }

  // Generates 30 initial history points for immediate graph population
  public generateInitialHistory(): TelemetryPoint[] {
    const points: TelemetryPoint[] = [];
    const now = Date.now();
    for (let i = 30; i >= 0; i--) {
      const t = new Date(now - i * 60 * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      points.push({
        timestamp: t,
        temperature: Number((26.5 + Math.sin(i * 0.2) * 1.5).toFixed(1)),
        humidity: Number((42.0 + Math.cos(i * 0.15) * 3.5).toFixed(1)),
        pressure: Number((1013.2 + Math.sin(i * 0.05) * 0.4).toFixed(1)),
        lux: Math.round(48000 + Math.sin(i * 0.2) * 4000),
        rain_raw: 3850 + Math.floor(Math.random() * 40),
        pan: Math.round(88 + (30 - i) * 0.3),
        tilt: Math.round(45 + Math.sin(i * 0.1) * 3),
        ors: Math.round(88 + Math.cos(i * 0.1) * 5)
      });
    }
    return points;
  }

  // Generates 20 replay frames for the scrubbable session replay engine
  public generateReplayFrames(): ReplayFrame[] {
    const frames: ReplayFrame[] = [];
    const startMs = Date.now() - 3600 * 1000;
    
    for (let i = 0; i < 20; i++) {
      const frameTime = new Date(startMs + i * 180 * 1000).toISOString();
      const isDip = i >= 8 && i <= 13;
      const isRain = i > 15;

      const state: EdgeSystemState = isRain ? 'SUSPEND' : isDip ? 'WAIT' : 'OBSERVE';
      const decision: AIDecisionState = isRain ? 'SUSPEND' : isDip ? 'WAIT' : 'OBSERVE';
      const ors = isRain ? 12 : isDip ? 44 : 93;

      frames.push({
        timestamp: frameTime,
        telemetry: {
          device_id: 'esp32-sentry-01',
          timestamp: frameTime,
          uptime_seconds: 1000 + i * 180,
          temperature: isDip ? 25.8 : 27.5,
          humidity: isRain ? 92.0 : isDip ? 71.0 : 44.0,
          pressure: 1013.0,
          lux: isRain ? 3200 : isDip ? 15000 : 51000,
          rain_raw: isRain ? 1340 : 3860,
          rain_detected: isRain,
          pan: isRain ? 90 : Math.round(85 + i * 0.8),
          tilt: isRain ? 0 : Math.round(40 + i * 0.5),
          state,
          health: isRain ? 70 : 100,
          wifi_rssi: -62,
          camera_online: true,
          sensor_status: { dht22: true, bh1750: true, bmp280: true, rain: true },
          firmware_version: '1.0.0'
        },
        decision,
        decision_confidence: isRain ? 0.99 : isDip ? 0.88 : 0.95,
        ors_score: ors,
        vision: {
          timestamp: frameTime,
          image_url: '/mock_sun.jpg',
          disk_detected: !isRain && !isDip,
          center_x: 320,
          center_y: 240,
          radius_px: 138,
          limb_darkening_coeff: 0.60,
          sunspots: [{ id: 'AR3664-A', x: 300, y: 230, area_px: 55, intensity_ratio: 0.70 }],
          cloud_occlusion_percent: isRain ? 98 : isDip ? 60 : 0,
          sharpness_score: isRain ? 12 : isDip ? 45 : 91,
          contrast_score: isRain ? 15 : isDip ? 52 : 94,
          exposure_ms: 12
        },
        notes: isRain 
          ? 'Precipitation event triggered auto-stow to home pose.' 
          : isDip 
          ? 'Cloud occlusion transit detected; state paused in WAIT.' 
          : 'Nominal solar disk tracking and active region observation.'
      });
    }
    return frames;
  }

  // Pre-configured mission targets and timelines
  public getMissionData(): { target: MissionTarget; timeline: MissionTimelineItem[] } {
    return {
      target: {
        id: 'TGT-SOL-01',
        name: 'Solar Disk & Active Region AR3664',
        solar_object: 'Sun (Sol)',
        target_azimuth: 142.5,
        target_elevation: 51.2,
        target_pan: 92,
        target_tilt: 51,
        tracking_error_deg: 0.28
      },
      timeline: [
        {
          id: 'MSN-01',
          title: 'System Self-Check & I2C Bus Diagnostics',
          phase: 'CALIBRATION',
          status: 'COMPLETED',
          start_time: '10:00 UTC',
          duration_minutes: 5,
          description: 'Verified DHT22, BMP280, BH1750 and dual-axis servo limit switches.'
        },
        {
          id: 'MSN-02',
          title: 'Solar Slew & Sun Center Acquisition',
          phase: 'SLEW',
          status: 'COMPLETED',
          start_time: '10:05 UTC',
          duration_minutes: 3,
          description: 'Slewed pan/tilt gimbal to calculated solar ephemeris coordinates.'
        },
        {
          id: 'MSN-03',
          title: 'Active High-Cadence Solar Tracking',
          phase: 'TRACKING',
          status: 'ACTIVE',
          start_time: '10:08 UTC',
          duration_minutes: 45,
          description: 'Closed-loop solar disk limb darkening analysis and sunspot photometry.'
        },
        {
          id: 'MSN-04',
          title: 'Atmospheric Seeing & Quality Verification',
          phase: 'VERIFICATION',
          status: 'UPCOMING',
          start_time: '10:53 UTC',
          duration_minutes: 10,
          description: 'Post-cadence image blur gradient and microclimate drift verification.'
        },
        {
          id: 'MSN-05',
          title: 'Mission Stow & Sensor Desiccation',
          phase: 'STOW',
          status: 'UPCOMING',
          start_time: '11:03 UTC',
          duration_minutes: 5,
          description: 'Park gimbal to protected home position (90°, 0°).'
        }
      ]
    };
  }
}

export const observatorySimulator = new ObservatorySimulator();
