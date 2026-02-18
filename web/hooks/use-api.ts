"use client";

import { useState, useEffect, useCallback } from "react";
import { useToast } from "@/components/common/toast-provider";
import type { ApiResponse } from "@/types/common";

interface UseApiOptions {
  /** 에러 시 토스트 표시 여부 (기본 true) */
  showErrorToast?: boolean;
}

interface UseApiState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  lastUpdated: Date | null;
  refetch: () => Promise<void>;
}

export function useApi<T>(
  fetcher: () => Promise<ApiResponse<T>>,
  options?: UseApiOptions,
): UseApiState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const { toast } = useToast();
  const showToast = options?.showErrorToast ?? true;

  const refetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetcher();
      if (res.error) {
        setError(res.error);
        setData(null);
        if (showToast) toast("error", res.error);
      } else {
        setData(res.data);
        setLastUpdated(new Date());
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Unknown error";
      setError(msg);
      setData(null);
      if (showToast) toast("error", msg);
    } finally {
      setLoading(false);
    }
  }, [fetcher, showToast, toast]);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return { data, error, loading, lastUpdated, refetch };
}
