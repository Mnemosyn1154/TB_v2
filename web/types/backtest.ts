import type { Market, TradeSide } from "./common";

export interface UniverseStock {
  code: string;
  market: string;
  exchange: string;
  name: string;
  sector: string;
  market_cap: number;
  avg_volume: number;
  last_price: number;
}

export interface BacktestRequest {
  strategy: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  commission_rate?: number;
  slippage_rate?: number;
  pair_name?: string | null;
  universe_codes?: UniverseStock[] | null;
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
  name?: string;
  market: Market;
  side: TradeSide;
  quantity: number;
  price: number;
  amount: number;
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
  logs?: string[];
}

export interface PeerMetrics {
  total_return: number;
  cagr: number;
  mdd: number;
}

export interface PeerComparisonData {
  dates: string[];
  strategy: number[];
  kospi: number[];
  sp500: number[];
  metrics: {
    strategy: PeerMetrics;
    kospi: PeerMetrics;
    sp500: PeerMetrics;
  };
}
