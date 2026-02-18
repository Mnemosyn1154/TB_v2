"use client";

import { useState, useCallback } from "react";
import { runBacktest as runBacktestApi } from "@/lib/api-client";
import type { BacktestRequest, BacktestResult } from "@/types/backtest";
import type { ApiResponse } from "@/types/common";

interface UseBacktestReturn {
  result: BacktestResult | null;
  error: string | null;
  loading: boolean;
  run: (params: BacktestRequest) => Promise<void>;
  clear: () => void;
}

export function useBacktest(): UseBacktestReturn {
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const run = useCallback(async (params: BacktestRequest) => {
    setLoading(true);
    setError(null);
    try {
      const res = (await runBacktestApi(params)) as ApiResponse<BacktestResult>;
      if (res.error) {
        setError(res.error);
      } else {
        setResult(res.data);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, []);

  const clear = useCallback(() => {
    setResult(null);
    setError(null);
  }, []);

  return { result, error, loading, run, clear };
}
