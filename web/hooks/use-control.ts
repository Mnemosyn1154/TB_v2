"use client";

import { useState, useCallback } from "react";
import { useApi } from "./use-api";
import { useInterval } from "./use-interval";
import {
  getKillSwitch,
  toggleKillSwitch,
  getBotStatus,
  toggleScheduler,
  runBot,
  collectData,
  invalidateCache,
  getTradingMode,
  setTradingMode,
} from "@/lib/api-client";
import type {
  KillSwitchStatus,
  BotStatus,
  TradingMode,
  LogEntry,
  FullBotStatus,
  SchedulerStatus,
} from "@/types/control";
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
      const d = res.data as Record<string, unknown> | null;
      const totalSignals = (d?.total_signals as number) ?? 0;
      const simMode = d?.simulation_mode ? "[시뮬레이션] " : "";
      const summary = totalSignals > 0
        ? `${simMode}전략 실행 완료 — 시그널 ${totalSignals}건`
        : `${simMode}전략 실행 완료 — 시그널 없음`;
      setLastResult({
        type: "run",
        success: !res.error,
        message: res.error ?? summary,
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
      // 포트폴리오/벤치마크 캐시 무효화 — 탭 전환 시 최신 데이터 표시
      invalidateCache("/portfolio");
      invalidateCache("/benchmark");
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

export function useScheduler() {
  const [status, setStatus] = useState<SchedulerStatus | null>(null);
  const [toggling, setToggling] = useState(false);

  const fetchStatus = useCallback(async () => {
    try {
      const res = (await getBotStatus()) as ApiResponse<FullBotStatus>;
      if (res.data?.scheduler) {
        setStatus(res.data.scheduler);
      }
    } catch {
      // silently fail
    }
  }, []);

  // Poll every 30s
  useInterval(fetchStatus, 30_000);

  const toggle = useCallback(async () => {
    if (!status) return;
    setToggling(true);
    try {
      const action = status.running ? "stop" : "start";
      const res = (await toggleScheduler(action)) as ApiResponse<SchedulerStatus>;
      if (res.data) {
        setStatus(res.data);
      } else {
        await fetchStatus();
      }
    } finally {
      setToggling(false);
    }
  }, [status, fetchStatus]);

  return {
    status,
    toggling,
    toggle,
    refetch: fetchStatus,
  };
}

export function useTradingMode() {
  const [mode, setMode] = useState<TradingMode>("simulation");
  const [switching, setSwitching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch current mode on mount
  const fetchMode = useCallback(async () => {
    try {
      const res = (await getTradingMode()) as ApiResponse<{ mode: TradingMode }>;
      if (res.data?.mode) {
        setMode(res.data.mode);
      }
    } catch {
      // silently fail
    }
  }, []);

  useInterval(fetchMode, 30_000);

  const switchMode = useCallback(async (newMode: TradingMode, confirm = false) => {
    setSwitching(true);
    setError(null);
    try {
      const res = (await setTradingMode(newMode, confirm)) as ApiResponse<{ mode: TradingMode }>;
      if (res.error) {
        setError(res.error);
      } else if (res.data?.mode) {
        setMode(res.data.mode);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "모드 전환 실패");
    } finally {
      setSwitching(false);
    }
  }, []);

  return { mode, switching, error, switchMode, refetch: fetchMode };
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
