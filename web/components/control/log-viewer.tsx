"use client";

import { useRef, useEffect } from "react";
import { Trash2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { LogEntry } from "@/types/control";

const LEVEL_STYLES: Record<LogEntry["level"], string> = {
  INFO: "text-muted-foreground",
  WARN: "text-yellow-600 dark:text-yellow-400",
  ERROR: "text-red-600 dark:text-red-400",
};

interface LogViewerProps {
  logs: LogEntry[];
  onClear: () => void;
}

export function LogViewer({ logs, onClear }: LogViewerProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs.length]);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <CardTitle className="text-base">실행 로그</CardTitle>
        <Button
          variant="ghost"
          size="sm"
          onClick={onClear}
          disabled={logs.length === 0}
          className="gap-1.5 text-xs"
        >
          <Trash2 className="h-3.5 w-3.5" />
          로그 지우기
        </Button>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-64 w-full rounded-md border bg-muted/30 p-3">
          {logs.length === 0 ? (
            <p className="text-center text-sm text-muted-foreground">
              실행 로그가 없습니다
            </p>
          ) : (
            <div className="space-y-1 font-mono text-xs">
              {logs.map((log, i) => (
                <div key={i} className="flex gap-2">
                  <span className="shrink-0 text-muted-foreground">
                    {new Date(log.timestamp).toLocaleTimeString("ko-KR")}
                  </span>
                  <span
                    className={`shrink-0 w-12 font-semibold ${LEVEL_STYLES[log.level]}`}
                  >
                    [{log.level}]
                  </span>
                  <span className={LEVEL_STYLES[log.level]}>{log.message}</span>
                </div>
              ))}
              <div ref={bottomRef} />
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
