import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { SensorTelemetry, TelemetryPoint } from '../types/telemetry';
import { CommandPayload, CommandResult, CommandVerb } from '../types/command';
import { AIDecisionState, ORSFactors, PredictionHorizon, ObservatoryHealth, SolarVisionMetadata, XAIExplanation } from '../types/intelligence';
import { MissionTarget, MissionTimelineItem, ReplayFrame } from '../types/mission';
import { AnomalyAlert, EventLogEntry } from '../types/alerts';
import { observatorySimulator, SimulationScenarioId, SIMULATION_SCENARIOS } from '../services/simulator';
import { observatoryApi } from '../services/api';
import { observatoryWs, WebSocketStatus } from '../services/websocket';

interface ObservatoryContextType {
  // Mode & Connection
  systemMode: 'DEMO' | 'HARDWARE';
  setSystemMode: (mode: 'DEMO' | 'HARDWARE') => Promise<void>;
  isOnline: boolean;
  isSimulationMode: boolean;
  setSimulationMode: (sim: boolean) => void;
  activeScenario: SimulationScenarioId;
  switchScenario: (scenario: SimulationScenarioId) => void;
  wsStatus: WebSocketStatus;
  
  // Real-time State
  telemetry: SensorTelemetry;
  telemetryHistory: TelemetryPoint[];
  orsScore: number;
  orsFactors: ORSFactors;
  aiDecision: AIDecisionState;
  aiConfidence: number;
  xai: XAIExplanation;
  observatoryHealth: ObservatoryHealth;
  predictions: Record<'horizon_15m' | 'horizon_30m' | 'horizon_60m', PredictionHorizon>;
  vision: SolarVisionMetadata;
  
  // Mission & Targets
  missionTarget: MissionTarget;
  missionTimeline: MissionTimelineItem[];
  
  // Alerts & Events
  alerts: AnomalyAlert[];
  eventLog: EventLogEntry[];
  acknowledgeAlert: (alertId: string) => void;
  clearAlerts: () => void;
  
  // Commands
  sendCommand: (verb: CommandVerb, params?: Partial<CommandPayload>) => Promise<CommandResult>;
  triggerEmergencyStop: () => Promise<CommandResult>;
  
  // Replay Mode
  isReplayActive: boolean;
  setIsReplayActive: (active: boolean) => void;
  replayFrames: ReplayFrame[];
  replayIndex: number;
  setReplayIndex: (index: number) => void;
  isReplayPlaying: boolean;
  setIsReplayPlaying: (playing: boolean) => void;
  replaySpeed: number;
  setReplaySpeed: (speed: number) => void;

  // Camera & Stream
  cameraState: {
    status: 'ONLINE' | 'OFFLINE' | 'DISCOVERING' | 'RECONNECTING' | 'DEGRADED';
    ip: string;
    hostname: string;
    streamUrl: string;
    latencyMs: number;
    discoveryMethod: string;
    isVerified: boolean;
  };
  rediscoverCamera: () => Promise<void>;
  updateCameraUrl: (url: string) => Promise<void>;
}

const ObservatoryContext = createContext<ObservatoryContextType | undefined>(undefined);

