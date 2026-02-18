import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { formatPercent } from "@/lib/formatters";
import type { StrategyComparison } from "@/types/benchmark";

interface StrategyVsMarketProps {
  comparisons: StrategyComparison[];
}

export function StrategyVsMarket({ comparisons }: StrategyVsMarketProps) {
  if (comparisons.length === 0) return null;

  return (
    <div className="overflow-x-auto rounded-lg border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>전략</TableHead>
            <TableHead className="text-right">수익률</TableHead>
            <TableHead className="text-right">벤치마크</TableHead>
            <TableHead className="text-right">초과수익</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {comparisons.map((c) => (
            <TableRow key={c.strategy}>
              <TableCell className="font-medium">{c.strategy}</TableCell>
              <TableCell
                className={cn(
                  "text-right font-mono",
                  c.return_pct > 0 && "text-success",
                  c.return_pct < 0 && "text-destructive"
                )}
              >
                {formatPercent(c.return_pct)}
              </TableCell>
              <TableCell className="text-right font-mono">
                {formatPercent(c.benchmark_return)}
              </TableCell>
              <TableCell
                className={cn(
                  "text-right font-mono font-medium",
                  c.excess_return > 0 && "text-success",
                  c.excess_return < 0 && "text-destructive"
                )}
              >
                {formatPercent(c.excess_return)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
