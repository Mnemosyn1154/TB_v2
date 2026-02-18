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
  onModeChange: (mode: TradingMode) => void;
}

export function ModeToggle({ mode, onModeChange }: ModeToggleProps) {
  const [confirmOpen, setConfirmOpen] = useState(false);

  const handleToggle = (target: TradingMode) => {
    if (target === "live") {
      setConfirmOpen(true);
    } else {
      onModeChange("paper");
    }
  };

  const confirmLiveMode = () => {
    onModeChange("live");
    setConfirmOpen(false);
  };

  return (
    <>
      <div className="flex items-center gap-2">
        <button
          onClick={() => handleToggle("paper")}
          className={`rounded-l-md px-4 py-2 text-sm font-medium transition-colors ${
            mode === "paper"
              ? "bg-blue-500 text-white"
              : "bg-muted text-muted-foreground hover:bg-accent"
          }`}
        >
          모의투자
        </button>
        <button
          onClick={() => handleToggle("live")}
          className={`rounded-r-md px-4 py-2 text-sm font-medium transition-colors ${
            mode === "live"
              ? "bg-red-500 text-white"
              : "bg-muted text-muted-foreground hover:bg-accent"
          }`}
        >
          실거래
        </button>
      </div>

      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>실거래 모드 전환</DialogTitle>
            <DialogDescription>
              정말 실거래 모드로 전환하시겠습니까? 실거래 모드에서는 실제 주문이
              실행됩니다.
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
  return (
    <Badge
      variant={mode === "live" ? "destructive" : "secondary"}
      className="text-xs"
    >
      {mode === "live" ? "실거래" : "모의투자"}
    </Badge>
  );
}
