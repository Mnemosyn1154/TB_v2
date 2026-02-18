"use client";

import { useState, useCallback } from "react";
import { useApi } from "./use-api";
import { useInterval } from "./use-interval";
import {
  getKillSwitch,
  toggleKillSwitch,
  getBotStatus,
  runBot,
  collectData,
} from "@/lib/api-client";
import type { KillSwitchStatus, BotStatus, TradingMode, LogEntry } from "@/types/control";
import type { ApiResponse } from "@/types/common";

export function useKillSwitch() {
  const {
    data,
    error,
    loading,
    refetch,
  } = useApi<KillSwitchStatus>(getKillSwitch as () => Promise<ApiResponse<KillSwitchStatus>>);
  const [toggling, setToggling] = useState(false);

  const toggle = useCallback(async () => {
    if (!data) return;
    setToggling(true);
    try {
      const action = data.kill_switch ? "deactivate" : "activate";
      await toggleKillSwitch(action);
      await refetch();
    } finally {
      setToggling(false);
    }
  }, [data, refetch]);

  return {
    active: data?.kill_switch ?? false,
    error,
    loading,
    toggling,
    toggle,
    refetch,
  };
}

export function useBotExecution() {
  const [running, setRunning] = useState(false);
  const [collecting, setCollecting] = useState(false);
  const [lastResult, setLastResult] = useState<{
    type: "run" | "collect";
    success: boolean;
    message: string;
    timestamp: string;
  } | null>(null);

  const executeRun = useCallback(async () => {
    setRunning(true);
    setLastResult(null);
    try {
      const res = await runBot();
      setLastResult({
        type: "run",
        success: !res.error,
        message: res.error ?? "전략 실행 완료",
        timestamp: new Date().toISOString(),
      });
    } catch (e) {
      setLastResult({
        type: "run",
        success: false,
        message: e instanceof Error ? e.message : "실행 실패",
        timestamp: new Date().toISOString(),
      });
    } finally {
      setRunning(false);
    }
  }, []);

  const executeCollect = useCallback(async () => {
    setCollecting(true);
    setLastResult(null);
    try {
      const res = await collectData();
      setLastResult({
        type: "collect",
        success: !res.error,
        message: res.error ?? "데이터 수집 완료",
        timestamp: new Date().toISOString(),
      });
    } catch (e) {
      setLastResult({
        type: "collect",
        success: false,
        message: e instanceof Error ? e.message : "수집 실패",
        timestamp: new Date().toISOString(),
      });
    } finally {
      setCollecting(false);
    }
  }, []);

  return {
    running,
    collecting,
    lastResult,
    executeRun,
    executeCollect,
  };
}

export function useTradingMode() {
  const [mode, setMode] = useState<TradingMode>("paper");

  const switchMode = useCallback((newMode: TradingMode) => {
    setMode(newMode);
  }, []);

  return { mode, switchMode };
}

export function useLogViewer(active: boolean) {
  const [logs, setLogs] = useState<LogEntry[]>([]);

  const addLog = useCallback((level: LogEntry["level"], message: string) => {
    setLogs((prev) => [
      ...prev,
      {
        timestamp: new Date().toISOString(),
        level,
        message,
      },
    ]);
  }, []);

  const clearLogs = useCallback(() => {
    setLogs([]);
  }, []);

  // Poll for status updates when active
  useInterval(
    () => {
      // In a real implementation, this would poll /api/bot/status
      // For now, logs are added locally when actions are triggered
    },
    active ? 10_000 : null
  );

  return { logs, addLog, clearLogs };
}
