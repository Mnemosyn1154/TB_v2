import { Inbox } from "lucide-react";
import { cn } from "@/lib/utils";

interface EmptyStateProps {
  title?: string;
  description?: string;
  className?: string;
}

export function EmptyState({
  title = "데이터 없음",
  description = "표시할 데이터가 없습니다",
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex h-[40vh] items-center justify-center rounded-lg border border-dashed border-border",
        className
      )}
    >
      <div className="text-center">
        <Inbox className="mx-auto h-10 w-10 text-muted-foreground/50" />
        <p className="mt-3 text-sm font-medium">{title}</p>
        <p className="mt-1 text-xs text-muted-foreground">{description}</p>
      </div>
    </div>
  );
}
