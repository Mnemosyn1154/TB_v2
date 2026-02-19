import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { formatPercent } from "@/lib/formatters";
import type { StrategyStatus, StrategyAllocationInfo } from "@/types/portfolio";

interface StrategyCardsProps {
  strategies: StrategyStatus[];
  allocation?: Record<string, StrategyAllocationInfo>;
}

export function StrategyCards({ strategies, allocation }: StrategyCardsProps) {
  if (!strategies || strategies.length === 0) return null;

  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
      {strategies.map((s) => {
        const alloc = allocation?.[s.key];
        return (
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
                  {alloc && (
                    <div className="flex flex-col gap-1 pt-1">
                      <div className="flex justify-between text-xs text-muted-foreground">
                        <span>할당 {alloc.allocated_pct}%</span>
                        <span>사용 {alloc.used_pct}%</span>
                      </div>
                      <div className="h-1.5 w-full rounded-full bg-muted">
                        <div
                          className={cn(
                            "h-full rounded-full transition-all",
                            alloc.used_pct / alloc.allocated_pct > 0.9
                              ? "bg-destructive"
                              : "bg-primary"
                          )}
                          style={{
                            width: `${Math.min((alloc.used_pct / alloc.allocated_pct) * 100, 100)}%`,
                          }}
                        />
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <span className="text-sm text-muted-foreground">비활성</span>
              )}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
