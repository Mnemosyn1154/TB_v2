import type { ApiResponse } from "@/types/common";

const BASE_URL = "/api";

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

// Portfolio
export const getPortfolio = () => fetchApi("/portfolio");

// Benchmark
export const getBenchmark = (period = "3M") =>
  fetchApi(`/benchmark?period=${period}`);

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
export const createPaperSession = () =>
  fetchApi("/paper/sessions", { method: "POST" });
export const executeAllSignals = () =>
  fetchApi("/paper/execute-all", { method: "POST" });