export const ObservatoryProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [systemMode, setSystemModeState] = useState<'DEMO' | 'HARDWARE'>('DEMO');
  const [isOnline, setIsOnline] = useState<boolean>(true);
  const [isSimulationMode, setSimulationMode] = useState<boolean>(true);
  const [activeScenario, setActiveScenario] = useState<SimulationScenarioId>('CLEAR_SKY_OPTIMAL');
  const [wsStatus, setWsStatus] = useState<WebSocketStatus>('DISCONNECTED');

  const setSystemMode = useCallback(async (mode: 'DEMO' | 'HARDWARE') => {
    try {
      await observatoryApi.switchSystemMode(mode);
      setSystemModeState(mode);
      if (mode === 'DEMO') {
        setSimulationMode(true);
        setIsOnline(true);
      } else {
        setSimulationMode(false);
        const status = await observatoryApi.getSystemStatus();
        setIsOnline(status.device_connected);
      }
    } catch (e) {
      console.error('Failed to switch system mode:', e);
      setSystemModeState(mode);
      setSimulationMode(mode === 'DEMO');
      setIsOnline(mode === 'DEMO');
    }
  }, []);

  // Camera State & Discovery
  const [cameraState, setCameraState] = useState<{
    status: 'ONLINE' | 'OFFLINE' | 'DISCOVERING' | 'RECONNECTING' | 'DEGRADED';
    ip: string;
    hostname: string;
    streamUrl: string;
    latencyMs: number;
    discoveryMethod: string;
    isVerified: boolean;
  }>({
    status: 'ONLINE',
    ip: '127.0.0.1 (simulated)',
    hostname: 'solar-sentry-cam.local',
    streamUrl: observatoryApi.getCameraStreamUrl(),
    latencyMs: 12,
    discoveryMethod: 'demo',
    isVerified: true,
  });

  const rediscoverCamera = useCallback(async () => {
    setCameraState((prev) => ({ ...prev, status: 'DISCOVERING' }));
    try {
      const res = await observatoryApi.discoverCamera();
      if (res && (res.status === 'ONLINE' || res.ip)) {
        setCameraState({
          status: 'ONLINE',
          ip: res.ip || '',
          hostname: res.hostname || 'solar-sentry-cam.local',
          streamUrl: observatoryApi.getCameraStreamUrl(),
          latencyMs: res.latency_ms || 45,
          discoveryMethod: res.discovery_method || 'mdns',
          isVerified: true,
        });
      } else {
        setCameraState((prev) => ({
          ...prev,
          status: 'OFFLINE',
          isVerified: false,
        }));
      }
    } catch (e) {
      console.warn('Camera rediscovery error:', e);
      setCameraState((prev) => ({ ...prev, status: 'OFFLINE', isVerified: false }));
    }
  }, []);

  const updateCameraUrl = useCallback(async (url: string) => {
    try {
      await observatoryApi.configureCameraUrl(url);
      await rediscoverCamera();
    } catch (e) {
      console.error('Failed to configure camera url:', e);
    }
  }, [rediscoverCamera]);

  // Periodic Camera status sync based on system mode
  useEffect(() => {
    if (systemMode === 'DEMO') {
      setCameraState({
        status: 'ONLINE',
        ip: '127.0.0.1 (simulated)',
        hostname: 'solar-sentry-cam.local',
        streamUrl: observatoryApi.getCameraStreamUrl(),
        latencyMs: 10,
        discoveryMethod: 'demo',
        isVerified: true,
      });
      return;
    }

    const pollCamera = async () => {
      try {
        const data = await observatoryApi.getCameraStatus();
        const reg = data.registry || {};
        const isCamOnline = data.connected || reg.status === 'ONLINE';
        setCameraState({
          status: isCamOnline ? 'ONLINE' : (reg.status === 'DISCOVERING' ? 'DISCOVERING' : 'OFFLINE'),
          ip: data.discovered_ip || reg.ip || '',
          hostname: data.hostname || reg.hostname || 'solar-sentry-cam.local',
          streamUrl: observatoryApi.getCameraStreamUrl(),
          latencyMs: data.latency_ms || (isCamOnline ? 42 : 0),
          discoveryMethod: data.discovery_method || reg.discovery_method || 'mdns',
          isVerified: isCamOnline,
        });
      } catch {
        setCameraState((prev) => ({
          ...prev,
          status: 'OFFLINE',
          isVerified: false,
        }));
      }
    };

    pollCamera();
    const interval = setInterval(pollCamera, 4000);
    return () => clearInterval(interval);
  }, [systemMode]);



  // Initialize initial simulator data
  const initialTick = useRef(observatorySimulator.tick()).current;
  const [telemetry, setTelemetry] = useState<SensorTelemetry>(initialTick.telemetry);
  const [telemetryHistory, setTelemetryHistory] = useState<TelemetryPoint[]>(() => observatorySimulator.generateInitialHistory());
  const [orsScore, setOrsScore] = useState<number>(initialTick.ors_score);
  const [orsFactors, setOrsFactors] = useState<ORSFactors>(initialTick.ors_factors);
  const [aiDecision, setAiDecision] = useState<AIDecisionState>(initialTick.decision);
  const [aiConfidence, setAiConfidence] = useState<number>(initialTick.xai.confidence);
  const [xai, setXai] = useState<XAIExplanation>(initialTick.xai);
  const [observatoryHealth, setObservatoryHealth] = useState<ObservatoryHealth>(initialTick.health);
  const [predictions, setPredictions] = useState(initialTick.predictions);
  const [vision, setVision] = useState<SolarVisionMetadata>(initialTick.vision);

  // Mission
  const initialMission = useRef(observatorySimulator.getMissionData()).current;
  const [missionTarget] = useState<MissionTarget>(initialMission.target);
  const [missionTimeline] = useState<MissionTimelineItem[]>(initialMission.timeline);

  // Alerts & Event Log
  const [alerts, setAlerts] = useState<AnomalyAlert[]>([]);
  const [eventLog, setEventLog] = useState<EventLogEntry[]>([
    {
      id: 'evt-init-1',
      timestamp: new Date(Date.now() - 60000).toLocaleTimeString(),
      level: 'INFO',
      category: 'EDGE',
      message: 'ESP32 DevKit booted successfully. Firmware version 1.0.0.'
    },
    {
      id: 'evt-init-2',
      timestamp: new Date(Date.now() - 45000).toLocaleTimeString(),
      level: 'INFO',
      category: 'EDGE',
      message: 'All sensors initialized on I2C bus (DHT22, BMP280 0x76, BH1750, Rain ADC).'
    },
    {
      id: 'evt-init-3',
      timestamp: new Date(Date.now() - 30000).toLocaleTimeString(),
      level: 'INFO',
      category: 'COGNITIVE',
      message: 'Agent 8 Cognitive Decision Engine connected. Autonomous tracking active.'
    }
  ]);

  // Replay
  const [isReplayActive, setIsReplayActive] = useState<boolean>(false);
  const [replayFrames] = useState<ReplayFrame[]>(() => observatorySimulator.generateReplayFrames());
  const [replayIndex, setReplayIndex] = useState<number>(0);
  const [isReplayPlaying, setIsReplayPlaying] = useState<boolean>(false);
  const [replaySpeed, setReplaySpeed] = useState<number>(1);

  // Switch Simulation Scenario
  const switchScenario = useCallback((scenario: SimulationScenarioId) => {
    setActiveScenario(scenario);
    observatorySimulator.setScenario(scenario);
    const meta = SIMULATION_SCENARIOS.find((s) => s.id === scenario);
    setEventLog((prev) => [
      {
        id: `evt-scenario-${Date.now()}`,
        timestamp: new Date().toLocaleTimeString(),
        level: 'WARN',
        category: 'COGNITIVE',
        message: `Simulation scenario switched to: [${meta?.name || scenario}].`
      },
      ...prev.slice(0, 49)
    ]);
  }, []);

  // Tick generator for Simulation Mode
  useEffect(() => {
    if (!isSimulationMode || isReplayActive) return;

    const interval = setInterval(() => {
      const data = observatorySimulator.tick();
      setTelemetry(data.telemetry);
      setOrsScore(data.ors_score);
      setOrsFactors(data.ors_factors);
      setAiDecision(data.decision);
      setAiConfidence(data.xai.confidence);
      setXai(data.xai);
      setObservatoryHealth(data.health);
      setPredictions(data.predictions);
      setVision(data.vision);

      // Append historical point
      setTelemetryHistory((prev) => {
        const newPoint: TelemetryPoint = {
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
          temperature: data.telemetry.temperature,
          humidity: data.telemetry.humidity,
          pressure: data.telemetry.pressure,
          lux: data.telemetry.lux,
          rain_raw: data.telemetry.rain_raw,
          pan: data.telemetry.pan,
          tilt: data.telemetry.tilt,
          ors: data.ors_score
        };
        const next = [...prev.slice(-40), newPoint];
        return next;
      });

      // Append alerts if present
      if (data.alerts && data.alerts.length > 0) {
        setAlerts((prev) => {
          const existingIds = new Set(prev.map((a) => a.type));
          const newAlerts = data.alerts.filter((a) => !existingIds.has(a.type));
          return [...newAlerts, ...prev].slice(0, 10);
        });
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [isSimulationMode, isReplayActive]);

  // Live WebSocket Integration when NOT in simulation mode
  useEffect(() => {
    if (isSimulationMode) {
      observatoryWs.disconnect();
      setWsStatus('DISCONNECTED');
      return;
    }

    observatoryWs.connect();
    const unsubStatus = observatoryWs.onStatusChange(setWsStatus);

    const unsubMsg = observatoryWs.onMessage((channel, payload) => {
      if (channel === 'telemetry') {
        setTelemetry(payload);
        if (payload.state && payload.state !== 'OFFLINE') {
          setIsOnline(true);
        } else if (payload.state === 'OFFLINE') {
          setIsOnline(false);
        }

        // In HARDWARE mode, also stream live points to history charts
        if (payload.temperature !== undefined) {
          setTelemetryHistory((prev) => {
            const newPoint: TelemetryPoint = {
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
              temperature: payload.temperature,
              humidity: payload.humidity,
              pressure: payload.pressure,
              lux: payload.lux,
              rain_raw: payload.rain_raw,
              pan: payload.pan,
              tilt: payload.tilt,
              ors: orsScore
            };
            return [...prev.slice(-40), newPoint];
          });
        }
      } else if (channel === 'ai_state') {
        if (payload.decision) setAiDecision(payload.decision);
        if (payload.confidence !== undefined) setAiConfidence(payload.confidence);
        if (payload.ors_score !== undefined) setOrsScore(payload.ors_score);
        if (payload.ors_factors) setOrsFactors(payload.ors_factors);
        if (payload.predictions) setPredictions(payload.predictions);
        if (payload.health_breakdown) setObservatoryHealth(payload.health_breakdown);
        if (payload.reasoning_trace) {
          setXai((prev) => ({
            ...prev,
            decision: payload.decision || prev.decision,
            confidence: payload.confidence ?? prev.confidence,
            why_factors: payload.reasoning_trace
          }));
        }
      } else if (channel === 'vision') {
        setVision(payload);
      } else if (channel === 'alerts') {
        setAlerts((prev) => [payload, ...prev.slice(0, 9)]);
      }
    });

    return () => {
      unsubStatus();
      unsubMsg();
      observatoryWs.disconnect();
    };
  }, [isSimulationMode]);

  // Replay playback ticker
  useEffect(() => {
    if (!isReplayActive || !isReplayPlaying) return;

    const intervalTime = Math.max(100, 1000 / replaySpeed);
    const timer = setInterval(() => {
      setReplayIndex((curr) => {
        if (curr >= replayFrames.length - 1) {
          setIsReplayPlaying(false);
          return curr;
        }
        return curr + 1;
      });
    }, intervalTime);

    return () => clearInterval(timer);
  }, [isReplayActive, isReplayPlaying, replaySpeed, replayFrames.length]);

  // Sync replay frame when in replay mode
  useEffect(() => {
    if (!isReplayActive || !replayFrames[replayIndex]) return;

    const frame = replayFrames[replayIndex];
    setTelemetry(frame.telemetry);
    setAiDecision(frame.decision);
    setAiConfidence(frame.decision_confidence);
    setOrsScore(frame.ors_score);
    setVision(frame.vision);
  }, [isReplayActive, replayIndex, replayFrames]);

  // Alert Management
  const acknowledgeAlert = useCallback((alertId: string) => {
    setAlerts((prev) => prev.filter((a) => a.alert_id !== alertId));
    if (!isSimulationMode) {
      observatoryApi.acknowledgeAlert(alertId).catch(console.error);
    }
  }, [isSimulationMode]);

  const clearAlerts = useCallback(() => {
    setAlerts([]);
  }, []);

  // Dispatch Command
  const sendCommand = useCallback(async (verb: CommandVerb, params?: Partial<CommandPayload>): Promise<CommandResult> => {
    const cmd: CommandPayload = {
      command_id: `cmd-${Date.now()}`,
      command: verb,
      ...params,
      timestamp: new Date().toISOString()
    };

    setEventLog((prev) => [
      {
        id: `evt-cmd-${Date.now()}`,
        timestamp: new Date().toLocaleTimeString(),
        level: 'INFO',
        category: 'ACTUATOR',
        message: `Dispatched command [${verb}] (ID: ${cmd.command_id}).`
      },
      ...prev.slice(0, 49)
    ]);

    if (isSimulationMode) {
      const result = observatorySimulator.executeCommand(cmd);
      setTelemetry((prev) => ({
        ...prev,
        pan: result.current_pan,
        tilt: result.current_tilt,
        state: result.current_state
      }));
      return result;
    } else {
      return await observatoryApi.dispatchCommand(cmd);
    }
  }, [isSimulationMode]);

  // Trigger Emergency Stop
  const triggerEmergencyStop = useCallback(async (): Promise<CommandResult> => {
    setAlerts((prev) => [
      {
        alert_id: `estop-${Date.now()}`,
        timestamp: new Date().toISOString(),
        severity: 'CRITICAL',
        type: 'MANUAL_EMERGENCY_STOP',
        message: 'OPERATOR MANUAL EMERGENCY STOP ENGAGED. Actuators stowing to home (90, 0).',
        acknowledged: false,
        source: 'EDGE'
      },
      ...prev
    ]);

    return await sendCommand('EMERGENCY_STOP');
  }, [sendCommand]);

  return (
    <ObservatoryContext.Provider
      value={{
        systemMode,
        setSystemMode,
        isOnline,
        isSimulationMode,
        setSimulationMode,
        activeScenario,
        switchScenario,
        wsStatus,
        telemetry,
        telemetryHistory,
        orsScore,
        orsFactors,
        aiDecision,
        aiConfidence,
        xai,
        observatoryHealth,
        predictions,
        vision,
        missionTarget,
        missionTimeline,
        alerts,
        eventLog,
        acknowledgeAlert,
        clearAlerts,
        sendCommand,
        triggerEmergencyStop,
        isReplayActive,
        setIsReplayActive,
        replayFrames,
        replayIndex,
        setReplayIndex,
        isReplayPlaying,
        setIsReplayPlaying,
        replaySpeed,
        setReplaySpeed,
        cameraState,
        rediscoverCamera,
        updateCameraUrl,
      }}
    >
      {children}
    </ObservatoryContext.Provider>
  );
};

export const useObservatory = (): ObservatoryContextType => {
  const context = useContext(ObservatoryContext);
  if (!context) {
    throw new Error('useObservatory must be used within an ObservatoryProvider');
  }
  return context;
};
