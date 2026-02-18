"use client";

import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatDateShort, formatPercent } from "@/lib/formatters";
import { CHART_COLORS } from "@/lib/constants";

interface DrawdownChartProps {
  dates: string[];
  values: number[];
}

export function DrawdownChart({ dates, values }: DrawdownChartProps) {
  // Calculate drawdown from equity curve
  let peak = values[0];
  const data = dates.map((date, i) => {
    if (values[i] > peak) peak = values[i];
    const dd = peak > 0 ? ((values[i] - peak) / peak) * 100 : 0;
    return { date, drawdown: dd };
  });

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-semibold">드로다운</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[200px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data}>
              <defs>
                <linearGradient id="ddGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={CHART_COLORS.red} stopOpacity={0.4} />
                  <stop offset="95%" stopColor={CHART_COLORS.red} stopOpacity={0.05} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis
                dataKey="date"
                tickFormatter={formatDateShort}
                tick={{ fontSize: 11 }}
                interval="preserveStartEnd"
              />
              <YAxis
                tickFormatter={(v: number) => `${v.toFixed(0)}%`}
                tick={{ fontSize: 11 }}
                width={50}
                domain={["dataMin", 0]}
              />
              <Tooltip
                formatter={(v) => [formatPercent(Number(v)), "드로다운"]}
                labelFormatter={(label) => String(label)}
              />
              <Area
                type="monotone"
                dataKey="drawdown"
                stroke={CHART_COLORS.red}
                fill="url(#ddGradient)"
                strokeWidth={1.5}
                dot={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
