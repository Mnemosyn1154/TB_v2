"use client";

import { Play, Download, Loader2, CheckCircle2, XCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

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
}

export function ExecutionStatus({
  running,
  collecting,
  killSwitchActive,
  lastResult,
  onRun,
  onCollect,
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
