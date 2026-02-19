"use client";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { formatKRW, formatUSD, formatPercent, formatNumber } from "@/lib/formatters";
import { snakeToTitle } from "@/lib/strategy-utils";
import type { Position, MarketBalance } from "@/types/portfolio";

interface HoldingsTableProps {
  kr: MarketBalance;
  us: MarketBalance;
}

function fmt(p: Position) {
  return p.market === "KR" ? formatKRW : formatUSD;
}

/** Group all positions by strategy */
function groupByStrategy(positions: Position[]): Map<string, Position[]> {
  const map = new Map<string, Position[]>();
  for (const p of positions) {
    const key = p.strategy || "";
    const list = map.get(key) ?? [];
    list.push(p);
    map.set(key, list);
  }
  return map;
}

/** Strategy-level totals */
function strategySummary(positions: Position[]) {
  let totalCost = 0;
  let totalValue = 0;
  for (const p of positions) {
    totalCost += p.avg_price * p.quantity;
    totalValue += p.current_price * p.quantity;
  }
  const pnl = totalValue - totalCost;
  const pnlPct = totalCost > 0 ? (pnl / totalCost) * 100 : 0;
  return { totalCost, totalValue, pnl, pnlPct };
}

function StrategyCard({
  strategy,
  positions,
}: {
  strategy: string;
  positions: Position[];
}) {
  const summary = strategySummary(positions);

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            {strategy ? snakeToTitle(strategy) : "기타"}
            <span className="text-xs font-normal text-muted-foreground">
              {positions.length}종목
            </span>
          </CardTitle>
          <div className="flex items-center gap-3 text-sm">
            <span
              className={cn(
                "font-mono font-semibold",
                summary.pnlPct > 0 && "text-success",
                summary.pnlPct < 0 && "text-destructive"
              )}
            >
              {formatPercent(summary.pnlPct)}
            </span>
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="overflow-x-auto rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>종목</TableHead>
                <TableHead className="text-right">수량</TableHead>
                <TableHead className="text-right">투자원금</TableHead>
                <TableHead className="text-right">평가금액</TableHead>
                <TableHead className="text-right">수익률</TableHead>
                <TableHead className="text-right">평가손익</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {positions.map((p) => {
                const formatPrice = fmt(p);
                const investedAmt = p.avg_price * p.quantity;
                const currentAmt = p.current_price * p.quantity;
                return (
                  <TableRow key={p.code}>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <div>
                          <div className="font-medium">{p.name}</div>
                          <div className="text-xs text-muted-foreground font-mono">
                            {p.code}
                          </div>
                        </div>
                        <Badge
                          variant="outline"
                          className="text-[10px] shrink-0"
                        >
                          {p.market}
                        </Badge>
                      </div>
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {formatNumber(p.quantity)}
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      <div>{formatPrice(investedAmt)}</div>
                      <div className="text-xs text-muted-foreground">
                        @{formatPrice(p.avg_price)}
                      </div>
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      <div>{formatPrice(currentAmt)}</div>
                      <div className="text-xs text-muted-foreground">
                        @{formatPrice(p.current_price)}
                      </div>
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
                      {fmt(p)(p.profit_amt)}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}

export function HoldingsTable({ kr, us }: HoldingsTableProps) {
  const allPositions = [...kr.positions, ...us.positions];

  if (allPositions.length === 0) {
    return (
      <div className="flex h-32 items-center justify-center rounded-lg border border-dashed text-sm text-muted-foreground">
        보유 종목이 없습니다
      </div>
    );
  }

  const grouped = groupByStrategy(allPositions);

  return (
    <div className="flex flex-col gap-4">
      {Array.from(grouped.entries()).map(([strategy, items]) => (
        <StrategyCard key={strategy} strategy={strategy} positions={items} />
      ))}
    </div>
  );
}
