"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ChevronDown, ChevronUp, Terminal } from "lucide-react";
import { cn } from "@/lib/utils";

interface BacktestLogsProps {
  logs: string[];
}

export function BacktestLogs({ logs }: BacktestLogsProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-sm font-semibold">
            <Terminal className="size-4" />
            실행 로그 ({logs.length}줄)
          </CardTitle>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? (
              <ChevronUp className="size-4" />
            ) : (
              <ChevronDown className="size-4" />
            )}
          </Button>
        </div>
      </CardHeader>
      {expanded && (
        <CardContent>
          <div className="max-h-[300px] overflow-y-auto rounded-md bg-muted p-3 font-mono text-xs leading-relaxed">
            {logs.map((line, i) => (
              <div
                key={i}
                className={cn(
                  "whitespace-pre-wrap",
                  line.startsWith("WARNING") && "text-yellow-600 dark:text-yellow-400",
                  line.startsWith("ERROR") && "text-destructive"
                )}
              >
                {line}
              </div>
            ))}
          </div>
        </CardContent>
      )}
    </Card>
  );
}
