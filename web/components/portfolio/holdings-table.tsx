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
import { cn } from "@/lib/utils";
import { formatKRW, formatUSD, formatPercent, formatNumber } from "@/lib/formatters";
import type { Position, MarketBalance } from "@/types/portfolio";

interface HoldingsTableProps {
  kr: MarketBalance;
  us: MarketBalance;
}

export function HoldingsTable({ kr, us }: HoldingsTableProps) {
  const [market, setMarket] = useState<"KR" | "US">("KR");
  const positions = market === "KR" ? kr.positions : us.positions;
  const formatPrice = market === "KR" ? formatKRW : formatUSD;

  return (
    <div>
      <div className="mb-4 flex items-center gap-2">
        {(["KR", "US"] as const).map((m) => (
          <button
            key={m}
            onClick={() => setMarket(m)}
            className={cn(
              "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
              market === m
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-accent"
            )}
          >
            {m === "KR" ? "국내" : "해외"}
          </button>
        ))}
      </div>

      {positions.length === 0 ? (
        <div className="flex h-32 items-center justify-center rounded-lg border border-dashed text-sm text-muted-foreground">
          보유 종목이 없습니다
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>종목</TableHead>
                <TableHead className="text-right">수량</TableHead>
                <TableHead className="text-right">평균가</TableHead>
                <TableHead className="text-right">현재가</TableHead>
                <TableHead className="text-right">수익률</TableHead>
                <TableHead className="text-right">평가손익</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {positions.map((p) => (
                <TableRow key={p.code}>
                  <TableCell>
                    <div>
                      <div className="font-medium">{p.name}</div>
                      <div className="text-xs text-muted-foreground font-mono">
                        {p.code}
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    {formatNumber(p.quantity)}
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    {formatPrice(p.avg_price)}
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    {formatPrice(p.current_price)}
                  </TableCell>
                  <TableCell
                    className={cn(
                      "text-right font-mono font-medium",
                      p.profit_pct > 0 && "text-success",
                      p.profit_pct < 0 && "text-destructive"
                    )}
                  >
                    {formatPercent(p.profit_pct)}
                  </TableCell>
                  <TableCell
                    className={cn(
                      "text-right font-mono",
                      p.profit_amt > 0 && "text-success",
                      p.profit_amt < 0 && "text-destructive"
                    )}
                  >
                    {formatPrice(p.profit_amt)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
