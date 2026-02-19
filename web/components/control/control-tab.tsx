"use client";

import { Loader2 } from "lucide-react";
import {
  useKillSwitch,
  useBotExecution,
  useScheduler,
  useTradingMode,
  useLogViewer,
} from "@/hooks/use-control";
import { ModeToggle } from "./mode-toggle";
import { KillSwitch } from "./kill-switch";
import { ExecutionStatus } from "./execution-status";
import { LogViewer } from "./log-viewer";
import { KisStatus } from "./kis-status";
import type { TradingMode } from "@/types/control";

interface ControlTabProps {
  onModeChange?: (mode: TradingMode) => void;
}

export function ControlTab({ onModeChange }: ControlTabProps) {
  const killSwitch = useKillSwitch();
  const execution = useBotExecution();
  const scheduler = useScheduler();
  const tradingMode = useTradingMode();
  const { logs, addLog, clearLogs } = useLogViewer(
    execution.running || execution.collecting
  );

  const handleModeChange = async (newMode: TradingMode, confirm?: boolean) => {
    const labels = { simulation: "시뮬레이션", paper: "모의투자", live: "실거래" };
    addLog("INFO", `모드 전환: ${labels[newMode]}...`);
    await tradingMode.switchMode(newMode, confirm);
    onModeChange?.(newMode);
  };

  const handleRun = async () => {
    addLog("INFO", "전체 사이클 실행 시작...");
    await execution.executeRun();
    if (execution.lastResult) {
      addLog(
        execution.lastResult.success ? "INFO" : "ERROR",
        execution.lastResult.message
      );
    } else {
      addLog("INFO", "실행 요청 전송 완료");
    }
  };

  const handleCollect = async () => {
    addLog("INFO", "데이터 수집 시작...");
    await execution.executeCollect();
    if (execution.lastResult) {
      addLog(
        execution.lastResult.success ? "INFO" : "ERROR",
        execution.lastResult.message
      );
    } else {
      addLog("INFO", "수집 요청 전송 완료");
    }
  };

  const handleKillSwitchToggle = async () => {
    const action = killSwitch.active ? "해제" : "활성화";
    addLog("WARN", `Kill Switch ${action} 요청...`);
    await killSwitch.toggle();
    addLog("INFO", `Kill Switch ${action} 완료`);
  };

  const handleSchedulerToggle = async () => {
    const action = scheduler.status?.running ? "중지" : "시작";
    addLog("INFO", `스케줄러 ${action} 요청...`);
    await scheduler.toggle();
    addLog("INFO", `스케줄러 ${action} 완료`);
  };

  if (killSwitch.loading) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <h2 className="text-lg font-semibold">실행 & 제어</h2>
          <KisStatus />
        </div>
        <ModeToggle
          mode={tradingMode.mode}
          switching={tradingMode.switching}
          error={tradingMode.error}
          onModeChange={handleModeChange}
        />
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <KillSwitch
          active={killSwitch.active}
          toggling={killSwitch.toggling}
          onToggle={handleKillSwitchToggle}
        />
        <ExecutionStatus
          running={execution.running}
          collecting={execution.collecting}
          killSwitchActive={killSwitch.active}
          lastResult={execution.lastResult}
          onRun={handleRun}
          onCollect={handleCollect}
          scheduler={scheduler.status}
          schedulerToggling={scheduler.toggling}
          onSchedulerToggle={handleSchedulerToggle}
        />
      </div>

      <LogViewer logs={logs} onClear={clearLogs} />
    </div>
  );
}
