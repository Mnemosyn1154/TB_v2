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
  exchangeRate?: number;
}

const DEFAULT_FX = 1350;

function fmtPrice(p: Position) {
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

/** Convert amount to KRW */
function toKRW(amount: number, market: string, fx: number): number {
  return market === "US" ? amount * fx : amount;
}

/** Strategy-level totals in KRW */
function strategySummary(positions: Position[], fx: number) {
  let totalCost = 0;
  let totalValue = 0;
  for (const p of positions) {
    totalCost += toKRW(p.avg_price * p.quantity, p.market, fx);
    totalValue += toKRW(p.current_price * p.quantity, p.market, fx);
  }
  const pnl = totalValue - totalCost;
  const pnlPct = totalCost > 0 ? (pnl / totalCost) * 100 : 0;
  return { totalCost, totalValue, pnl, pnlPct };
}

function StrategyCard({
  strategy,
  positions,
  fx,
}: {
  strategy: string;
  positions: Position[];
  fx: number;
}) {
  const summary = strategySummary(positions, fx);

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
          <div className="flex items-center gap-4 text-sm">
            <div className="text-right">
              <div className="text-xs text-muted-foreground">투자원금</div>
              <div className="font-mono">{formatKRW(summary.totalCost)}</div>
            </div>
            <div className="text-right">
              <div className="text-xs text-muted-foreground">평가금액</div>
              <div className="font-mono">{formatKRW(summary.totalValue)}</div>
            </div>
            <div className="text-right">
              <div className="text-xs text-muted-foreground">수익률</div>
              <div
                className={cn(
                  "font-mono font-semibold",
                  summary.pnlPct > 0 && "text-success",
                  summary.pnlPct < 0 && "text-destructive"
                )}
              >
                {formatPercent(summary.pnlPct)}
              </div>
            </div>
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
                const formatP = fmtPrice(p);
                const investedAmt = p.avg_price * p.quantity;
                const currentAmt = p.current_price * p.quantity;
                const isUS = p.market === "US";
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
                      <div>{formatP(investedAmt)}</div>
                      {isUS && (
                        <div className="text-xs text-muted-foreground">
                          {formatKRW(investedAmt * fx)}
                        </div>
                      )}
                      <div className="text-xs text-muted-foreground">
                        @{formatP(p.avg_price)}
                      </div>
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      <div>{formatP(currentAmt)}</div>
                      {isUS && (
                        <div className="text-xs text-muted-foreground">
                          {formatKRW(currentAmt * fx)}
                        </div>
                      )}
                      <div className="text-xs text-muted-foreground">
                        @{formatP(p.current_price)}
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
                      <div>{fmtPrice(p)(p.profit_amt)}</div>
                      {isUS && (
                        <div className="text-xs text-muted-foreground">
                          {formatKRW(p.profit_amt * fx)}
                        </div>
                      )}
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

export function HoldingsTable({ kr, us, exchangeRate }: HoldingsTableProps) {
  const fx = exchangeRate || DEFAULT_FX;
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
      <div className="flex justify-end">
        <span className="text-xs text-muted-foreground font-mono">
          USD/KRW {formatKRW(fx)}
        </span>
      </div>
      {Array.from(grouped.entries()).map(([strategy, items]) => (
        <StrategyCard
          key={strategy}
          strategy={strategy}
          positions={items}
          fx={fx}
        />
      ))}
    </div>
  );
}
