"use client";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
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

/** Strategy-level totals (KRW 기준 환산) */
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

function PositionRows({ positions }: { positions: Position[] }) {
  return (
    <>
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
                <Badge variant="outline" className="text-[10px] shrink-0">
                  {p.market}
                </Badge>
              </div>
            </TableCell>
            <TableCell className="text-right font-mono">
              {formatNumber(p.quantity)}
            </TableCell>
            <TableCell className="text-right font-mono">
              <div>{formatPrice(p.avg_price)}</div>
              <div className="text-xs text-muted-foreground">
                {formatPrice(investedAmt)}
              </div>
            </TableCell>
            <TableCell className="text-right font-mono">
              <div>{formatPrice(p.current_price)}</div>
              <div className="text-xs text-muted-foreground">
                {formatPrice(currentAmt)}
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
    </>
  );
}

function StrategyGroup({
  strategy,
  positions,
}: {
  strategy: string;
  positions: Position[];
}) {
  const summary = strategySummary(positions);
  // 그룹 내 첫 포지션의 통화로 합산 표시 (혼합 시 KRW 기본)
  const mixed = new Set(positions.map((p) => p.market)).size > 1;
  const groupFmt = mixed ? formatKRW : fmt(positions[0]);

  return (
    <>
      <TableRow className="bg-muted/40 hover:bg-muted/40">
        <TableCell colSpan={2} className="py-2">
          <Badge variant="outline" className="text-xs font-semibold">
            {strategy ? snakeToTitle(strategy) : "기타"}
          </Badge>
          <span className="ml-2 text-xs text-muted-foreground">
            {positions.length}종목
          </span>
        </TableCell>
        <TableCell className="text-right font-mono text-xs py-2">
          {groupFmt(summary.totalCost)}
        </TableCell>
        <TableCell className="text-right font-mono text-xs py-2">
          {groupFmt(summary.totalValue)}
        </TableCell>
        <TableCell
          className={cn(
            "text-right font-mono text-xs font-medium py-2",
            summary.pnlPct > 0 && "text-success",
            summary.pnlPct < 0 && "text-destructive"
          )}
        >
          {formatPercent(summary.pnlPct)}
        </TableCell>
        <TableCell
          className={cn(
            "text-right font-mono text-xs py-2",
            summary.pnl > 0 && "text-success",
            summary.pnl < 0 && "text-destructive"
          )}
        >
          {groupFmt(summary.pnl)}
        </TableCell>
      </TableRow>
      <PositionRows positions={positions} />
    </>
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
  const hasStrategies = grouped.size > 1 || (grouped.size === 1 && !grouped.has(""));

  return (
    <div className="overflow-x-auto rounded-lg border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>종목</TableHead>
            <TableHead className="text-right">수량</TableHead>
            <TableHead className="text-right">평균가 / 원금</TableHead>
            <TableHead className="text-right">현재가 / 평가금</TableHead>
            <TableHead className="text-right">수익률</TableHead>
            <TableHead className="text-right">평가손익</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {hasStrategies ? (
            Array.from(grouped.entries()).map(([strategy, items]) => (
              <StrategyGroup
                key={strategy}
                strategy={strategy}
                positions={items}
              />
            ))
          ) : (
            <PositionRows positions={allPositions} />
          )}
        </TableBody>
      </Table>
    </div>
  );
}
