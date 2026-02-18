import { TrendingUp, Activity, BarChart3 } from "lucide-react";
import { MetricsCard } from "@/components/common/metrics-card";
import { formatPercent } from "@/lib/formatters";
import type { BenchmarkMetrics } from "@/types/benchmark";

interface AlphaBetaCardsProps {
  metrics: BenchmarkMetrics;
}

export function AlphaBetaCards({ metrics }: AlphaBetaCardsProps) {
  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
      <MetricsCard
        icon={TrendingUp}
        label="Alpha"
        value={formatPercent(metrics.alpha)}
        description="시장 대비 초과수익"
        changePositive={metrics.alpha > 0}
      />
      <MetricsCard
        icon={Activity}
        label="Beta"
        value={metrics.beta.toFixed(2)}
        description="시장 대비 변동성"
      />
      <MetricsCard
        icon={BarChart3}
        label="Information Ratio"
        value={metrics.information_ratio.toFixed(2)}
        description="추적오차 대비 초과수익"
        changePositive={metrics.information_ratio > 0}
      />
    </div>
  );
}
