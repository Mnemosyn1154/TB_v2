"use client";

import { useState, useCallback, useEffect } from "react";
import { getBotStatus } from "@/lib/api-client";
import type { ApiResponse } from "@/types/common";
import type { FullBotStatus, SchedulerStatus, TradingMode } from "@/types/control";

interface BotStatusResult {
  kill_switch: boolean;
  mode: TradingMode;
  scheduler: SchedulerStatus | null;
}

export function useBotStatus() {
  const [status, setStatus] = useState<BotStatusResult | null>(null);

  const fetch = useCallback(async () => {
    try {
      const res = (await getBotStatus()) as ApiResponse<FullBotStatus>;
      if (res.data) {
        setStatus({
          kill_switch: res.data.kill_switch,
          mode: res.data.mode ?? "simulation",
          scheduler: res.data.scheduler,
        });
      }
    } catch {
      // silently fail - header indicator is non-critical
    }
  }, []);

  useEffect(() => {
    fetch();
    const id = setInterval(fetch, 30_000); // 30s polling
    return () => clearInterval(id);
  }, [fetch]);

  return status;
}
