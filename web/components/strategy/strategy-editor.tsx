"use client";

import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface StrategyEditorProps {
  strategyKey: string | null;
  config: Record<string, unknown> | null;
  onSave: (key: string, updated: Record<string, unknown>) => void;
  onClose: () => void;
}

const STRATEGY_LABELS: Record<string, string> = {
  stat_arb: "Statistical Arbitrage",
  dual_momentum: "Dual Momentum",
  quant_factor: "Quant Factor",
};

/** 편집 가능한 숫자 파라미터만 추출 */
function getEditableParams(
  key: string,
  config: Record<string, unknown>
): { field: string; label: string; value: number }[] {
  switch (key) {
    case "stat_arb":
      return [
        { field: "lookback_window", label: "룩백 윈도우 (일)", value: config.lookback_window as number },
        { field: "entry_z_score", label: "진입 Z-Score", value: config.entry_z_score as number },
        { field: "exit_z_score", label: "청산 Z-Score", value: config.exit_z_score as number },
        { field: "stop_loss_z_score", label: "손절 Z-Score", value: config.stop_loss_z_score as number },
        { field: "recalc_beta_days", label: "헤지 비율 재계산 주기 (일)", value: config.recalc_beta_days as number },
        { field: "coint_pvalue", label: "공적분 p-value 임계값", value: config.coint_pvalue as number },
      ];
    case "dual_momentum":
      return [
        { field: "lookback_months", label: "룩백 기간 (월)", value: config.lookback_months as number },
        { field: "rebalance_day", label: "리밸런싱 거래일", value: config.rebalance_day as number },
        { field: "risk_free_rate", label: "무위험수익률 (연)", value: config.risk_free_rate as number },
      ];
    case "quant_factor":
      return [
        { field: "top_n", label: "상위 N종목", value: config.top_n as number },
        { field: "rebalance_months", label: "리밸런싱 주기 (월)", value: config.rebalance_months as number },
        { field: "lookback_days", label: "Value 룩백 (거래일)", value: config.lookback_days as number },
        { field: "momentum_days", label: "Momentum 룩백 (거래일)", value: config.momentum_days as number },
        { field: "volatility_days", label: "변동성 윈도우 (일)", value: config.volatility_days as number },
      ];
    default:
      return [];
  }
}

export function StrategyEditor({
  strategyKey,
  config,
  onSave,
  onClose,
}: StrategyEditorProps) {
  const [values, setValues] = useState<Record<string, number>>({});
  const open = strategyKey !== null && config !== null;

  useEffect(() => {
    if (strategyKey && config) {
      const params = getEditableParams(strategyKey, config);
      const init: Record<string, number> = {};
      for (const p of params) init[p.field] = p.value;
      setValues(init);
    }
  }, [strategyKey, config]);

  if (!strategyKey || !config) return null;

  const params = getEditableParams(strategyKey, config);

  function handleSave() {
    if (!strategyKey || !config) return;
    const updated = { ...config };
    for (const [k, v] of Object.entries(values)) {
      updated[k] = v;
    }
    onSave(strategyKey, updated);
  }

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>
            {STRATEGY_LABELS[strategyKey] ?? strategyKey} 파라미터
          </DialogTitle>
        </DialogHeader>
        <div className="flex flex-col gap-4 py-2">
          {params.map((p) => (
            <div key={p.field} className="flex flex-col gap-1.5">
              <Label htmlFor={p.field} className="text-sm">
                {p.label}
              </Label>
              <Input
                id={p.field}
                type="number"
                step="any"
                value={values[p.field] ?? ""}
                onChange={(e) =>
                  setValues((prev) => ({
                    ...prev,
                    [p.field]: parseFloat(e.target.value) || 0,
                  }))
                }
              />
            </div>
          ))}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            취소
          </Button>
          <Button onClick={handleSave}>저장</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
