"use client";

import { useState, useCallback } from "react";
import { Loader2, Play, Eye } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useApi } from "@/hooks/use-api";
import { getSignals } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import { formatKRW, formatNumber } from "@/lib/formatters";
import type { PaperSignal } from "@/types/paper";
import type { ApiResponse } from "@/types/common";

interface SignalPreviewProps {
  onExecute: (signalIndex?: number) => void;
  executing: boolean;
}

export function SignalPreview({ onExecute, executing }: SignalPreviewProps) {
  const fetcher = useCallback(
    () => getSignals() as Promise<ApiResponse<PaperSignal[]>>,
    []
  );
  const { data: signals, loading, refetch } = useApi<PaperSignal[]>(fetcher);

  if (loading && !signals) {
    return (
      <div className="flex h-32 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!signals || signals.length === 0) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed py-8">
        <p className="text-sm text-muted-foreground">현재 시그널이 없습니다</p>
        <Button variant="outline" size="sm" onClick={refetch}>
          <Eye className="mr-2 h-4 w-4" />
          시그널 새로고침
        </Button>
      </div>
    );
  }

  // 전략별 그룹핑
  const grouped: Record<string, PaperSignal[]> = {};
  for (const s of signals) {
    (grouped[s.strategy] ??= []).push(s);
  }

  return (
    <div className="flex flex-col gap-4">
      {Object.entries(grouped).map(([strategy, sigs]) => (
        <Card key={strategy} className="gap-0 py-4">
          <CardContent className="flex flex-col gap-3">
            <div className="flex items-center gap-2">
              <Badge variant="outline">{strategy}</Badge>
              <span className="text-xs text-muted-foreground">
                {sigs.length}건
              </span>
            </div>
            {sigs.map((s, i) => (
              <div
                key={`${s.code}-${i}`}
                className="flex items-center justify-between rounded-md border px-3 py-2"
              >
                <div className="flex flex-col gap-0.5">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm font-medium">
                      {s.code}
                    </span>
                    <Badge
                      variant={s.signal === "BUY" ? "default" : "destructive"}
                      className={cn(
                        s.signal === "BUY" && "bg-success text-success-foreground"
                      )}
                    >
                      {s.signal}
                    </Badge>
                    <Badge variant="outline">{s.market}</Badge>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {s.reason}
                  </span>
                </div>
                <div className="text-right text-sm">
                  <div className="font-mono">{formatNumber(s.quantity)}주</div>
                  <div className="text-xs text-muted-foreground">
                    {s.market === "KR" ? formatKRW(s.price) : `$${s.price}`}
                  </div>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      ))}

      <div className="flex gap-2">
        <Button onClick={() => onExecute()} disabled={executing}>
          {executing ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Play className="mr-2 h-4 w-4" />
          )}
          전체 모의 실행
        </Button>
        <Button variant="outline" onClick={refetch}>
          <Eye className="mr-2 h-4 w-4" />
          시그널 새로고침
        </Button>
      </div>
    </div>
  );
}
