"use client";

import { Clock } from "lucide-react";

interface LastUpdatedProps {
  timestamp: Date | null;
}

export function LastUpdated({ timestamp }: LastUpdatedProps) {
  if (!timestamp) return null;

  const formatted = timestamp.toLocaleTimeString("ko-KR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });

  return (
    <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
      <Clock className="h-3 w-3" />
      {formatted} 업데이트
    </span>
  );
}
