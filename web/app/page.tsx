"use client";

import { useState } from "react";
import { DashboardHeader } from "@/components/layout/dashboard-header";
import type { TabKey } from "@/lib/constants";

export default function Home() {
  const [activeTab, setActiveTab] = useState<TabKey>("portfolio");

  return (
    <div className="min-h-screen bg-background">
      <DashboardHeader activeTab={activeTab} onTabChange={setActiveTab} />

      <main className="mx-auto max-w-7xl px-4 py-6">
        {activeTab === "portfolio" && <PlaceholderTab name="자산 현황" />}
        {activeTab === "benchmark" && <PlaceholderTab name="벤치마크 비교" />}
        {activeTab === "strategy" && <PlaceholderTab name="전략 설정" />}
        {activeTab === "backtest" && <PlaceholderTab name="백테스트" />}
        {activeTab === "paper" && <PlaceholderTab name="모의거래" />}
        {activeTab === "control" && <PlaceholderTab name="실행 & 제어" />}
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
