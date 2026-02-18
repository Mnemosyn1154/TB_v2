"use client";

import { useMemo } from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
  CartesianGrid,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CHART_COLORS } from "@/lib/constants";

interface PnlDistributionProps {
  pnlValues: number[];
}

function buildBins(values: number[], binCount = 20) {
  if (values.length === 0) return [];
  const min = Math.min(...values);
  const max = Math.max(...values);
  if (min === max) return [{ range: `${min.toFixed(0)}`, count: values.length, mid: min }];
  const step = (max - min) / binCount;
  const bins = Array.from({ length: binCount }, (_, i) => {
    const lo = min + step * i;
    const hi = lo + step;
    return { lo, hi, mid: (lo + hi) / 2, count: 0, range: `${(lo / 10000).toFixed(1)}~${(hi / 10000).toFixed(1)}만` };
  });
  for (const v of values) {
    const idx = Math.min(Math.floor((v - min) / step), binCount - 1);
    bins[idx].count++;
  }
  return bins.filter((b) => b.count > 0);
}

export function PnlDistribution({ pnlValues }: PnlDistributionProps) {
  const bins = useMemo(() => buildBins(pnlValues), [pnlValues]);

  if (bins.length === 0) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-semibold">손익 분포</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex h-[200px] items-center justify-center text-sm text-muted-foreground">
            데이터가 없습니다
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-semibold">손익 분포</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[180px] md:h-[200px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={bins}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis
                dataKey="range"
                tick={{ fontSize: 10 }}
                interval="preserveStartEnd"
              />
              <YAxis tick={{ fontSize: 11 }} allowDecimals={false} width={30} />
              <Tooltip
                formatter={(v) => [`${v}건`, "거래 수"]}
                labelFormatter={(label) => `구간: ${String(label)}`}
              />
              <Bar dataKey="count" radius={[2, 2, 0, 0]}>
                {bins.map((b, i) => (
                  <Cell
                    key={i}
                    fill={b.mid >= 0 ? CHART_COLORS.emerald : CHART_COLORS.red}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
