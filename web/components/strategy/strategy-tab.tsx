"use client";

import { useCallback, useMemo, useState } from "react";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  arrayMove,
} from "@dnd-kit/sortable";
import { restrictToVerticalAxis } from "@dnd-kit/modifiers";
import { LoadingSpinner } from "@/components/common/loading-spinner";
import { useApi } from "@/hooks/use-api";
import { getSettings, updateSettings } from "@/lib/api-client";
import { SortableStrategyCard } from "./sortable-strategy-card";
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

  // Local ordering override — null means use server order
  const [localOrder, setLocalOrder] = useState<string[] | null>(null);

  const strategyKeys = useMemo(() => {
    if (!data) return [];
    const serverKeys = Object.keys(data.strategies);
    if (localOrder) {
      // Keep localOrder but filter out deleted keys, append new ones
      const existing = new Set(serverKeys);
      const ordered = localOrder.filter((k) => existing.has(k));
      const appended = serverKeys.filter((k) => !localOrder.includes(k));
      return [...ordered, ...appended];
    }
    return serverKeys;
  }, [data, localOrder]);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  async function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id || !data) return;

    const oldIndex = strategyKeys.indexOf(active.id as string);
    const newIndex = strategyKeys.indexOf(over.id as string);
    const newOrder = arrayMove(strategyKeys, oldIndex, newIndex);
    setLocalOrder(newOrder);

    // Rebuild strategies object in new order
    const reordered: Record<string, Record<string, unknown>> = {};
    for (const key of newOrder) {
      reordered[key] = data.strategies[key];
    }
    await updateSettings({ ...data, strategies: reordered });
    refetch();
  }

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
      setLocalOrder((prev) => prev?.filter((k) => k !== key) ?? null);
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

      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        modifiers={[restrictToVerticalAxis]}
        onDragEnd={handleDragEnd}
      >
        <SortableContext
          items={strategyKeys}
          strategy={verticalListSortingStrategy}
        >
          <div className="flex flex-col gap-4">
            {strategyKeys.map((key) => (
              <SortableStrategyCard
                key={key}
                strategyKey={key}
                config={strategies[key]}
                onToggle={handleToggle}
                onSave={handleSave}
                onDelete={handleDelete}
              />
            ))}
          </div>
        </SortableContext>
      </DndContext>
    </div>
  );
}
