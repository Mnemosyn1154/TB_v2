import type { LucideIcon } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface MetricsCardProps {
  icon: LucideIcon;
  label: string;
  value: string;
  description?: string;
  change?: string;
  changePositive?: boolean;
  className?: string;
}

export function MetricsCard({
  icon: Icon,
  label,
  value,
  description,
  change,
  changePositive,
  className,
}: MetricsCardProps) {
  return (
    <Card className={cn("gap-0 py-4", className)}>
      <CardContent className="flex flex-col gap-1">
        <div className="flex items-center gap-2 text-muted-foreground">
          <Icon className="h-4 w-4" />
          <span className="text-sm font-medium">{label}</span>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-bold tracking-tight">{value}</span>
          {change && (
            <span
              className={cn(
                "text-sm font-medium",
                changePositive === true && "text-success",
                changePositive === false && "text-destructive"
              )}
            >
              {change}
            </span>
          )}
        </div>
        {description && (
          <span className="text-xs text-muted-foreground">{description}</span>
        )}
      </CardContent>
    </Card>
  );
}
