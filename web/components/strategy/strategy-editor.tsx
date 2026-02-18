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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  snakeToTitle,
  extractNumericParams,
  extractStringParams,
} from "@/lib/strategy-utils";
import { Plus, Trash2 } from "lucide-react";

interface Pair {
  name: string;
  market: string;
  stock_a: string;
  stock_b: string;
  hedge_etf: string;
  exchange_a?: string;
  exchange_b?: string;
  exchange_hedge?: string;
}

interface UniverseCode {
  code: string;
  market: string;
  name: string;
  exchange?: string;
}

interface StrategyEditorProps {
  strategyKey: string | null;
  config: Record<string, unknown> | null;
  onSave: (key: string, updated: Record<string, unknown>) => void;
  onClose: () => void;
}

const EMPTY_PAIR: Pair = {
  name: "",
  market: "KR",
  stock_a: "",
  stock_b: "",
  hedge_etf: "",
};

const EMPTY_CODE: UniverseCode = { code: "", market: "KR", name: "" };

export function StrategyEditor({
  strategyKey,
  config,
  onSave,
  onClose,
}: StrategyEditorProps) {
  const [numericValues, setNumericValues] = useState<Record<string, number>>(
    {}
  );
  const [stringValues, setStringValues] = useState<Record<string, string>>({});
  const [pairs, setPairs] = useState<Pair[]>([]);
  const [codes, setCodes] = useState<UniverseCode[]>([]);
  const open = strategyKey !== null && config !== null;

  const hasPairs = config ? Array.isArray(config.pairs) : false;
  const hasCodes = config ? Array.isArray(config.universe_codes) : false;
  const isComplex = hasPairs || hasCodes;

  useEffect(() => {
    if (strategyKey && config) {
      const numParams = extractNumericParams(config);
      const numInit: Record<string, number> = {};
      for (const p of numParams) numInit[p.field] = p.value;
      setNumericValues(numInit);

      const strParams = extractStringParams(config);
      const strInit: Record<string, string> = {};
      for (const p of strParams) strInit[p.field] = p.value;
      setStringValues(strInit);

      if (Array.isArray(config.pairs)) {
        setPairs((config.pairs as Pair[]).map((p) => ({ ...p })));
      } else {
        setPairs([]);
      }

      if (Array.isArray(config.universe_codes)) {
        setCodes(
          (config.universe_codes as UniverseCode[]).map((c) => ({ ...c }))
        );
      } else {
        setCodes([]);
      }
    }
  }, [strategyKey, config]);

  if (!strategyKey || !config) return null;

  const numericParams = extractNumericParams(config);
  const stringParams = extractStringParams(config);

  function handleSave() {
    if (!strategyKey || !config) return;
    const updated = { ...config };
    for (const [k, v] of Object.entries(numericValues)) updated[k] = v;
    for (const [k, v] of Object.entries(stringValues)) updated[k] = v;
    if (hasPairs) updated.pairs = pairs;
    if (hasCodes) updated.universe_codes = codes;
    onSave(strategyKey, updated);
  }

  function updatePair(idx: number, field: keyof Pair, value: string) {
    setPairs((prev) => {
      const next = prev.map((p) => ({ ...p }));
      (next[idx] as Record<string, string>)[field] = value;
      // Clear exchange fields when switching to KR
      if (field === "market" && value === "KR") {
        delete (next[idx] as Record<string, string | undefined>).exchange_a;
        delete (next[idx] as Record<string, string | undefined>).exchange_b;
        delete (next[idx] as Record<string, string | undefined>).exchange_hedge;
      }
      return next;
    });
  }

  function updateCode(idx: number, field: keyof UniverseCode, value: string) {
    setCodes((prev) => {
      const next = prev.map((c) => ({ ...c }));
      (next[idx] as Record<string, string>)[field] = value;
      if (field === "market" && value === "KR") {
        delete (next[idx] as Record<string, string | undefined>).exchange;
      }
      return next;
    });
  }

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className={isComplex ? "max-w-2xl" : "max-w-md"}>
        <DialogHeader>
          <DialogTitle>{snakeToTitle(strategyKey)} 파라미터</DialogTitle>
        </DialogHeader>
        <div className="flex flex-col gap-4 py-2 max-h-[70vh] overflow-y-auto">
          {/* Numeric parameters */}
          {numericParams.length > 0 && (
            <div className="flex flex-col gap-3">
              {numericParams.map((p) => (
                <div key={p.field} className="flex flex-col gap-1.5">
                  <Label htmlFor={p.field} className="text-sm">
                    {p.label}
                  </Label>
                  <Input
                    id={p.field}
                    type="number"
                    step="any"
                    value={numericValues[p.field] ?? ""}
                    onChange={(e) =>
                      setNumericValues((prev) => ({
                        ...prev,
                        [p.field]: parseFloat(e.target.value) || 0,
                      }))
                    }
                  />
                </div>
              ))}
            </div>
          )}

          {/* String parameters (ETF codes etc.) */}
          {stringParams.length > 0 && (
            <div className="flex flex-col gap-3">
              <h4 className="text-sm font-medium text-muted-foreground">
                코드 / 문자열
              </h4>
              {stringParams.map((p) => (
                <div key={p.field} className="flex flex-col gap-1.5">
                  <Label htmlFor={p.field} className="text-sm">
                    {p.label}
                  </Label>
                  <Input
                    id={p.field}
                    type="text"
                    value={stringValues[p.field] ?? ""}
                    onChange={(e) =>
                      setStringValues((prev) => ({
                        ...prev,
                        [p.field]: e.target.value,
                      }))
                    }
                  />
                </div>
              ))}
            </div>
          )}

          {/* Pairs editing (stat_arb) */}
          {hasPairs && (
            <div className="flex flex-col gap-2">
              <h4 className="text-sm font-medium text-muted-foreground">
                페어
              </h4>
              {pairs.map((pair, idx) => (
                <div
                  key={idx}
                  className="grid grid-cols-[1fr_auto] gap-2 rounded-md border p-3"
                >
                  <div className="grid grid-cols-2 gap-2">
                    <Input
                      placeholder="이름"
                      value={pair.name}
                      onChange={(e) => updatePair(idx, "name", e.target.value)}
                    />
                    <Select
                      value={pair.market}
                      onValueChange={(v) => updatePair(idx, "market", v)}
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="KR">KR</SelectItem>
                        <SelectItem value="US">US</SelectItem>
                      </SelectContent>
                    </Select>
                    <Input
                      placeholder="종목 A"
                      value={pair.stock_a}
                      onChange={(e) =>
                        updatePair(idx, "stock_a", e.target.value)
                      }
                    />
                    <Input
                      placeholder="종목 B"
                      value={pair.stock_b}
                      onChange={(e) =>
                        updatePair(idx, "stock_b", e.target.value)
                      }
                    />
                    <Input
                      placeholder="헤지 ETF"
                      value={pair.hedge_etf}
                      onChange={(e) =>
                        updatePair(idx, "hedge_etf", e.target.value)
                      }
                    />
                    {pair.market === "US" && (
                      <>
                        <Input
                          placeholder="거래소 A (예: NAS)"
                          value={pair.exchange_a ?? ""}
                          onChange={(e) =>
                            updatePair(idx, "exchange_a", e.target.value)
                          }
                        />
                        <Input
                          placeholder="거래소 B"
                          value={pair.exchange_b ?? ""}
                          onChange={(e) =>
                            updatePair(idx, "exchange_b", e.target.value)
                          }
                        />
                        <Input
                          placeholder="거래소 헤지"
                          value={pair.exchange_hedge ?? ""}
                          onChange={(e) =>
                            updatePair(idx, "exchange_hedge", e.target.value)
                          }
                        />
                      </>
                    )}
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="self-start text-destructive"
                    onClick={() =>
                      setPairs((prev) => prev.filter((_, i) => i !== idx))
                    }
                  >
                    <Trash2 className="size-4" />
                  </Button>
                </div>
              ))}
              <Button
                variant="outline"
                size="sm"
                className="self-start"
                onClick={() => setPairs((prev) => [...prev, { ...EMPTY_PAIR }])}
              >
                <Plus className="size-4 mr-1" />
                페어 추가
              </Button>
            </div>
          )}

          {/* Universe codes editing (quant_factor) */}
          {hasCodes && (
            <div className="flex flex-col gap-2">
              <h4 className="text-sm font-medium text-muted-foreground">
                유니버스 종목
              </h4>
              {codes.map((item, idx) => (
                <div
                  key={idx}
                  className="grid grid-cols-[1fr_auto] gap-2 items-center"
                >
                  <div className="grid grid-cols-3 gap-2">
                    <Input
                      placeholder="코드"
                      value={item.code}
                      onChange={(e) => updateCode(idx, "code", e.target.value)}
                    />
                    <Select
                      value={item.market}
                      onValueChange={(v) => updateCode(idx, "market", v)}
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="KR">KR</SelectItem>
                        <SelectItem value="US">US</SelectItem>
                      </SelectContent>
                    </Select>
                    <Input
                      placeholder="종목명"
                      value={item.name}
                      onChange={(e) => updateCode(idx, "name", e.target.value)}
                    />
                    {item.market === "US" && (
                      <Input
                        placeholder="거래소 (예: NAS)"
                        value={item.exchange ?? ""}
                        onChange={(e) =>
                          updateCode(idx, "exchange", e.target.value)
                        }
                        className="col-span-3"
                      />
                    )}
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="text-destructive"
                    onClick={() =>
                      setCodes((prev) => prev.filter((_, i) => i !== idx))
                    }
                  >
                    <Trash2 className="size-4" />
                  </Button>
                </div>
              ))}
              <Button
                variant="outline"
                size="sm"
                className="self-start"
                onClick={() =>
                  setCodes((prev) => [...prev, { ...EMPTY_CODE }])
                }
              >
                <Plus className="size-4 mr-1" />
                종목 추가
              </Button>
            </div>
          )}
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
