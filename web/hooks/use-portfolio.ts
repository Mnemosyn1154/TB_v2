"use client";

import { useCallback } from "react";
import { useApi } from "./use-api";
import { useInterval } from "./use-interval";
import { getPortfolio } from "@/lib/api-client";
import { DEFAULTS } from "@/lib/constants";
import type { PortfolioData } from "@/types/portfolio";
import type { ApiResponse } from "@/types/common";

export function usePortfolio() {
  const fetcher = useCallback(
    () => getPortfolio() as Promise<ApiResponse<PortfolioData>>,
    []
  );
  const { data, error, loading, refetch } = useApi<PortfolioData>(fetcher);

  useInterval(refetch, DEFAULTS.POLLING_INTERVAL);

  return { data, error, loading, refetch };
}
