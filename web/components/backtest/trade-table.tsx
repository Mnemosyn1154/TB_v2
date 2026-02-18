"use client";

import { useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { formatKRW, formatPercent, formatDate } from "@/lib/formatters";
import type { Trade } from "@/types/backtest";

type SortKey = "date" | "pnl" | "pnl_pct" | "holding_days";

interface TradeTableProps {
  trades: Trade[];
}

export function TradeTable({ trades }: TradeTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("date");
  const [sortAsc, setSortAsc] = useState(false);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortAsc(!sortAsc);
    } else {
      setSortKey(key);
      setSortAsc(false);
    }
  };

  const sorted = [...trades].sort((a, b) => {
    let cmp = 0;
    switch (sortKey) {
      case "date":
        cmp = a.date.localeCompare(b.date);
        break;
      case "pnl":
        cmp = (a.pnl ?? 0) - (b.pnl ?? 0);
        break;
      case "pnl_pct":
        cmp = (a.pnl_pct ?? 0) - (b.pnl_pct ?? 0);
        break;
      case "holding_days":
        cmp = (a.holding_days ?? 0) - (b.holding_days ?? 0);
        break;
    }
    return sortAsc ? cmp : -cmp;
  });

  const sortIndicator = (key: SortKey) =>
    sortKey === key ? (sortAsc ? " ▲" : " ▼") : "";

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-semibold">
          거래 내역 ({trades.length}건)
        </CardTitle>
      </CardHeader>
      <CardContent>
        {trades.length === 0 ? (
          <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">
            거래 내역이 없습니다
          </div>
        ) : (
          <div className="overflow-x-auto max-h-[400px] overflow-y-auto rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead
                    className="cursor-pointer select-none"
                    onClick={() => handleSort("date")}
                  >
                    날짜{sortIndicator("date")}
                  </TableHead>
                  <TableHead>전략</TableHead>
                  <TableHead>종목</TableHead>
                  <TableHead>방향</TableHead>
                  <TableHead className="text-right">가격</TableHead>
                  <TableHead className="text-right">금액</TableHead>
                  <TableHead
                    className="cursor-pointer select-none text-right"
                    onClick={() => handleSort("pnl")}
                  >
                    손익{sortIndicator("pnl")}
                  </TableHead>
                  <TableHead
                    className="cursor-pointer select-none text-right"
                    onClick={() => handleSort("pnl_pct")}
                  >
                    수익률{sortIndicator("pnl_pct")}
                  </TableHead>
                  <TableHead
                    className="cursor-pointer select-none text-right"
                    onClick={() => handleSort("holding_days")}
                  >
                    보유일{sortIndicator("holding_days")}
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sorted.map((t, i) => (
                  <TableRow key={i}>
                    <TableCell className="font-mono text-xs">
                      {formatDate(t.date)}
                    </TableCell>
                    <TableCell className="text-xs">{t.strategy}</TableCell>
                    <TableCell>
                      <div>
                        <span className="text-xs font-mono">{t.code}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <span
                        className={cn(
                          "text-xs font-medium",
                          t.side === "BUY" && "text-red-500",
                          (t.side === "SELL" || t.side === "CLOSE") &&
                            "text-blue-500"
                        )}
                      >
                        {t.side}
                      </span>
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs">
                      {formatKRW(t.price)}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs">
                      {formatKRW(t.amount)}
                    </TableCell>
                    <TableCell
                      className={cn(
                        "text-right font-mono text-xs",
                        t.pnl != null && t.pnl > 0 && "text-success",
                        t.pnl != null && t.pnl < 0 && "text-destructive"
                      )}
                    >
                      {t.pnl != null ? formatKRW(t.pnl) : "-"}
                    </TableCell>
                    <TableCell
                      className={cn(
                        "text-right font-mono text-xs font-medium",
                        t.pnl_pct != null && t.pnl_pct > 0 && "text-success",
                        t.pnl_pct != null &&
                          t.pnl_pct < 0 &&
                          "text-destructive"
                      )}
                    >
                      {t.pnl_pct != null
                        ? formatPercent(t.pnl_pct * 100)
                        : "-"}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs">
                      {t.holding_days ?? "-"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
