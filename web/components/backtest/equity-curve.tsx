"use client";

import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  CartesianGrid,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatNumber, formatDateShort } from "@/lib/formatters";
import { CHART_COLORS } from "@/lib/constants";

interface EquityCurveProps {
  dates: string[];
  values: number[];
  initialCapital: number;
}

export function EquityCurve({ dates, values, initialCapital }: EquityCurveProps) {
  const data = dates.map((date, i) => ({ date, value: values[i] }));

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-semibold">에퀴티 커브</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data}>
              <defs>
                <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={CHART_COLORS.purple} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={CHART_COLORS.purple} stopOpacity={0} />
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
                tickFormatter={(v: number) => `${formatNumber(Math.round(v / 10000))}만`}
                tick={{ fontSize: 11 }}
                width={70}
              />
              <Tooltip
                formatter={(v) => [`₩${formatNumber(Math.round(Number(v)))}`, "자산"]}
                labelFormatter={(label) => String(label)}
              />
              <ReferenceLine
                y={initialCapital}
                stroke={CHART_COLORS.gray}
                strokeDasharray="5 5"
                label={{ value: "초기자본", position: "right", fontSize: 10 }}
              />
              <Area
                type="monotone"
                dataKey="value"
                stroke={CHART_COLORS.purple}
                fill="url(#equityGradient)"
                strokeWidth={2}
                dot={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
