"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Plus, Square } from "lucide-react";
import { formatDate } from "@/lib/formatters";
import type { PaperSession } from "@/types/paper";

interface PaperSessionProps {
  active: PaperSession | null;
  sessions: PaperSession[];
  onCreateSession: () => void;
  onStopSession: (id: string) => void;
  creating: boolean;
}

export function PaperSessionPanel({
  active,
  sessions,
  onCreateSession,
  onStopSession,
  creating,
}: PaperSessionProps) {
  return (
    <div className="flex flex-col gap-4">
      {/* 활성 세션 */}
      {active ? (
        <Card className="gap-0 border-success/30 py-4">
          <CardContent className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Badge className="bg-success text-success-foreground">
                  활성
                </Badge>
                <span className="font-mono text-sm">{active.session_id}</span>
              </div>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => onStopSession(active.session_id)}
              >
                <Square className="mr-1.5 h-3.5 w-3.5" />
                세션 종료
              </Button>
            </div>
            <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
              <span>시작: {formatDate(active.start_date)}</span>
              <span>
                전략: {active.strategy_names?.join(", ") ?? "없음"}
              </span>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed py-6">
          <p className="text-sm text-muted-foreground">활성 세션이 없습니다</p>
          <Button onClick={onCreateSession} disabled={creating}>
            <Plus className="mr-2 h-4 w-4" />
            새 세션 시작
          </Button>
        </div>
      )}

      {/* 과거 세션 목록 */}
      {sessions.length > 0 && (
        <div>
          <h4 className="mb-2 text-sm font-medium text-muted-foreground">
            세션 히스토리
          </h4>
          <div className="flex flex-col gap-2">
            {sessions
              .filter((s) => s.status === "stopped")
              .slice(0, 5)
              .map((s) => (
                <div
                  key={s.session_id}
                  className="flex items-center justify-between rounded-md border px-3 py-2 text-sm"
                >
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary">종료</Badge>
                    <span className="font-mono text-xs">{s.session_id}</span>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {formatDate(s.start_date)}
                    {s.end_date ? ` ~ ${formatDate(s.end_date)}` : ""}
                  </span>
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}
