"use client";

import { useState, useCallback, useEffect } from "react";
import { getBenchmark } from "@/lib/api-client";
import type { BenchmarkData } from "@/types/benchmark";
import type { ApiResponse } from "@/types/common";

export function useBenchmark() {
  const [period, setPeriod] = useState("3M");
  const [data, setData] = useState<BenchmarkData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async (p: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = (await getBenchmark(p)) as ApiResponse<BenchmarkData>;
      if (res.error) {
        setError(res.error);
      } else {
        setData(res.data);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData(period);
  }, [period, fetchData]);

  const changePeriod = useCallback(
    (p: string) => setPeriod(p),
    []
  );

  return { data, error, loading, period, changePeriod };
}
