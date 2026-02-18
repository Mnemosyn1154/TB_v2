import { ShieldAlert, Activity, TrendingDown } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import type { RiskSummary } from "@/types/portfolio";

interface RiskIndicatorsProps {
  risk: RiskSummary;
}

function Indicator({
  icon: Icon,
  label,
  value,
  tooltip,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  tooltip: string;
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <div className="flex items-center gap-2">
          <Icon className="h-4 w-4 text-muted-foreground" />
          <span className="text-xs text-muted-foreground">{label}</span>
          <span className="text-sm font-medium font-mono">{value}</span>
        </div>
      </TooltipTrigger>
      <TooltipContent>
        <p className="text-xs">{tooltip}</p>
      </TooltipContent>
    </Tooltip>
  );
}

export function RiskIndicators({ risk }: RiskIndicatorsProps) {
  return (
    <div className="flex flex-wrap items-center gap-4 rounded-lg border px-4 py-3 md:gap-6">
      <Indicator
        icon={TrendingDown}
        label="MDD"
        value={risk.drawdown}
        tooltip="최대 낙폭 (Maximum Drawdown)"
      />
      <Indicator
        icon={Activity}
        label="포지션"
        value={`${risk.positions_count} / ${risk.max_positions}`}
        tooltip="현재 포지션 수 / 최대 포지션 수"
      />
      <div className="flex items-center gap-2">
        <ShieldAlert className="h-4 w-4 text-muted-foreground" />
        <span className="text-xs text-muted-foreground">Kill Switch</span>
        <Badge
          variant={risk.kill_switch ? "destructive" : "secondary"}
          className={cn(!risk.kill_switch && "bg-success/15 text-success")}
        >
          {risk.kill_switch ? "ON" : "OFF"}
        </Badge>
      </div>
    </div>
  );
}
