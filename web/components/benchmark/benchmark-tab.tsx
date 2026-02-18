"use client";

import { LoadingSpinner } from "@/components/common/loading-spinner";
import { useBenchmark } from "@/hooks/use-benchmark";
import { PeriodSelector } from "./period-selector";
import { BenchmarkChart } from "./benchmark-chart";
import { AlphaBetaCards } from "./alpha-beta-cards";
import { StrategyVsMarket } from "./strategy-vs-market";
import { formatPercent } from "@/lib/formatters";
import { cn } from "@/lib/utils";

export function BenchmarkTab() {
  const { data, error, loading, period, changePeriod } = useBenchmark();

  if (loading && !data) {
    return <LoadingSpinner />;
  }

  if (error && !data) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <p className="text-sm text-destructive">{error}</p>
      </div>
    );
  }

  if (!data) return null;

  const { metrics } = data;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">벤치마크 비교</h2>
        <PeriodSelector value={period} onChange={changePeriod} />
      </div>

      {/* 수익률 요약 뱃지 */}
      <div className="flex flex-wrap gap-3 text-sm">
        {[
          { label: "포트폴리오", value: metrics.portfolio_return },
          { label: "KOSPI", value: metrics.kospi_return },
          { label: "S&P500", value: metrics.sp500_return },
        ].map((item) => (
          <span
            key={item.label}
            className="inline-flex items-center gap-1.5 rounded-md border px-3 py-1"
          >
            <span className="text-muted-foreground">{item.label}</span>
            <span
              className={cn(
                "font-mono font-medium",
                item.value > 0 && "text-success",
                item.value < 0 && "text-destructive"
              )}
            >
              {formatPercent(item.value)}
            </span>
          </span>
        ))}
      </div>

      <BenchmarkChart data={data} />

      <AlphaBetaCards metrics={metrics} />

      {data.strategy_comparison.length > 0 && (
        <section>
          <h3 className="mb-3 text-sm font-semibold text-muted-foreground">
            전략별 벤치마크 대비
          </h3>
          <StrategyVsMarket comparisons={data.strategy_comparison} />
        </section>
      )}

      {loading && (
        <div className="text-center text-xs text-muted-foreground">
          데이터 갱신 중...
        </div>
      )}
    </div>
  );
}
