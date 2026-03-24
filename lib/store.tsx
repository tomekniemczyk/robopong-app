"use client";

import { createContext, useContext, useState, useCallback, type ReactNode } from "react";
import type {
  TabType,
  Language,
  ConnectionStatus,
  UserRole,
  CalibrationState,
  LogEntry,
  ServerLogEntry,
  Session,
  Preset,
} from "./types";
import { t as translate } from "./i18n";

interface AppState {
  // Connection
  connectionStatus: ConnectionStatus;
  robotName: string;
  transport: "ble" | "usb" | null;
  lastAddr: string | null;
  firmware: string | null;
  simulationMode: boolean;

  // User
  userRole: UserRole;
  sessionId: string;
  sessions: Session[];

  // Navigation
  activeTab: TabType;
  language: Language;

  // Calibration
  calibration: CalibrationState;
  presets: Preset[];
  selectedPreset: number | null;
  hasUnsavedChanges: boolean;

  // Logs
  robotLogs: LogEntry[];
  serverLogs: ServerLogEntry[];

  // Drill state
  activeDrill: {
    name: string;
    currentBall: number;
    totalBalls: number;
    isPaused: boolean;
    currentParams: { top: number; bot: number; osc: number; height: number; rot: number };
  } | null;

  // Training state
  activeTraining: {
    name: string;
    currentStep: number;
    totalSteps: number;
    stepName: string;
    currentBall: number;
    totalBalls: number;
    phase: "COUNTDOWN" | "DRILLING" | "PAUSE" | "EXERCISE" | "DONE";
    timeRemaining: number;
    isPaused: boolean;
  } | null;
}

interface AppActions {
  setActiveTab: (tab: TabType) => void;
  setLanguage: (lang: Language) => void;
  setConnectionStatus: (status: ConnectionStatus) => void;
  setSimulationMode: (enabled: boolean) => void;
  setRobotName: (name: string) => void;
  setCalibration: (cal: Partial<CalibrationState>) => void;
  resetCalibration: () => void;
  setSelectedPreset: (id: number | null) => void;
  addRobotLog: (entry: LogEntry) => void;
  clearRobotLogs: () => void;
  addServerLog: (entry: ServerLogEntry) => void;
  clearServerLogs: () => void;
  setActiveDrill: (drill: AppState["activeDrill"]) => void;
  setActiveTraining: (training: AppState["activeTraining"]) => void;
  t: (key: string) => string;
}

const defaultCalibration: CalibrationState = {
  oscillation: 150,
  height: 150,
  rotation: 150,
  topSpeed: 80,
  bottomSpeed: 0,
  waitMs: 2000,
};

const initialState: AppState = {
  connectionStatus: "disconnected",
  robotName: "Robopong 3050XL",
  transport: null,
  lastAddr: null,
  firmware: null,
  simulationMode: false,
  userRole: "controller",
  sessionId: "abc123",
  sessions: [],
  activeTab: "connect",
  language: "en",
  calibration: defaultCalibration,
  presets: [
    { id: 1, name: "Default", is_default: true, ...defaultCalibration },
    { id: 2, name: "Topspin Fast", is_default: false, oscillation: 160, height: 180, rotation: 150, topSpeed: 200, bottomSpeed: -50, waitMs: 1500 },
    { id: 3, name: "Backspin Slow", is_default: false, oscillation: 140, height: 120, rotation: 150, topSpeed: -30, bottomSpeed: 100, waitMs: 2500 },
  ],
  selectedPreset: 1,
  hasUnsavedChanges: false,
  robotLogs: [],
  serverLogs: [],
  activeDrill: null,
  activeTraining: null,
};

const AppContext = createContext<(AppState & AppActions) | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AppState>(initialState);

  const setActiveTab = useCallback((tab: TabType) => {
    setState((s) => ({ ...s, activeTab: tab }));
  }, []);

  const setLanguage = useCallback((lang: Language) => {
    setState((s) => ({ ...s, language: lang }));
  }, []);

  const setConnectionStatus = useCallback((status: ConnectionStatus) => {
    setState((s) => ({ ...s, connectionStatus: status }));
  }, []);

  const setSimulationMode = useCallback((enabled: boolean) => {
    setState((s) => ({
      ...s,
      simulationMode: enabled,
      connectionStatus: enabled ? "simulation" : "disconnected",
    }));
  }, []);

  const setRobotName = useCallback((name: string) => {
    setState((s) => ({ ...s, robotName: name }));
  }, []);

  const setCalibration = useCallback((cal: Partial<CalibrationState>) => {
    setState((s) => ({
      ...s,
      calibration: { ...s.calibration, ...cal },
      hasUnsavedChanges: true,
    }));
  }, []);

  const resetCalibration = useCallback(() => {
    setState((s) => ({
      ...s,
      calibration: defaultCalibration,
      hasUnsavedChanges: false,
    }));
  }, []);

  const setSelectedPreset = useCallback((id: number | null) => {
    setState((s) => {
      if (id === null) return { ...s, selectedPreset: null };
      const preset = s.presets.find((p) => p.id === id);
      if (!preset) return s;
      return {
        ...s,
        selectedPreset: id,
        calibration: {
          oscillation: preset.oscillation,
          height: preset.height,
          rotation: preset.rotation,
          topSpeed: preset.top_speed,
          bottomSpeed: preset.bot_speed,
          waitMs: preset.wait_ms,
        },
        hasUnsavedChanges: false,
      };
    });
  }, []);

  const addRobotLog = useCallback((entry: LogEntry) => {
    setState((s) => ({
      ...s,
      robotLogs: [...s.robotLogs.slice(-499), entry],
    }));
  }, []);

  const clearRobotLogs = useCallback(() => {
    setState((s) => ({ ...s, robotLogs: [] }));
  }, []);

  const addServerLog = useCallback((entry: ServerLogEntry) => {
    setState((s) => ({
      ...s,
      serverLogs: [...s.serverLogs.slice(-499), entry],
    }));
  }, []);

  const clearServerLogs = useCallback(() => {
    setState((s) => ({ ...s, serverLogs: [] }));
  }, []);

  const setActiveDrill = useCallback((drill: AppState["activeDrill"]) => {
    setState((s) => ({ ...s, activeDrill: drill }));
  }, []);

  const setActiveTraining = useCallback((training: AppState["activeTraining"]) => {
    setState((s) => ({ ...s, activeTraining: training }));
  }, []);

  const t = useCallback(
    (key: string) => translate(key, state.language),
    [state.language]
  );

  const value: AppState & AppActions = {
    ...state,
    setActiveTab,
    setLanguage,
    setConnectionStatus,
    setSimulationMode,
    setRobotName,
    setCalibration,
    resetCalibration,
    setSelectedPreset,
    addRobotLog,
    clearRobotLogs,
    addServerLog,
    clearServerLogs,
    setActiveDrill,
    setActiveTraining,
    t,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error("useApp must be used within AppProvider");
  }
  return context;
}
