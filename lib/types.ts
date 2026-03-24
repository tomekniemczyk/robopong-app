export interface Ball {
  top_speed: number;
  bot_speed: number;
  oscillation: number;
  height: number;
  rotation: number;
  wait_ms: number;
}

export interface Drill {
  id?: number;
  name: string;
  description: string;
  youtube_id?: string;
  delay_s?: number;
  balls: Ball[];
  repeat: number;
  sort_order: number;
  readonly?: boolean;
}

export interface DrillFolder {
  id?: number;
  name: string;
  description: string;
  sort_order: number;
  readonly?: boolean;
  drills: Drill[];
}

export interface TrainingStep {
  drill_id: number;
  drill_name: string;
  count: number;
  percent: number;
  pause_after_sec: number;
}

export interface Training {
  id?: number;
  name: string;
  description: string;
  countdown_sec: number;
  steps: TrainingStep[];
}

export interface Exercise {
  name: string;
  description: string;
  duration_sec: number;
}

export interface ExerciseCategory {
  name: string;
  icon: string;
  exercises: Exercise[];
}

export interface Preset {
  id?: number;
  name: string;
  is_default: boolean;
  top_speed: number;
  bot_speed: number;
  oscillation: number;
  height: number;
  rotation: number;
  wait_ms: number;
}

export interface LogEntry {
  timestamp: string;
  direction: 'sent' | 'received' | 'status';
  message: string;
}

export interface ServerLogEntry {
  timestamp: string;
  level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR';
  logger: string;
  message: string;
}

export interface Session {
  id: string;
  role: 'controller' | 'observer' | 'pending';
  ip?: string;
  ua?: string;
  since: string;
}

export interface BLEDevice {
  name: string;
  address: string;
  rssi?: number;
}

export interface USBPort {
  port: string;
  description?: string;
}

export type ConnectionStatus = 'disconnected' | 'connected' | 'simulation';
export type UserRole = 'controller' | 'observer' | 'pending';
export type TabType = 'connect' | 'calibration' | 'drills' | 'training' | 'exercises' | 'camera' | 'logs';
export type Language = 'pl' | 'en' | 'de' | 'fr' | 'zh';

export interface CalibrationState {
  oscillation: number;
  height: number;
  rotation: number;
  topSpeed: number;
  bottomSpeed: number;
  waitMs: number;
}
