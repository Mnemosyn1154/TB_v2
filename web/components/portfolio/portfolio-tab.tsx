"use client";

import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { LoadingSpinner } from "@/components/common/loading-spinner";
import { LastUpdated } from "@/components/common/last-updated";
import { usePortfolio } from "@/hooks/use-portfolio";
import { CapitalSettings } from "./capital-settings";
import { PortfolioKPIs } from "./portfolio-kpis";
import { StrategyCards } from "./strategy-cards";
import { HoldingsTable } from "./holdings-table";
import { RiskIndicators } from "./risk-indicators";

export function PortfolioTab() {
  const { data, error, loading, lastUpdated, refetch } = usePortfolio();

  if (loading && !data) {
    return <LoadingSpinner />;
  }

  if (error && !data) {
    return (
      <div className="flex h-[60vh] flex-col items-center justify-center gap-4">
        <p className="text-sm text-destructive">{error}</p>
        <Button variant="outline" size="sm" onClick={refetch}>
          <RefreshCw className="mr-2 h-4 w-4" />
          다시 시도
        </Button>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold">자산 현황</h2>
          <LastUpdated timestamp={lastUpdated} />
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={refetch}
          disabled={loading}
        >
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          새로고침
        </Button>
      </div>

      {data.initial_capital !== undefined && (
        <CapitalSettings
          initialCapital={data.initial_capital}
          cash={data.risk.cash}
          onUpdate={refetch}
        />
      )}

      <PortfolioKPIs data={data} />

      {data.strategies && data.strategies.length > 0 && (
        <section>
          <h3 className="mb-3 text-sm font-semibold text-muted-foreground">
            전략별 실적
          </h3>
          <StrategyCards strategies={data.strategies} />
        </section>
      )}

      <section>
        <h3 className="mb-3 text-sm font-semibold text-muted-foreground">
          보유 종목
        </h3>
        <HoldingsTable kr={data.kr} us={data.us} />
      </section>

      <RiskIndicators risk={data.risk} />
    </div>
  );
}
