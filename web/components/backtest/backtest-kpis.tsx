import {
  TrendingUp,
  BarChart3,
  Activity,
  TrendingDown,
  Target,
  Scale,
} from "lucide-react";
import { MetricsCard } from "@/components/common/metrics-card";
import { formatPercent } from "@/lib/formatters";
import type { BacktestMetrics } from "@/types/backtest";

interface BacktestKPIsProps {
  metrics: BacktestMetrics;
}

export function BacktestKPIs({ metrics }: BacktestKPIsProps) {
  const v = (n: number | null | undefined) => n ?? 0;

  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
      <MetricsCard
        icon={TrendingUp}
        label="총 수익률"
        value={formatPercent(v(metrics.total_return) * 100)}
        changePositive={v(metrics.total_return) > 0}
      />
      <MetricsCard
        icon={BarChart3}
        label="CAGR"
        value={formatPercent(v(metrics.cagr) * 100)}
        changePositive={v(metrics.cagr) > 0}
      />
      <MetricsCard
        icon={Activity}
        label="Sharpe Ratio"
        value={v(metrics.sharpe_ratio).toFixed(2)}
        changePositive={v(metrics.sharpe_ratio) > 0}
      />
      <MetricsCard
        icon={TrendingDown}
        label="MDD"
        value={formatPercent(v(metrics.mdd) * 100)}
        changePositive={false}
      />
      <MetricsCard
        icon={Target}
        label="승률"
        value={formatPercent(v(metrics.win_rate) * 100)}
        description={`총 ${metrics.total_trades ?? 0}건`}
      />
      <MetricsCard
        icon={Scale}
        label="손익비"
        value={v(metrics.profit_factor).toFixed(2)}
        changePositive={v(metrics.profit_factor) > 1}
      />
    </div>
  );
}
