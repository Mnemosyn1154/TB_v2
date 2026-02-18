import { Wallet, TrendingUp, Banknote, BarChart3 } from "lucide-react";
import { MetricsCard } from "@/components/common/metrics-card";
import { formatKRW, formatPercent } from "@/lib/formatters";
import type { PortfolioData } from "@/types/portfolio";

function parsePercentString(s: string): number {
  return parseFloat(s.replace("%", "")) || 0;
}

interface PortfolioKPIsProps {
  data: PortfolioData;
}

export function PortfolioKPIs({ data }: PortfolioKPIsProps) {
  const { risk } = data;
  const cashPct = parsePercentString(risk.cash_pct);
  const drawdown = parsePercentString(risk.drawdown);

  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      <MetricsCard
        icon={Wallet}
        label="총자산"
        value={formatKRW(risk.total_equity)}
        description={`현금 ${formatKRW(risk.cash)}`}
      />
      <MetricsCard
        icon={TrendingUp}
        label="일일 손익"
        value={formatKRW(risk.daily_pnl)}
        changePositive={risk.daily_pnl > 0}
        change={risk.daily_pnl !== 0 ? (risk.daily_pnl > 0 ? "+" : "") + formatKRW(risk.daily_pnl) : undefined}
      />
      <MetricsCard
        icon={Banknote}
        label="현금 비중"
        value={formatPercent(cashPct, 1)}
        description={`포지션 ${risk.positions_count} / ${risk.max_positions}`}
      />
      <MetricsCard
        icon={BarChart3}
        label="드로다운"
        value={formatPercent(drawdown, 1)}
        changePositive={drawdown >= 0}
      />
    </div>
  );
}
