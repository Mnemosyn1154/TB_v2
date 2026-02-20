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
import { getBacktestPairs, previewUniverse } from "@/lib/api-client";
import { formatNumber } from "@/lib/formatters";
import { snakeToTitle } from "@/lib/strategy-utils";
import type { BacktestRequest, UniverseStock } from "@/types/backtest";
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

  const handleSubmit = () => {
    onRun({
      strategy,
      start_date: startDate,
      end_date: endDate,
      initial_capital: initialCapital,
      pair_name: pairName,
      universe_codes: previewStocks ?? undefined,
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
              <div className="mt-3 space-y-3">
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
