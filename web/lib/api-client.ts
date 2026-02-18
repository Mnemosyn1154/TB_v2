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

// Cache TTL constants (ms)
const CACHE_TTL = {
  PORTFOLIO: 5 * 60 * 1000,  // 5분
  BENCHMARK: 15 * 60 * 1000, // 15분
} as const;

async function fetchApi<T>(
  path: string,
  options?: RequestInit
): Promise<ApiResponse<T>> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  return res.json();
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

// Bot
export const runBot = () => fetchApi("/bot/run", { method: "POST" });
export const collectData = () =>
  fetchApi("/bot/collect", { method: "POST" });
export const getKillSwitch = () => fetchApi("/bot/kill-switch");
export const activateKillSwitch = () =>
  fetchApi("/bot/kill-switch/activate", { method: "POST" });
export const deactivateKillSwitch = () =>
  fetchApi("/bot/kill-switch/deactivate", { method: "POST" });

// Signals
export const getSignals = () => fetchApi("/signals");

// Paper Trading
export const getPaperSessions = () => fetchApi("/paper/sessions");
export const createPaperSession = () =>
  fetchApi("/paper/sessions", { method: "POST" });
export const executeAllSignals = () =>
  fetchApi("/paper/execute-all", { method: "POST" });
