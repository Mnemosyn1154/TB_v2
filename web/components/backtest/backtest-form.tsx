"use client";

import { useState, useEffect, useCallback } from "react";
import { Play, Loader2, ChevronDown, ChevronRight, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { getBacktestPairs, getSettings, previewUniverse } from "@/lib/api-client";
import { formatNumber } from "@/lib/formatters";
import { snakeToTitle } from "@/lib/strategy-utils";
import type { BacktestRequest, StrategyOverrides, UniverseStock } from "@/types/backtest";
import type { ApiResponse } from "@/types/common";

interface BacktestFormProps {
  strategies: string[];
  onRun: (params: BacktestRequest) => void;
  loading: boolean;
}

export function BacktestForm({ strategies, onRun, loading }: BacktestFormProps) {
  const [strategy, setStrategy] = useState("");
  const [startDate, setStartDate] = useState("2024-01-01");
  const [endDate, setEndDate] = useState("2025-12-31");
  const [initialCapital, setInitialCapital] = useState(50_000_000);
  const [pairName, setPairName] = useState<string | null>(null);
  const [pairs, setPairs] = useState<string[]>([]);

  // Strategy overrides state (quant_factor defaults)
  const [overrides, setOverrides] = useState<StrategyOverrides>({
    top_n: 20,
    rebalance_months: 1,
    lookback_days: 252,
    momentum_days: 126,
    volatility_days: 60,
    weight_value: 0.3,
    weight_quality: 0.3,
    weight_momentum: 0.4,
    absolute_momentum_filter: true,
    abs_mom_threshold: 0,
  });
  const [defaultOverrides, setDefaultOverrides] = useState<StrategyOverrides>({});

  // Load defaults from settings.yaml
  useEffect(() => {
    getSettings().then((res: ApiResponse<unknown>) => {
      if (!res.data) return;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const cfg = (res.data as any)?.strategies?.quant_factor;
      if (!cfg) return;
      const defaults: StrategyOverrides = {
        top_n: (cfg.top_n as number) ?? 20,
        rebalance_months: (cfg.rebalance_months as number) ?? 1,
        lookback_days: (cfg.lookback_days as number) ?? 252,
        momentum_days: (cfg.momentum_days as number) ?? 126,
        volatility_days: (cfg.volatility_days as number) ?? 60,
        weight_value: (cfg.weight_value as number) ?? 0.3,
        weight_quality: (cfg.weight_quality as number) ?? 0.3,
        weight_momentum: (cfg.weight_momentum as number) ?? 0.4,
        absolute_momentum_filter: (cfg.absolute_momentum_filter as boolean) ?? true,
        abs_mom_threshold: (cfg.abs_mom_threshold as number) ?? 0,
      };
      setOverrides(defaults);
      setDefaultOverrides(defaults);
    }).catch(() => {});
  }, []);

  // Universe experiment state
  const [universeOpen, setUniverseOpen] = useState(false);
  const [minPrice, setMinPrice] = useState(10);
  const [minVolume, setMinVolume] = useState(10_000_000);
  const [minCap, setMinCap] = useState(5_000_000_000);
  const [previewStocks, setPreviewStocks] = useState<UniverseStock[] | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);

  // Select first strategy when list loads
  useEffect(() => {
    if (strategies.length > 0 && !strategies.includes(strategy)) {
      setStrategy(strategies[0]);
    }
  }, [strategies, strategy]);

  // Reset universe preview when strategy changes
  useEffect(() => {
    setPreviewStocks(null);
    setPreviewError(null);
  }, [strategy]);

  const fetchPairs = useCallback(async (strat: string) => {
    try {
      const res = await getBacktestPairs(strat);
      const data = (res as { data: string[] | null }).data;
      setPairs(data ?? []);
      setPairName(null);
    } catch {
      setPairs([]);
    }
  }, []);

  useEffect(() => {
    if (strategy) fetchPairs(strategy);
  }, [strategy, fetchPairs]);

  const handlePreview = async () => {
    setPreviewLoading(true);
    setPreviewError(null);
    try {
      const res = (await previewUniverse({
        min_price: minPrice,
        min_avg_daily_volume: minVolume,
        min_market_cap: minCap,
      })) as ApiResponse<UniverseStock[]>;
      if (res.error) {
        setPreviewError(res.error);
      } else {
        setPreviewStocks(res.data);
      }
    } catch {
      setPreviewError("프리뷰 요청 실패");
    } finally {
      setPreviewLoading(false);
    }
  };

  const buildOverrides = (): StrategyOverrides | undefined => {
    if (!isQuantFactor) return undefined;
    const changed: StrategyOverrides = {};
    for (const key of Object.keys(overrides) as (keyof StrategyOverrides)[]) {
      if (overrides[key] !== defaultOverrides[key]) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (changed as any)[key] = overrides[key];
      }
    }
    return Object.keys(changed).length > 0 ? changed : undefined;
  };

  const handleSubmit = () => {
    onRun({
      strategy,
      start_date: startDate,
      end_date: endDate,
      initial_capital: initialCapital,
      pair_name: pairName,
      universe_codes: previewStocks ?? undefined,
      strategy_overrides: buildOverrides(),
    });
  };

  const isQuantFactor = strategy === "quant_factor";

  const formatLargeNumber = (n: number) => {
    if (n >= 1e12) return `${(n / 1e12).toFixed(1)}T`;
    if (n >= 1e9) return `${(n / 1e9).toFixed(1)}B`;
    if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
    return formatNumber(n);
  };

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
          {/* Strategy */}
          <div className="col-span-2 md:col-span-1">
            <Label className="mb-1.5 text-xs">전략</Label>
            <Select value={strategy} onValueChange={setStrategy}>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {strategies.map((key) => (
                  <SelectItem key={key} value={key}>
                    {snakeToTitle(key)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Pair (optional) */}
          {pairs.length > 0 && (
            <div>
              <Label className="mb-1.5 text-xs">페어</Label>
              <Select
                value={pairName ?? "__all__"}
                onValueChange={(v) =>
                  setPairName(v === "__all__" ? null : v)
                }
              >
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__all__">전체</SelectItem>
                  {pairs.map((p) => (
                    <SelectItem key={p} value={p}>
                      {p}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {/* Start Date */}
          <div>
            <Label className="mb-1.5 text-xs">시작일</Label>
            <Input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
          </div>

          {/* End Date */}
          <div>
            <Label className="mb-1.5 text-xs">종료일</Label>
            <Input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
          </div>

          {/* Initial Capital */}
          <div>
            <Label className="mb-1.5 text-xs">초기 자본금</Label>
            <Input
              type="number"
              value={initialCapital}
              onChange={(e) => setInitialCapital(Number(e.target.value))}
              step={1_000_000}
              min={1_000_000}
            />
            <span className="text-xs text-muted-foreground">
              {formatNumber(initialCapital)}원
            </span>
          </div>

          {/* Run Button */}
          <div>
            <Label className="mb-1.5 text-xs invisible">실행</Label>
            <Button
              onClick={handleSubmit}
              disabled={loading}
              className="w-full"
            >
              {loading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Play className="mr-2 h-4 w-4" />
              )}
              {loading ? "실행 중..." : "백테스트 실행"}
            </Button>
          </div>
        </div>

        {/* Universe Experiment — quant_factor only */}
        {isQuantFactor && (
          <div className="mt-4 border-t pt-4">
            <button
              type="button"
              className="flex items-center gap-1 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
              onClick={() => setUniverseOpen(!universeOpen)}
            >
              {universeOpen ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
              유니버스 실험
              {previewStocks && (
                <span className="ml-2 text-xs text-primary">
                  ({previewStocks.length}개 종목 적용)
                </span>
              )}
            </button>

            {universeOpen && (
              <div className="mt-3 space-y-4">
                {/* Strategy Parameters */}
                <div>
                  <h4 className="text-xs font-medium text-muted-foreground mb-2">전략 파라미터</h4>
                  <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                    <div>
                      <Label className="mb-1 text-xs">종목 수 (top_n)</Label>
                      <Input type="number" value={overrides.top_n} min={1} step={1}
                        onChange={(e) => setOverrides({ ...overrides, top_n: Number(e.target.value) })} />
                    </div>
                    <div>
                      <Label className="mb-1 text-xs">리밸런싱 주기 (개월)</Label>
                      <Input type="number" value={overrides.rebalance_months} min={1} step={1}
                        onChange={(e) => setOverrides({ ...overrides, rebalance_months: Number(e.target.value) })} />
                    </div>
                    <div>
                      <Label className="mb-1 text-xs">데이터 기간 (일)</Label>
                      <Input type="number" value={overrides.lookback_days} min={1} step={1}
                        onChange={(e) => setOverrides({ ...overrides, lookback_days: Number(e.target.value) })} />
                    </div>
                    <div>
                      <Label className="mb-1 text-xs">모멘텀 기간 (일)</Label>
                      <Input type="number" value={overrides.momentum_days} min={1} step={1}
                        onChange={(e) => setOverrides({ ...overrides, momentum_days: Number(e.target.value) })} />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3 md:grid-cols-4 mt-3">
                    <div>
                      <Label className="mb-1 text-xs">가치 가중치</Label>
                      <Input type="number" value={overrides.weight_value} min={0} max={1} step={0.05}
                        onChange={(e) => setOverrides({ ...overrides, weight_value: Number(e.target.value) })} />
                    </div>
                    <div>
                      <Label className="mb-1 text-xs">퀄리티 가중치</Label>
                      <Input type="number" value={overrides.weight_quality} min={0} max={1} step={0.05}
                        onChange={(e) => setOverrides({ ...overrides, weight_quality: Number(e.target.value) })} />
                    </div>
                    <div>
                      <Label className="mb-1 text-xs">모멘텀 가중치</Label>
                      <Input type="number" value={overrides.weight_momentum} min={0} max={1} step={0.05}
                        onChange={(e) => setOverrides({ ...overrides, weight_momentum: Number(e.target.value) })} />
                    </div>
                    <div>
                      <Label className="mb-1 text-xs">변동성 기간 (일)</Label>
                      <Input type="number" value={overrides.volatility_days} min={1} step={1}
                        onChange={(e) => setOverrides({ ...overrides, volatility_days: Number(e.target.value) })} />
                    </div>
                  </div>
                  <div className="flex items-center gap-4 mt-3">
                    <label className="flex items-center gap-2 text-xs cursor-pointer">
                      <input type="checkbox" checked={overrides.absolute_momentum_filter}
                        onChange={(e) => setOverrides({ ...overrides, absolute_momentum_filter: e.target.checked })}
                        className="rounded border-border" />
                      절대 모멘텀 필터
                    </label>
                    <div className="flex items-center gap-2">
                      <Label className="text-xs whitespace-nowrap">임계값</Label>
                      <Input type="number" value={overrides.abs_mom_threshold} step={0.01}
                        className="w-24"
                        onChange={(e) => setOverrides({ ...overrides, abs_mom_threshold: Number(e.target.value) })} />
                    </div>
                    {(() => {
                      const sum = (overrides.weight_value ?? 0) + (overrides.weight_quality ?? 0) + (overrides.weight_momentum ?? 0);
                      const isOne = Math.abs(sum - 1) < 0.001;
                      return (
                        <span className={`text-xs ml-auto ${isOne ? "text-muted-foreground" : "text-destructive font-medium"}`}>
                          가중치 합: {sum.toFixed(2)}{!isOne && " ⚠ 합이 1이 아닙니다"}
                        </span>
                      );
                    })()}
                  </div>
                </div>

                {/* Universe Filter */}
                <div>
                  <h4 className="text-xs font-medium text-muted-foreground mb-2">유니버스 필터</h4>
                </div>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <Label className="mb-1.5 text-xs">최소 주가 ($)</Label>
                    <Input
                      type="number"
                      value={minPrice}
                      onChange={(e) => setMinPrice(Number(e.target.value))}
                      min={0}
                      step={1}
                    />
                  </div>
                  <div>
                    <Label className="mb-1.5 text-xs">최소 거래대금 (일평균, $)</Label>
                    <Input
                      type="number"
                      value={minVolume}
                      onChange={(e) => setMinVolume(Number(e.target.value))}
                      min={0}
                      step={1_000_000}
                    />
                  </div>
                  <div>
                    <Label className="mb-1.5 text-xs">최소 시가총액 ($)</Label>
                    <Input
                      type="number"
                      value={minCap}
                      onChange={(e) => setMinCap(Number(e.target.value))}
                      min={0}
                      step={1_000_000_000}
                    />
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handlePreview}
                    disabled={previewLoading}
                  >
                    {previewLoading ? (
                      <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Search className="mr-2 h-3.5 w-3.5" />
                    )}
                    {previewLoading ? "조회 중 (30~60초)..." : "프리뷰 조회"}
                  </Button>
                  {previewStocks && (
                    <span className="text-sm text-muted-foreground">
                      {previewStocks.length}개 종목
                    </span>
                  )}
                  {previewError && (
                    <span className="text-sm text-destructive">{previewError}</span>
                  )}
                </div>

                {previewStocks && previewStocks.length > 0 && (
                  <div className="max-h-64 overflow-auto rounded border">
                    <table className="w-full text-xs">
                      <thead className="bg-muted/50 sticky top-0">
                        <tr>
                          <th className="px-3 py-1.5 text-left font-medium">티커</th>
                          <th className="px-3 py-1.5 text-left font-medium">이름</th>
                          <th className="px-3 py-1.5 text-left font-medium">섹터</th>
                          <th className="px-3 py-1.5 text-right font-medium">시가총액</th>
                          <th className="px-3 py-1.5 text-right font-medium">현재가</th>
                        </tr>
                      </thead>
                      <tbody>
                        {previewStocks.map((s) => (
                          <tr key={s.code} className="border-t border-border/50">
                            <td className="px-3 py-1 font-mono">{s.code}</td>
                            <td className="px-3 py-1 truncate max-w-[160px]">{s.name}</td>
                            <td className="px-3 py-1 text-muted-foreground">{s.sector}</td>
                            <td className="px-3 py-1 text-right font-mono">
                              {formatLargeNumber(s.market_cap)}
                            </td>
                            <td className="px-3 py-1 text-right font-mono">
                              ${s.last_price.toFixed(2)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
