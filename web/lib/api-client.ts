import type { ApiResponse } from "@/types/common";

const BASE_URL = "/api";

// --- Response cache ---
const cache = new Map<string, { data: unknown; expiry: number }>();

function getCached<T>(key: string): ApiResponse<T> | null {
  const entry = cache.get(key);
  if (!entry) return null;
  if (Date.now() > entry.expiry) {
    cache.delete(key);
    return null;
  }
  return entry.data as ApiResponse<T>;
}

function setCache(key: string, data: unknown, ttlMs: number) {
  cache.set(key, { data, expiry: Date.now() + ttlMs });
}

/** 특정 경로 또는 전체 캐시 무효화 */
export function invalidateCache(pathPrefix?: string) {
  if (!pathPrefix) {
    cache.clear();
    return;
  }
  for (const key of cache.keys()) {
    if (key.startsWith(pathPrefix)) {
      cache.delete(key);
    }
  }
}

// Cache TTL constants (ms)
const CACHE_TTL = {
  PORTFOLIO: 5 * 60 * 1000,  // 5분
  BENCHMARK: 15 * 60 * 1000, // 15분
} as const;

async function fetchApi<T>(
  path: string,
  options?: RequestInit
): Promise<ApiResponse<T>> {
  try {
    const res = await fetch(`${BASE_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    return res.json();
  } catch (e) {
    return {
      data: null,
      error: e instanceof Error ? e.message : "Network error",
    } as ApiResponse<T>;
  }
}

async function fetchCached<T>(
  path: string,
  ttlMs: number
): Promise<ApiResponse<T>> {
  const cached = getCached<T>(path);
  if (cached) return cached;
  const result = await fetchApi<T>(path);
  if (!result.error) {
    setCache(path, result, ttlMs);
  }
  return result;
}

// Portfolio
export const getPortfolio = () =>
  fetchCached("/portfolio", CACHE_TTL.PORTFOLIO);
export const getCapital = () => fetchApi("/portfolio/capital");
export const setCapital = async (amount: number) => {
  const res = await fetchApi("/portfolio/capital", {
    method: "POST",
    body: JSON.stringify({ amount }),
  });
  invalidateCache("/portfolio");
  return res;
};
export const resetPortfolio = async () => {
  const res = await fetchApi("/portfolio/reset", { method: "POST" });
  invalidateCache("/portfolio");
  return res;
};

// Benchmark
export const getBenchmark = (period = "3M") =>
  fetchCached(`/benchmark?period=${period}`, CACHE_TTL.BENCHMARK);

// Settings
export const getSettings = () => fetchApi("/settings");
export const updateSettings = (data: unknown) =>
  fetchApi("/settings", { method: "PUT", body: JSON.stringify(data) });

// Backtest
export const runBacktest = (params: unknown) =>
  fetchApi("/backtest/run", { method: "POST", body: JSON.stringify(params) });
export const runBacktestPerPair = (params: unknown) =>
  fetchApi("/backtest/run-per-pair", {
    method: "POST",
    body: JSON.stringify(params),
  });
export const getBacktestPairs = (strategy: string) =>
  fetchApi(`/backtest/pairs/${strategy}`);
export const getBacktestPeerComparison = (params: {
  start_date: string;
  end_date: string;
  equity_curve: { dates: string[]; values: number[] };
}) =>
  fetchApi("/backtest/peer-comparison", {
    method: "POST",
    body: JSON.stringify(params),
  });

// Bot
export const runBot = () => fetchApi("/bot/run", { method: "POST" });
export const collectData = () =>
  fetchApi("/bot/collect", { method: "POST" });
export const getKillSwitch = () => fetchApi("/bot/kill-switch");
export const toggleKillSwitch = (action: "activate" | "deactivate") =>
  fetchApi("/bot/kill-switch", {
    method: "POST",
    body: JSON.stringify({ action }),
  });
export const getBotStatus = () => fetchApi("/bot/status");

// Signals
export const getSignals = () => fetchApi("/signals");

// Paper Trading
export const getPaperSessions = () => fetchApi("/paper/sessions");
export const getActivePaperSession = () => fetchApi("/paper/sessions/active");
export const createPaperSession = () =>
  fetchApi("/paper/sessions", { method: "POST" });
export const stopPaperSession = (id: string) =>
  fetchApi(`/paper/sessions/${id}/stop`, { method: "POST" });
export const getPaperTrades = (id: string) =>
  fetchApi(`/paper/sessions/${id}/trades`);
export const getPaperSummary = (id: string) =>
  fetchApi(`/paper/sessions/${id}/summary`);
export const executePaperSignals = (sessionId: string, signalIndex?: number) =>
  fetchApi("/paper/execute", {
    method: "POST",
    body: JSON.stringify({
      session_id: sessionId,
      signal_index: signalIndex ?? null,
    }),
  });
