"use client";

import {
  Play,
  Download,
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  Timer,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import type { SchedulerStatus } from "@/types/control";

interface ExecutionStatusProps {
  running: boolean;
  collecting: boolean;
  killSwitchActive: boolean;
  lastResult: {
    type: "run" | "collect";
    success: boolean;
    message: string;
    timestamp: string;
  } | null;
  onRun: () => void;
  onCollect: () => void;
  scheduler: SchedulerStatus | null;
  schedulerToggling: boolean;
  onSchedulerToggle: () => void;
}

function formatTime(isoString: string): string {
  return new Date(isoString).toLocaleString("ko-KR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function SchedulerLastRunInfo({ lastRun }: { lastRun: SchedulerStatus["last_run"] }) {
  if (!lastRun) return null;

  const statusLabel =
    lastRun.status === "success"
      ? `성공 (시그널 ${lastRun.total_signals ?? 0}건)`
      : lastRun.status === "skipped"
        ? `스킵 (${lastRun.reason === "kill_switch" ? "킬스위치" : "장외시간"})`
        : `오류: ${lastRun.error ?? "알 수 없음"}`;

  const colorClass =
    lastRun.status === "success"
      ? "text-green-600 dark:text-green-400"
      : lastRun.status === "skipped"
        ? "text-yellow-600 dark:text-yellow-400"
        : "text-red-600 dark:text-red-400";

  return (
    <p className={`text-xs ${colorClass}`}>
      마지막 실행: {formatTime(lastRun.time)} — {statusLabel}
    </p>
  );
}

export function ExecutionStatus({
  running,
  collecting,
  killSwitchActive,
  lastResult,
  onRun,
  onCollect,
  scheduler,
  schedulerToggling,
  onSchedulerToggle,
}: ExecutionStatusProps) {
  const busy = running || collecting;

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">실행 제어</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex flex-wrap gap-3">
          <Button
            onClick={onRun}
            disabled={busy || killSwitchActive}
            className="gap-2"
          >
            {running ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Play className="h-4 w-4" />
            )}
            {running ? "실행 중..." : "전체 사이클 실행"}
          </Button>

          <Button
            variant="secondary"
            onClick={onCollect}
            disabled={busy || killSwitchActive}
            className="gap-2"
          >
            {collecting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Download className="h-4 w-4" />
            )}
            {collecting ? "수집 중..." : "데이터 수집"}
          </Button>
        </div>

        {killSwitchActive && (
          <p className="text-sm text-red-500">
            Kill Switch가 활성화되어 실행이 차단됩니다
          </p>
        )}

        {/* Scheduler controls */}
        <div className="flex flex-col gap-2 rounded-md border p-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Timer className="h-4 w-4 text-muted-foreground" />
              <Label htmlFor="scheduler-toggle" className="text-sm font-medium">
                자동 실행 (스케줄러)
              </Label>
            </div>
            <Switch
              id="scheduler-toggle"
              checked={scheduler?.running ?? false}
              onCheckedChange={onSchedulerToggle}
              disabled={schedulerToggling || killSwitchActive}
            />
          </div>
          {scheduler && (
            <div className="flex flex-col gap-1 text-xs text-muted-foreground">
              {scheduler.running && scheduler.next_run && (
                <p className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  다음 실행: {formatTime(scheduler.next_run)}
                  {scheduler.interval_minutes && ` (${scheduler.interval_minutes}분 간격)`}
                </p>
              )}
              <SchedulerLastRunInfo lastRun={scheduler.last_run} />
            </div>
          )}
        </div>

        {lastResult && (
          <div
            className={`flex items-start gap-2 rounded-md p-3 text-sm ${
              lastResult.success
                ? "bg-green-500/10 text-green-700 dark:text-green-400"
                : "bg-red-500/10 text-red-700 dark:text-red-400"
            }`}
          >
            {lastResult.success ? (
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
            ) : (
              <XCircle className="mt-0.5 h-4 w-4 shrink-0" />
            )}
            <div>
              <p className="font-medium">{lastResult.message}</p>
              <p className="mt-0.5 text-xs opacity-70">
                {new Date(lastResult.timestamp).toLocaleString("ko-KR")}
              </p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
