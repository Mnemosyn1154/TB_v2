"use client";

import { useState, useEffect, useCallback } from "react";
import type { ApiResponse } from "@/types/common";

interface UseApiState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  lastUpdated: Date | null;
  refetch: () => Promise<void>;
}

export function useApi<T>(fetcher: () => Promise<ApiResponse<T>>): UseApiState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const refetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetcher();
      if (res.error) {
        setError(res.error);
        setData(null);
      } else {
        setData(res.data);
        setLastUpdated(new Date());
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [fetcher]);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return { data, error, loading, lastUpdated, refetch };
}
