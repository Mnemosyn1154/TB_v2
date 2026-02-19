"use client";

import { useEffect, useState, useMemo } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
  ReferenceLine,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2 } from "lucide-react";
import { getBacktestPeerComparison } from "@/lib/api-client";
import { formatDateShort, formatPercent } from "@/lib/formatters";
import { CHART_COLORS } from "@/lib/constants";
import { downsample } from "@/lib/downsample";
import { cn } from "@/lib/utils";
import type { PeerComparisonData, PeerMetrics } from "@/types/backtest";
import type { ApiResponse } from "@/types/common";

interface PeerComparisonProps {
  startDate: string;
  endDate: string;
  equityCurve: { dates: string[]; values: number[] };
}

const PEER_LABELS: Record<string, string> = {
  strategy: "전략",
  kospi: "KOSPI",
  sp500: "S&P 500",
};

const PEER_COLORS: Record<string, string> = {
  strategy: CHART_COLORS.purple,
  kospi: CHART_COLORS.blue,
  sp500: CHART_COLORS.emerald,
};

const METRIC_LABELS: { key: keyof PeerMetrics; label: string }[] = [
  { key: "total_return", label: "총 수익률" },
  { key: "cagr", label: "CAGR" },
  { key: "mdd", label: "MDD" },
];

export function PeerComparison({
  startDate,
  endDate,
  equityCurve,
}: PeerComparisonProps) {
  const [data, setData] = useState<PeerComparisonData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function fetch() {
      setLoading(true);
      setError(null);
      try {
        const res = (await getBacktestPeerComparison({
          start_date: startDate,
          end_date: endDate,
          equity_curve: equityCurve,
        })) as ApiResponse<PeerComparisonData>;
        if (cancelled) return;
        if (res.error) {
          setError(res.error);
        } else {
          setData(res.data);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Unknown error");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    fetch();
    return () => {
      cancelled = true;
    };
  }, [startDate, endDate, equityCurve]);

  const chartData = useMemo(() => {
    if (!data) return [];
    const raw = data.dates.map((date, i) => ({
      date,
      strategy: data.strategy[i],
      kospi: data.kospi[i],
      sp500: data.sp500[i],
    }));
    return downsample(raw, 500);
  }, [data]);

  if (loading) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-semibold">
            피어그룹 비교
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex h-[300px] items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            <span className="ml-2 text-sm text-muted-foreground">
              벤치마크 데이터 로딩 중...
            </span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-semibold">
            피어그룹 비교
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex h-[100px] items-center justify-center text-sm text-muted-foreground">
            벤치마크 데이터를 불러올 수 없습니다
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!data) return null;

  const peers = ["strategy", "kospi", "sp500"] as const;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-semibold">피어그룹 비교</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-6">
        {/* Normalized performance chart */}
        <div className="h-[260px] md:h-[320px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis
                dataKey="date"
                tickFormatter={formatDateShort}
                tick={{ fontSize: 11 }}
                interval="preserveStartEnd"
              />
              <YAxis
                tick={{ fontSize: 11 }}
                width={50}
                tickFormatter={(v: number) => `${v}`}
              />
              <Tooltip
                formatter={(v, name) => [
                  `${Number(v).toFixed(1)}`,
                  PEER_LABELS[String(name)] ?? String(name),
                ]}
                labelFormatter={(label) => String(label)}
              />
              <Legend
                formatter={(value: string) => PEER_LABELS[value] ?? value}
              />
              <ReferenceLine
                y={100}
                stroke={CHART_COLORS.gray}
                strokeDasharray="5 5"
              />
              {peers.map((key) => (
                <Line
                  key={key}
                  type="monotone"
                  dataKey={key}
                  stroke={PEER_COLORS[key]}
                  strokeWidth={key === "strategy" ? 2.5 : 1.5}
                  dot={false}
                  strokeOpacity={key === "strategy" ? 1 : 0.7}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Comparison metrics table */}
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="py-2 text-left font-medium text-muted-foreground">
                  지표
                </th>
                {peers.map((key) => (
                  <th
                    key={key}
                    className="py-2 text-right font-medium text-muted-foreground"
                  >
                    <span className="flex items-center justify-end gap-1.5">
                      <span
                        className="inline-block h-2.5 w-2.5 rounded-full"
                        style={{ backgroundColor: PEER_COLORS[key] }}
                      />
                      {PEER_LABELS[key]}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {METRIC_LABELS.map(({ key, label }) => {
                // Find the best value for highlighting
                const values = peers.map((p) => data.metrics[p][key]);
                const bestIdx =
                  key === "mdd"
                    ? values.indexOf(Math.max(...values)) // MDD: closer to 0 is better
                    : values.indexOf(Math.max(...values)); // Return/CAGR: higher is better

                return (
                  <tr key={key} className="border-b border-border/50">
                    <td className="py-2.5 text-muted-foreground">{label}</td>
                    {peers.map((p, i) => {
                      const v = data.metrics[p][key];
                      const isBest = i === bestIdx;
                      return (
                        <td
                          key={p}
                          className={cn(
                            "py-2.5 text-right tabular-nums",
                            isBest && "font-semibold"
                          )}
                        >
                          <span
                            className={cn(
                              v > 0 && key !== "mdd" && "text-success",
                              v < 0 && "text-destructive",
                              key === "mdd" && "text-destructive"
                            )}
                          >
                            {formatPercent(v)}
                          </span>
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
              {/* Excess return row */}
              <tr>
                <td className="py-2.5 text-muted-foreground">
                  초과수익 (vs KOSPI)
                </td>
                {peers.map((p) => {
                  const excess = +(
                    data.metrics[p].total_return -
                    data.metrics.kospi.total_return
                  ).toFixed(2);
                  return (
                    <td key={p} className="py-2.5 text-right tabular-nums">
                      {p === "kospi" ? (
                        <span className="text-muted-foreground">-</span>
                      ) : (
                        <span
                          className={cn(
                            excess > 0 ? "text-success" : "text-destructive",
                            "font-semibold"
                          )}
                        >
                          {formatPercent(excess)}
                        </span>
                      )}
                    </td>
                  );
                })}
              </tr>
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
