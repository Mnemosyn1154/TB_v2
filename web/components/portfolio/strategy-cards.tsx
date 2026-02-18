import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { formatPercent } from "@/lib/formatters";
import type { StrategyStatus } from "@/types/portfolio";

interface StrategyCardsProps {
  strategies: StrategyStatus[];
}

export function StrategyCards({ strategies }: StrategyCardsProps) {
  if (!strategies || strategies.length === 0) return null;

  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
      {strategies.map((s) => (
        <Card
          key={s.key}
          className={cn("gap-0 py-4", !s.enabled && "opacity-50")}
        >
          <CardContent className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold">{s.name}</span>
              <Badge variant={s.enabled ? "default" : "secondary"}>
                {s.enabled ? "ON" : "OFF"}
              </Badge>
            </div>
            {s.enabled ? (
              <>
                <span
                  className={cn(
                    "text-xl font-bold",
                    s.pnl_pct > 0 && "text-success",
                    s.pnl_pct < 0 && "text-destructive"
                  )}
                >
                  {formatPercent(s.pnl_pct)}
                </span>
                <span className="text-xs text-muted-foreground">
                  포지션 {s.positions_count}개
                </span>
              </>
            ) : (
              <span className="text-sm text-muted-foreground">비활성</span>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
