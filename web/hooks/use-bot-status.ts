"use client";

import { useState, useCallback, useEffect } from "react";
import { getKillSwitch } from "@/lib/api-client";
import type { ApiResponse } from "@/types/common";

interface BotStatus {
  kill_switch: boolean;
  mode: "live" | "paper" | "idle";
}

export function useBotStatus() {
  const [status, setStatus] = useState<BotStatus | null>(null);

  const fetch = useCallback(async () => {
    try {
      const res = (await getKillSwitch()) as ApiResponse<BotStatus>;
      if (res.data) {
        setStatus(res.data);
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
