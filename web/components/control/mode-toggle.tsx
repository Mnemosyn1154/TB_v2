"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import type { TradingMode } from "@/types/control";

interface ModeToggleProps {
  mode: TradingMode;
  switching?: boolean;
  error?: string | null;
  onModeChange: (mode: TradingMode, confirm?: boolean) => void;
}

const MODE_CONFIG = {
  simulation: { label: "시뮬레이션", color: "bg-blue-500 text-white" },
  paper: { label: "모의투자", color: "bg-amber-500 text-white" },
  live: { label: "실거래", color: "bg-red-500 text-white" },
} as const;

export function ModeToggle({ mode, switching, error, onModeChange }: ModeToggleProps) {
  const [confirmOpen, setConfirmOpen] = useState(false);

  const handleToggle = (target: TradingMode) => {
    if (target === mode) return;
    if (target === "live") {
      setConfirmOpen(true);
    } else {
      onModeChange(target);
    }
  };

  const confirmLiveMode = () => {
    onModeChange("live", true);
    setConfirmOpen(false);
  };

  return (
    <>
      <div className="space-y-2">
        <div className="flex items-center gap-1">
          {(Object.keys(MODE_CONFIG) as TradingMode[]).map((key, idx) => {
            const isActive = mode === key;
            const roundedClass =
              idx === 0 ? "rounded-l-md" : idx === 2 ? "rounded-r-md" : "";
            return (
              <button
                key={key}
                disabled={switching}
                onClick={() => handleToggle(key)}
                className={`px-4 py-2 text-sm font-medium transition-colors ${roundedClass} ${
                  isActive
                    ? MODE_CONFIG[key].color
                    : "bg-muted text-muted-foreground hover:bg-accent"
                } ${switching ? "opacity-50 cursor-not-allowed" : ""}`}
              >
                {MODE_CONFIG[key].label}
              </button>
            );
          })}
        </div>
        {error && (
          <p className="text-xs text-destructive">{error}</p>
        )}
      </div>

      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>실거래 모드 전환</DialogTitle>
            <DialogDescription>
              정말 실거래 모드로 전환하시겠습니까? 실거래 모드에서는 실제 주문이
              실행됩니다. KIS API를 통해 실제 자금이 사용됩니다.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmOpen(false)}>
              취소
            </Button>
            <Button variant="destructive" onClick={confirmLiveMode}>
              실거래 모드 전환
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

export function ModeBadge({ mode }: { mode: TradingMode }) {
  const config = {
    simulation: { label: "시뮬", variant: "secondary" as const, className: "bg-blue-500/20 text-blue-400 border-blue-500/30" },
    paper: { label: "모의", variant: "secondary" as const, className: "bg-amber-500/20 text-amber-400 border-amber-500/30" },
    live: { label: "실거래", variant: "destructive" as const, className: "" },
  };
  const c = config[mode];
  return (
    <Badge variant={c.variant} className={`text-xs ${c.className}`}>
      {c.label}
    </Badge>
  );
}
