"use client";

import { useBacktest } from "@/hooks/use-backtest";
import { BacktestForm } from "./backtest-form";
import { BacktestKPIs } from "./backtest-kpis";
import { EquityCurve } from "./equity-curve";
import { DrawdownChart } from "./drawdown-chart";
import { MonthlyHeatmap } from "./monthly-heatmap";
import { PnlDistribution } from "./pnl-distribution";
import { TradeTable } from "./trade-table";

export function BacktestTab() {
  const { result, error, loading, run } = useBacktest();

  return (
    <div className="flex flex-col gap-6">
      <h2 className="text-lg font-semibold">백테스트</h2>

      <BacktestForm onRun={run} loading={loading} />

      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {result && (
        <>
          <BacktestKPIs metrics={result.metrics} />

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <EquityCurve
              dates={result.equity_curve.dates}
              values={result.equity_curve.values}
              initialCapital={
                result.equity_curve.values[0] ?? 50_000_000
              }
            />
            <DrawdownChart
              dates={result.equity_curve.dates}
              values={result.equity_curve.values}
            />
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <MonthlyHeatmap
              index={result.monthly_returns.index}
              columns={result.monthly_returns.columns}
              data={result.monthly_returns.data}
            />
            <PnlDistribution pnlValues={result.pnl_values} />
          </div>

          <TradeTable trades={result.trades} />
        </>
      )}

      {!result && !error && !loading && (
        <div className="flex h-[40vh] items-center justify-center rounded-lg border border-dashed border-border">
          <div className="text-center">
            <p className="text-sm text-muted-foreground">
              전략과 기간을 선택한 뒤 백테스트를 실행하세요
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
