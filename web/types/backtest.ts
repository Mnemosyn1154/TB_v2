import type { Market, TradeSide } from "./common";

export interface BacktestRequest {
  strategy: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  commission_rate?: number;
  slippage_rate?: number;
  pair_name?: string | null;
}

export interface BacktestMetrics {
  total_return: number;
  cagr: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  mdd: number;
  win_rate: number;
  profit_factor: number;
  total_trades: number;
  avg_holding_days: number;
}

export interface Trade {
  date: string;
  strategy: string;
  code: string;
  market: Market;
  side: TradeSide;
  quantity: number;
  price: number;
  commission: number;
  pnl: number | null;
  pnl_pct: number | null;
  holding_days: number | null;
}

export interface BacktestResult {
  metrics: BacktestMetrics;
  equity_curve: { dates: string[]; values: number[] };
  monthly_returns: { index: number[]; columns: string[]; data: number[][] };
  trades: Trade[];
  pnl_values: number[];
}
