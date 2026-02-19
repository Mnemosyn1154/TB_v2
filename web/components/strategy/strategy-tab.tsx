"use client";

import { useCallback } from "react";
import { LoadingSpinner } from "@/components/common/loading-spinner";
import { useApi } from "@/hooks/use-api";
import { getSettings, updateSettings } from "@/lib/api-client";
import { StrategyCard } from "./strategy-card";
import { StrategyCreateDialog } from "./strategy-create-dialog";
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
    refetch();
  }

  async function handleDelete(key: string) {
    try {
      await fetch(`/api/settings/strategies/${key}`, { method: "DELETE" });
      refetch();
    } catch {
      // silently fail, refetch will show current state
    }
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
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">전략 설정</h2>
        <StrategyCreateDialog onCreated={refetch} />
      </div>

      <div className="flex flex-col gap-4">
        {Object.entries(strategies).map(([key, config]) => (
          <StrategyCard
            key={key}
            strategyKey={key}
            config={config}
            onToggle={handleToggle}
            onSave={handleSave}
            onDelete={handleDelete}
          />
        ))}
      </div>
    </div>
  );
}
