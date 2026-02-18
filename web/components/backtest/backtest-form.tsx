"use client";

import { useState, useEffect, useCallback } from "react";
import { Play, Loader2 } from "lucide-react";
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
import { getBacktestPairs } from "@/lib/api-client";
import { formatNumber } from "@/lib/formatters";
import { snakeToTitle } from "@/lib/strategy-utils";
import type { BacktestRequest } from "@/types/backtest";

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

  // Select first strategy when list loads
  useEffect(() => {
    if (strategies.length > 0 && !strategies.includes(strategy)) {
      setStrategy(strategies[0]);
    }
  }, [strategies, strategy]);

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

  const handleSubmit = () => {
    onRun({
      strategy,
      start_date: startDate,
      end_date: endDate,
      initial_capital: initialCapital,
      pair_name: pairName,
    });
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
          <div className="flex items-end">
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
      </CardContent>
    </Card>
  );
}
