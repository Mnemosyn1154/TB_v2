"use client";

import { useState } from "react";
import { DashboardHeader } from "@/components/layout/dashboard-header";
import { ErrorBoundary } from "@/components/common/error-boundary";
import { PortfolioTab } from "@/components/portfolio/portfolio-tab";
import { BenchmarkTab } from "@/components/benchmark/benchmark-tab";
import { StrategyTab } from "@/components/strategy/strategy-tab";
import { BacktestTab } from "@/components/backtest/backtest-tab";
import type { TabKey } from "@/lib/constants";

export default function Home() {
  const [activeTab, setActiveTab] = useState<TabKey>("portfolio");

  return (
    <div className="min-h-screen bg-background">
      <DashboardHeader activeTab={activeTab} onTabChange={setActiveTab} />

      <main className="mx-auto max-w-7xl px-4 py-6">
        <ErrorBoundary>
          {activeTab === "portfolio" && <PortfolioTab />}
          {activeTab === "benchmark" && <BenchmarkTab />}
          {activeTab === "strategy" && <StrategyTab />}
          {activeTab === "backtest" && <BacktestTab />}
          {activeTab === "paper" && <PlaceholderTab name="모의거래" />}
          {activeTab === "control" && <PlaceholderTab name="실행 & 제어" />}
        </ErrorBoundary>
      </main>
    </div>
  );
}

function PlaceholderTab({ name }: { name: string }) {
  return (
    <div className="flex h-[60vh] items-center justify-center rounded-lg border border-dashed border-border">
      <div className="text-center">
        <h2 className="text-xl font-semibold">{name}</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          이 페이지는 곧 구현됩니다
        </p>
      </div>
    </div>
  );
}
