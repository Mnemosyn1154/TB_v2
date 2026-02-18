"use client";

import { Loader2 } from "lucide-react";
import {
  useKillSwitch,
  useBotExecution,
  useTradingMode,
  useLogViewer,
} from "@/hooks/use-control";
import { ModeToggle } from "./mode-toggle";
import { KillSwitch } from "./kill-switch";
import { ExecutionStatus } from "./execution-status";
import { LogViewer } from "./log-viewer";
import type { TradingMode } from "@/types/control";

interface ControlTabProps {
  onModeChange?: (mode: TradingMode) => void;
}

export function ControlTab({ onModeChange }: ControlTabProps) {
  const killSwitch = useKillSwitch();
  const execution = useBotExecution();
  const { mode, switchMode } = useTradingMode();
  const { logs, addLog, clearLogs } = useLogViewer(
    execution.running || execution.collecting
  );

  const handleModeChange = (newMode: TradingMode) => {
    switchMode(newMode);
    onModeChange?.(newMode);
    addLog("INFO", `모드 전환: ${newMode === "live" ? "실거래" : "모의투자"}`);
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
        <h2 className="text-lg font-semibold">실행 & 제어</h2>
        <ModeToggle mode={mode} onModeChange={handleModeChange} />
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
        />
      </div>

      <LogViewer logs={logs} onClear={clearLogs} />
    </div>
  );
}
