export interface Position {
  code: string;
  name: string;
  quantity: number;
  avg_price: number;
  current_price: number;
  profit_pct: number;
  profit_amt: number;
  market: "KR" | "US";
  strategy?: string;
}

export interface RiskSummary {
  total_equity: number;
  cash: number;
  cash_pct: string;
  daily_pnl: number;
  drawdown: string;
  positions_count: number;
  max_positions: number;
  kill_switch: boolean;
  positions: { code: string; side: string; pnl_pct: string; value: number }[];
}

export interface StrategyStatus {
  name: string;
  key: string;
  enabled: boolean;
  pnl_pct: number;
  positions_count: number;
}

export interface MarketBalance {
  positions: Position[];
  total_equity?: number;
  cash?: number;
  total_value?: number;
}

export interface PortfolioData {
  kr: MarketBalance;
  us: MarketBalance;
  risk: RiskSummary;
  strategies?: StrategyStatus[];
  initial_capital?: number;
  exchange_rate?: number;
}
