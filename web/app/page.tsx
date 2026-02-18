"use client";

import { useState } from "react";
import { DashboardHeader } from "@/components/layout/dashboard-header";
import { ErrorBoundary } from "@/components/common/error-boundary";
import { PortfolioTab } from "@/components/portfolio/portfolio-tab";
import { BenchmarkTab } from "@/components/benchmark/benchmark-tab";
import { StrategyTab } from "@/components/strategy/strategy-tab";
import { BacktestTab } from "@/components/backtest/backtest-tab";
import { PaperTab } from "@/components/paper/paper-tab";
import { ControlTab } from "@/components/control/control-tab";
import type { TabKey } from "@/lib/constants";
import type { TradingMode } from "@/types/control";

export default function Home() {
  const [activeTab, setActiveTab] = useState<TabKey>("portfolio");
  const [tradingMode, setTradingMode] = useState<TradingMode>("paper");

  return (
    <div className="min-h-screen bg-background">
      <DashboardHeader
        activeTab={activeTab}
        onTabChange={setActiveTab}
        tradingMode={tradingMode}
      />

      <main className="mx-auto max-w-7xl px-4 py-6">
        <ErrorBoundary>
          {activeTab === "portfolio" && <PortfolioTab />}
          {activeTab === "benchmark" && <BenchmarkTab />}
          {activeTab === "strategy" && <StrategyTab />}
          {activeTab === "backtest" && <BacktestTab />}
          {activeTab === "paper" && <PaperTab />}
          {activeTab === "control" && (
            <ControlTab onModeChange={setTradingMode} />
          )}
        </ErrorBoundary>
      </main>
    </div>
  );
}
