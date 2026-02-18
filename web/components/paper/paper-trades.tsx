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
import { formatKRW, formatNumber, formatDateShort } from "@/lib/formatters";
import type { PaperTrade } from "@/types/paper";

interface PaperTradesProps {
  trades: PaperTrade[];
}

export function PaperTrades({ trades }: PaperTradesProps) {
  if (trades.length === 0) {
    return (
      <div className="flex h-32 items-center justify-center rounded-lg border border-dashed text-sm text-muted-foreground">
        거래 내역이 없습니다
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>일시</TableHead>
            <TableHead>전략</TableHead>
            <TableHead>종목</TableHead>
            <TableHead>방향</TableHead>
            <TableHead className="text-right">수량</TableHead>
            <TableHead className="text-right">가격</TableHead>
            <TableHead>사유</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {trades.map((t, i) => (
            <TableRow key={`${t.code}-${t.timestamp}-${i}`}>
              <TableCell className="text-xs font-mono">
                {t.timestamp ? formatDateShort(t.timestamp) : "-"}
              </TableCell>
              <TableCell>
                <Badge variant="outline" className="text-xs">
                  {t.strategy}
                </Badge>
              </TableCell>
              <TableCell className="font-mono text-sm">{t.code}</TableCell>
              <TableCell>
                <Badge
                  variant={t.side === "BUY" ? "default" : "destructive"}
                  className={cn(
                    t.side === "BUY" && "bg-success text-success-foreground"
                  )}
                >
                  {t.side}
                </Badge>
              </TableCell>
              <TableCell className="text-right font-mono">
                {formatNumber(t.quantity)}
              </TableCell>
              <TableCell className="text-right font-mono">
                {t.market === "KR" ? formatKRW(t.price) : `$${t.price}`}
              </TableCell>
              <TableCell className="max-w-48 truncate text-xs text-muted-foreground">
                {t.reason}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
