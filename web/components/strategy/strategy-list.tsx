"use client";

import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Settings } from "lucide-react";
import { cn } from "@/lib/utils";

interface StrategyListProps {
  strategies: Record<string, Record<string, unknown>>;
  onToggle: (key: string) => void;
  onEdit: (key: string) => void;
}

const STRATEGY_LABELS: Record<string, string> = {
  stat_arb: "Statistical Arbitrage",
  dual_momentum: "Dual Momentum",
  quant_factor: "Quant Factor",
};

function summarize(key: string, config: Record<string, unknown>): string {
  switch (key) {
    case "stat_arb": {
      const pairs = config.pairs as unknown[] | undefined;
      return `Z-Score 진입: ${config.entry_z_score} / 청산: ${config.exit_z_score} / 손절: ${config.stop_loss_z_score} · 룩백: ${config.lookback_window}일 · ${pairs?.length ?? 0}개 페어`;
    }
    case "dual_momentum":
      return `룩백: ${config.lookback_months}개월 · 리밸런싱: 매월 ${config.rebalance_day}일`;
    case "quant_factor": {
      const w = config.weights as Record<string, number> | undefined;
      const codes = config.universe_codes as unknown[] | undefined;
      return w
        ? `Value ${(w.value * 100).toFixed(0)}% / Quality ${(w.quality * 100).toFixed(0)}% / Momentum ${(w.momentum * 100).toFixed(0)}% · ${codes?.length ?? 0}종목`
        : "";
    }
    default:
      return "";
  }
}

export function StrategyList({
  strategies,
  onToggle,
  onEdit,
}: StrategyListProps) {
  return (
    <div className="flex flex-col gap-4">
      {Object.entries(strategies).map(([key, config]) => {
        const enabled = config.enabled as boolean;
        return (
          <Card
            key={key}
            className={cn("gap-0 py-4", !enabled && "opacity-60")}
          >
            <CardContent className="flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="font-semibold">
                    {STRATEGY_LABELS[key] ?? key}
                  </span>
                  <Badge variant={enabled ? "default" : "secondary"}>
                    {enabled ? "ON" : "OFF"}
                  </Badge>
                </div>
                <Switch
                  checked={enabled}
                  onCheckedChange={() => onToggle(key)}
                />
              </div>
              <p className="text-sm text-muted-foreground">
                {summarize(key, config)}
              </p>
              <div className="flex justify-end">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onEdit(key)}
                >
                  <Settings className="mr-1.5 h-3.5 w-3.5" />
                  파라미터 편집
                </Button>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
