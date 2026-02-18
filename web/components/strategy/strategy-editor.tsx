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
import { snakeToTitle, extractNumericParams } from "@/lib/strategy-utils";

interface StrategyEditorProps {
  strategyKey: string | null;
  config: Record<string, unknown> | null;
  onSave: (key: string, updated: Record<string, unknown>) => void;
  onClose: () => void;
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
      const params = extractNumericParams(config);
      const init: Record<string, number> = {};
      for (const p of params) init[p.field] = p.value;
      setValues(init);
    }
  }, [strategyKey, config]);

  if (!strategyKey || !config) return null;

  const params = extractNumericParams(config);

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
            {snakeToTitle(strategyKey)} 파라미터
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
