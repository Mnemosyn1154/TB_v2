"use client";

import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ChevronDown, ChevronUp, Trash2, Plus } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  snakeToTitle,
  extractNumericParams,
  extractStringParams,
  summarizeConfig,
} from "@/lib/strategy-utils";

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

const EMPTY_PAIR: Pair = {
  name: "",
  market: "KR",
  stock_a: "",
  stock_b: "",
  hedge_etf: "",
};

const EMPTY_CODE: UniverseCode = { code: "", market: "KR", name: "" };

interface StrategyCardProps {
  strategyKey: string;
  config: Record<string, unknown>;
  onToggle: (key: string) => void;
  onSave: (key: string, updated: Record<string, unknown>) => void;
  onDelete: (key: string) => void;
}

export function StrategyCard({
  strategyKey,
  config,
  onToggle,
  onSave,
  onDelete,
}: StrategyCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  // Editing state
  const [numericValues, setNumericValues] = useState<Record<string, number>>(
    {}
  );
  const [stringValues, setStringValues] = useState<Record<string, string>>({});
  const [pairs, setPairs] = useState<Pair[]>([]);
  const [codes, setCodes] = useState<UniverseCode[]>([]);

  const enabled = config.enabled as boolean;
  const typeName = config.type as string | undefined;
  const hasPairs = Array.isArray(config.pairs);
  const hasCodes = Array.isArray(config.universe_codes);

  const numericParams = extractNumericParams(config);
  const stringParams = extractStringParams(config);

  function initEditing() {
    const numInit: Record<string, number> = {};
    for (const p of numericParams) numInit[p.field] = p.value;
    setNumericValues(numInit);

    const strInit: Record<string, string> = {};
    for (const p of stringParams) strInit[p.field] = p.value;
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

  function toggleExpand() {
    if (!expanded) {
      initEditing();
    }
    setExpanded(!expanded);
  }

  function handleSave() {
    const updated = { ...config };
    for (const [k, v] of Object.entries(numericValues)) updated[k] = v;
    for (const [k, v] of Object.entries(stringValues)) updated[k] = v;
    if (hasPairs) updated.pairs = pairs;
    if (hasCodes) updated.universe_codes = codes;
    onSave(strategyKey, updated);
    setExpanded(false);
  }

  function handleCancel() {
    setExpanded(false);
  }

  function updatePair(idx: number, field: keyof Pair, value: string) {
    setPairs((prev) => {
      const next = prev.map((p) => ({ ...p }));
      (next[idx] as Record<string, string>)[field] = value;
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

  // Brief universe summary for collapsed view
  function universeSummary(): string | null {
    if (Array.isArray(config.pairs) && config.pairs.length > 0) {
      return `페어 ${config.pairs.length}개`;
    }
    if (
      Array.isArray(config.universe_codes) &&
      config.universe_codes.length > 0
    ) {
      return `유니버스 ${config.universe_codes.length}종목`;
    }
    const etfKeys = Object.entries(config).filter(
      ([k, v]) => typeof v === "string" && k.includes("etf")
    );
    if (etfKeys.length > 0) {
      return `ETF ${etfKeys.length}개`;
    }
    return null;
  }

  return (
    <>
      <Card
        className={cn("gap-0 py-0 overflow-hidden", !enabled && "opacity-60")}
      >
        {/* Header — always visible, click to expand/collapse */}
        <div
          className="flex items-center justify-between px-6 py-4 cursor-pointer select-none"
          onClick={toggleExpand}
        >
          <div className="flex items-center gap-3">
            {expanded ? (
              <ChevronUp className="h-4 w-4 shrink-0 text-muted-foreground" />
            ) : (
              <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
            )}
            <span className="font-semibold">{snakeToTitle(strategyKey)}</span>
            <Badge variant={enabled ? "default" : "secondary"}>
              {enabled ? "ON" : "OFF"}
            </Badge>
            {typeName && (
              <Badge variant="outline" className="text-xs">
                {typeName}
              </Badge>
            )}
          </div>
          <Switch
            checked={enabled}
            onClick={(e) => e.stopPropagation()}
            onCheckedChange={() => onToggle(strategyKey)}
          />
        </div>

        {/* Collapsed summary */}
        {!expanded && (
          <div className="px-6 pb-4 -mt-1">
            <p className="text-sm text-muted-foreground">
              {[summarizeConfig(config), universeSummary()]
                .filter(Boolean)
                .join(" · ")}
            </p>
          </div>
        )}

        {/* Expanded — inline editing */}
        {expanded && (
          <CardContent className="flex flex-col gap-5 border-t px-6 pt-5 pb-6">
            {/* Numeric parameters */}
            {numericParams.length > 0 && (
              <div className="flex flex-col gap-3">
                <h4 className="text-sm font-medium text-muted-foreground">
                  파라미터
                </h4>
                <div className="grid grid-cols-2 gap-3">
                  {numericParams.map((p) => (
                    <div key={p.field} className="flex flex-col gap-1.5">
                      <Label
                        htmlFor={`${strategyKey}-${p.field}`}
                        className="text-sm"
                      >
                        {p.label}
                      </Label>
                      <Input
                        id={`${strategyKey}-${p.field}`}
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
              </div>
            )}

            {/* String parameters (ETF codes etc.) */}
            {stringParams.length > 0 && (
              <div className="flex flex-col gap-3">
                <h4 className="text-sm font-medium text-muted-foreground">
                  코드 / 문자열
                </h4>
                <div className="grid grid-cols-2 gap-3">
                  {stringParams.map((p) => (
                    <div key={p.field} className="flex flex-col gap-1.5">
                      <Label
                        htmlFor={`${strategyKey}-${p.field}`}
                        className="text-sm"
                      >
                        {p.label}
                      </Label>
                      <Input
                        id={`${strategyKey}-${p.field}`}
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
                  onClick={() =>
                    setPairs((prev) => [...prev, { ...EMPTY_PAIR }])
                  }
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

            {/* Actions */}
            <div className="flex justify-between border-t pt-4">
              <Button
                variant="ghost"
                size="sm"
                className="text-destructive hover:text-destructive"
                onClick={() => setDeleteOpen(true)}
              >
                <Trash2 className="mr-1.5 h-3.5 w-3.5" />
                삭제
              </Button>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={handleCancel}>
                  취소
                </Button>
                <Button size="sm" onClick={handleSave}>
                  저장
                </Button>
              </div>
            </div>
          </CardContent>
        )}
      </Card>

      {/* Delete confirmation dialog */}
      <Dialog open={deleteOpen} onOpenChange={(v) => !v && setDeleteOpen(false)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>전략 삭제</DialogTitle>
            <DialogDescription>
              &apos;{strategyKey}&apos; 전략을 삭제하시겠습니까?
              settings.yaml에서 해당 설정이 제거됩니다. 이 작업은 되돌릴 수
              없습니다.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setDeleteOpen(false)}>
              취소
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                onDelete(strategyKey);
                setDeleteOpen(false);
              }}
            >
              삭제
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
