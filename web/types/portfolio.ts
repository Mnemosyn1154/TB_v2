export interface Position {
  code: string;
  name: string;
  quantity: number;
  avg_price: number;
  current_price: number;
  pnl_pct: number;
  value: number;
  weight: number;
}

export interface RiskSummary {
  total_equity: number;
  cash: number;
  cash_pct: number;
  daily_pnl: number;
  drawdown: number;
  mdd: number;
  positions_count: number;
  max_positions: number;
  kill_switch: boolean;
  sharpe_ratio: number;
  sortino_ratio: number;
}

export interface StrategyStatus {
  name: string;
  key: string;
  enabled: boolean;
  pnl_pct: number;
  positions_count: number;
}

export interface PortfolioData {
  kr: { total_equity: number; cash: number; positions: Position[] };
  us: { total_equity: number; cash: number; positions: Position[] };
  risk: RiskSummary;
  strategies: StrategyStatus[];
}
