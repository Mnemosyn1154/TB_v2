"use client";

import { useState, useCallback } from "react";
import { LoadingSpinner } from "@/components/common/loading-spinner";
import { useApi } from "@/hooks/use-api";
import { getSettings, updateSettings } from "@/lib/api-client";
import { StrategyList } from "./strategy-list";
import { StrategyEditor } from "./strategy-editor";
import { UniverseViewer } from "./universe-viewer";
import type { ApiResponse } from "@/types/common";

interface SettingsData {
  strategies: Record<string, Record<string, unknown>>;
  [key: string]: unknown;
}

export function StrategyTab() {
  const fetcher = useCallback(
    () => getSettings() as Promise<ApiResponse<SettingsData>>,
    []
  );
  const { data, error, loading, refetch } = useApi<SettingsData>(fetcher);
  const [editingKey, setEditingKey] = useState<string | null>(null);

  async function handleToggle(key: string) {
    try {
      await fetch(`/api/settings/strategies/${key}/toggle`, {
        method: "PATCH",
      });
      refetch();
    } catch {
      // silently fail, refetch will show current state
    }
  }

  async function handleSave(key: string, updated: Record<string, unknown>) {
    if (!data) return;
    const newData = {
      ...data,
      strategies: { ...data.strategies, [key]: updated },
    };
    await updateSettings(newData);
    setEditingKey(null);
    refetch();
  }

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

  const strategies = data.strategies;

  return (
    <div className="flex flex-col gap-6">
      <h2 className="text-lg font-semibold">전략 설정</h2>

      <StrategyList
        strategies={strategies}
        onToggle={handleToggle}
        onEdit={setEditingKey}
      />

      {/* 유니버스 뷰어 - 각 전략별 */}
      {Object.entries(strategies).map(([key, config]) => {
        const enabled = config.enabled as boolean;
        if (!enabled) return null;
        return (
          <section key={key}>
            <h3 className="mb-3 text-sm font-semibold text-muted-foreground">
              {key === "stat_arb"
                ? "페어 유니버스"
                : key === "dual_momentum"
                  ? "ETF 목록"
                  : key === "quant_factor"
                    ? "종목 유니버스"
                    : "유니버스"}
            </h3>
            <UniverseViewer strategyKey={key} config={config} />
          </section>
        );
      })}

      <StrategyEditor
        strategyKey={editingKey}
        config={editingKey ? strategies[editingKey] ?? null : null}
        onSave={handleSave}
        onClose={() => setEditingKey(null)}
      />
    </div>
  );
}
