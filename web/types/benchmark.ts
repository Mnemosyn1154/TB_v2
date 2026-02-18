export interface BenchmarkMetrics {
  portfolio_return: number;
  kospi_return: number;
  sp500_return: number;
  alpha: number;
  beta: number;
  information_ratio: number;
}

export interface StrategyComparison {
  strategy: string;
  return_pct: number;
  benchmark_return: number;
  excess_return: number;
}

export interface BenchmarkData {
  dates: string[];
  portfolio: number[];
  kospi: number[];
  sp500: number[];
  metrics: BenchmarkMetrics;
  strategy_comparison: StrategyComparison[];
}
