"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { CHART_COLORS } from "@/lib/constants";
import type { BenchmarkData } from "@/types/benchmark";

interface BenchmarkChartProps {
  data: BenchmarkData;
}

export function BenchmarkChart({ data }: BenchmarkChartProps) {
  const chartData = data.dates.map((date, i) => ({
    date,
    portfolio: data.portfolio[i],
    kospi: data.kospi[i],
    sp500: data.sp500[i],
  }));

  if (chartData.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center rounded-lg border border-dashed text-sm text-muted-foreground">
        차트 데이터가 없습니다
      </div>
    );
  }

  const allValues = chartData.flatMap((d) =>
    [d.portfolio, d.kospi, d.sp500].filter((v): v is number => v != null)
  );
  const yMin = Math.floor(Math.min(...allValues) - 2);
  const yMax = Math.ceil(Math.max(...allValues) + 2);

  return (
    <div className="h-72 w-full md:h-80">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-border/50" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11 }}
            tickFormatter={(v: string) => v.slice(5)}
            className="text-muted-foreground"
          />
          <YAxis
            domain={[yMin, yMax]}
            tick={{ fontSize: 11 }}
            tickFormatter={(v: number) => `${v}`}
            className="text-muted-foreground"
          />
          <RechartsTooltip
            contentStyle={{
              backgroundColor: "hsl(var(--card))",
              border: "1px solid hsl(var(--border))",
              borderRadius: "8px",
              fontSize: 12,
            }}
            labelFormatter={(label) => String(label)}
            formatter={(value, name) => [
              `${Number(value).toFixed(1)}`,
              name === "portfolio"
                ? "포트폴리오"
                : name === "kospi"
                  ? "KOSPI"
                  : "S&P500",
            ]}
          />
          <Legend
            formatter={(value: string) =>
              value === "portfolio"
                ? "포트폴리오"
                : value === "kospi"
                  ? "KOSPI"
                  : "S&P500"
            }
          />
          <Line
            type="monotone"
            dataKey="portfolio"
            stroke={CHART_COLORS.purple}
            strokeWidth={2.5}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="kospi"
            stroke={CHART_COLORS.blue}
            strokeWidth={1.5}
            strokeDasharray="5 5"
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="sp500"
            stroke={CHART_COLORS.emerald}
            strokeWidth={1.5}
            strokeDasharray="5 5"
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
