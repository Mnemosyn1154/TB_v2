"use client";

import { useEffect, useState } from "react";
import { checkKisHealth } from "@/lib/api-client";
import type { ApiResponse } from "@/types/common";

interface KisHealth {
  connected: boolean;
  mode: string | null;
  account: string | null;
  error: string | null;
}

export function KisStatus() {
  const [health, setHealth] = useState<KisHealth | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const res = (await checkKisHealth()) as ApiResponse<KisHealth>;
        setHealth(res.data ?? null);
      } catch {
        setHealth(null);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <span className="h-2 w-2 rounded-full bg-muted animate-pulse" />
        KIS 연결 확인 중...
      </div>
    );
  }

  if (!health) {
    return (
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <span className="h-2 w-2 rounded-full bg-muted" />
        KIS 상태 불명
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 text-xs">
      <span
        className={`h-2 w-2 rounded-full ${
          health.connected ? "bg-green-500" : "bg-red-500"
        }`}
      />
      <span className={health.connected ? "text-green-400" : "text-red-400"}>
        KIS {health.connected ? "연결됨" : "미연결"}
      </span>
      {health.connected && health.account && (
        <span className="text-muted-foreground">
          ({health.mode === "live" ? "실거래" : "모의"} / {health.account})
        </span>
      )}
      {!health.connected && health.error && (
        <span className="text-muted-foreground truncate max-w-[200px]" title={health.error}>
          {health.error}
        </span>
      )}
    </div>
  );
}
