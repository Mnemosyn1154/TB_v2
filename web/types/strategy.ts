export interface StrategyConfig {
  enabled: boolean;
  [key: string]: unknown;
}

export interface StrategiesData {
  strategies: Record<string, StrategyConfig>;
  risk: Record<string, unknown>;
  backtest: Record<string, unknown>;
}
