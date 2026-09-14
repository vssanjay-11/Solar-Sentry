import { EdgeSystemState } from './telemetry';

export type CommandVerb =
  | 'OBSERVE'
  | 'PARK'
  | 'SCAN'
  | 'SET_SERVO'
  | 'SET_STATE'
  | 'REBOOT'
  | 'CALIBRATE'
  | 'EMERGENCY_STOP';

export interface CommandPayload {
  command_id: string;
  command: CommandVerb;
  pan?: number;
  tilt?: number;
  speed?: number; // 1-100 default 100
  target_state?: EdgeSystemState;
  timestamp?: string;
}

export type CommandOutcomeStatus =
  | 'SUCCESS'
  | 'REJECTED_SAFETY'
  | 'INVALID_PARAMS'
  | 'EXECUTION_ERROR';

export interface CommandResult {
  command_id: string;
  status: CommandOutcomeStatus;
  message?: string;
  current_pan: number;
  current_tilt: number;
  current_state: EdgeSystemState;
  timestamp?: string;
}
