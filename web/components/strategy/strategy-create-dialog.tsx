"use client";

import { useState } from "react";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const STRATEGY_TYPES = [
  { value: "stat_arb", label: "Stat Arb (통계적 차익거래)" },
  { value: "dual_momentum", label: "Dual Momentum (듀얼 모멘텀)" },
  { value: "quant_factor", label: "Quant Factor (퀀트 팩터)" },
] as const;

interface StrategyCreateDialogProps {
  onCreated: () => void;
}

export function StrategyCreateDialog({ onCreated }: StrategyCreateDialogProps) {
  const [open, setOpen] = useState(false);
  const [type, setType] = useState("");
  const [key, setKey] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function reset() {
    setType("");
    setKey("");
    setError(null);
    setLoading(false);
  }

  async function handleCreate() {
    setError(null);

    if (!type || !key) {
      setError("타입과 이름을 모두 입력하세요.");
      return;
    }

    if (!/^[a-z][a-z0-9_]*$/.test(key)) {
      setError("이름은 영문 소문자, 숫자, 언더스코어만 사용 가능합니다 (snake_case).");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch("/api/settings/strategies", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key, type }),
      });
      const json = await res.json();

      if (!res.ok) {
        setError(json.error ?? "생성 실패");
        return;
      }

      setOpen(false);
      reset();
      onCreated();
    } catch {
      setError("네트워크 오류");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        setOpen(v);
        if (!v) reset();
      }}
    >
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <Plus className="mr-1.5 h-3.5 w-3.5" />
          새 전략 추가
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>새 전략 인스턴스 생성</DialogTitle>
          <DialogDescription>
            기존 전략 타입을 기반으로 새 인스턴스를 생성합니다. 생성 후 파라미터를
            편집할 수 있습니다.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-4 py-2">
          <div className="flex flex-col gap-2">
            <Label>전략 타입</Label>
            <Select value={type} onValueChange={setType}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="타입 선택" />
              </SelectTrigger>
              <SelectContent>
                {STRATEGY_TYPES.map((t) => (
                  <SelectItem key={t.value} value={t.value}>
                    {t.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-2">
            <Label>인스턴스 이름 (snake_case)</Label>
            <Input
              placeholder="예: stat_arb_crypto"
              value={key}
              onChange={(e) => setKey(e.target.value)}
            />
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => setOpen(false)}>
            취소
          </Button>
          <Button onClick={handleCreate} disabled={loading}>
            {loading ? "생성 중..." : "생성"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
