"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

const MONTH_LABELS = [
  "1월",
  "2월",
  "3월",
  "4월",
  "5월",
  "6월",
  "7월",
  "8월",
  "9월",
  "10월",
  "11월",
  "12월",
];

interface MonthlyHeatmapProps {
  /** year labels (rows) */
  index: number[];
  /** month labels (columns) — e.g. ["01","02",...,"12"] */
  columns: string[];
  /** data[row][col] = monthly return as decimal */
  data: number[][];
}

function getCellColor(value: number | null | undefined): string {
  if (value == null || isNaN(value)) return "bg-muted";
  const pct = value * 100;
  if (pct > 5) return "bg-emerald-600 text-white";
  if (pct > 2) return "bg-emerald-500 text-white";
  if (pct > 0) return "bg-emerald-300 dark:bg-emerald-800 text-emerald-900 dark:text-emerald-100";
  if (pct === 0) return "bg-muted";
  if (pct > -2) return "bg-red-300 dark:bg-red-900 text-red-900 dark:text-red-100";
  if (pct > -5) return "bg-red-500 text-white";
  return "bg-red-600 text-white";
}

export function MonthlyHeatmap({ index, columns, data }: MonthlyHeatmapProps) {
  if (!data || data.length === 0) return null;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-semibold">월별 수익률</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-xs">
            <thead>
              <tr>
                <th className="px-2 py-1.5 text-left font-medium text-muted-foreground">
                  연도
                </th>
                {(columns.length > 0 ? columns : MONTH_LABELS).map((m, i) => (
                  <th
                    key={i}
                    className="px-1 py-1.5 text-center font-medium text-muted-foreground"
                  >
                    {MONTH_LABELS[i] ?? m}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {index.map((year, rowIdx) => (
                <tr key={year}>
                  <td className="px-2 py-1 font-medium font-mono text-muted-foreground">
                    {year}
                  </td>
                  {(data[rowIdx] ?? []).map((val, colIdx) => {
                    const pct =
                      val != null && !isNaN(val) ? (val * 100).toFixed(1) : "-";
                    return (
                      <td key={colIdx} className="px-0.5 py-0.5">
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <div
                              className={cn(
                                "flex h-8 items-center justify-center rounded text-[11px] font-mono font-medium",
                                getCellColor(val)
                              )}
                            >
                              {pct !== "-" ? `${pct}%` : "-"}
                            </div>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p className="text-xs">
                              {year}년 {MONTH_LABELS[colIdx]}: {pct}%
                            </p>
                          </TooltipContent>
                        </Tooltip>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
