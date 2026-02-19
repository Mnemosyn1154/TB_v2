"use client";

import { useState } from "react";
import { Settings, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { setCapital, resetPortfolio } from "@/lib/api-client";
import { formatKRW } from "@/lib/formatters";

interface CapitalSettingsProps {
  initialCapital: number;
  cash: number;
  onUpdate: () => void;
}

export function CapitalSettings({
  initialCapital,
  cash,
  onUpdate,
}: CapitalSettingsProps) {
  const formatWithCommas = (n: number) => n.toLocaleString("en-US");
  const parseRaw = (s: string) => s.replace(/,/g, "");

  const [display, setDisplay] = useState(formatWithCommas(initialCapital));
  const [loading, setLoading] = useState(false);
  const [resetOpen, setResetOpen] = useState(false);

  const handleAmountChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = parseRaw(e.target.value);
    if (raw === "" || /^\d+$/.test(raw)) {
      setDisplay(raw === "" ? "" : formatWithCommas(Number(raw)));
    }
  };

  const handleSetCapital = async () => {
    const value = Number(parseRaw(display));
    if (isNaN(value) || value <= 0) return;

    setLoading(true);
    try {
      await setCapital(value);
      onUpdate();
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    setLoading(true);
    try {
      await resetPortfolio();
      setResetOpen(false);
      onUpdate();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center gap-3 rounded-lg border bg-card p-3">
      <Settings className="h-4 w-4 text-muted-foreground" />
      <div className="flex flex-1 items-center gap-4 text-sm">
        <span className="text-muted-foreground">
          초기자본 <strong className="text-foreground">{formatKRW(initialCapital)}</strong>
        </span>
        <span className="text-muted-foreground">
          현금 <strong className="text-foreground">{formatKRW(cash)}</strong>
        </span>
      </div>
      <div className="flex items-center gap-2">
        <Input
          type="text"
          inputMode="numeric"
          value={display}
          onChange={handleAmountChange}
          className="h-8 w-40 text-sm"
          placeholder="자본금 (원)"
        />
        <Button
          variant="outline"
          size="sm"
          onClick={handleSetCapital}
          disabled={loading}
        >
          설정
        </Button>
        <Dialog open={resetOpen} onOpenChange={setResetOpen}>
          <DialogTrigger asChild>
            <Button variant="ghost" size="sm" disabled={loading}>
              <RotateCcw className="mr-1 h-3.5 w-3.5" />
              리셋
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>포트폴리오 리셋</DialogTitle>
              <DialogDescription>
                모든 포지션이 삭제되고 현금이 초기 자본금({formatKRW(initialCapital)})으로 복원됩니다.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={() => setResetOpen(false)}>
                취소
              </Button>
              <Button variant="destructive" onClick={handleReset} disabled={loading}>
                리셋 확인
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
}
