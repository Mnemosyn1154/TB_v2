import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface LoadingSpinnerProps {
  className?: string;
  /** Full-page centered spinner (default) or inline */
  fullPage?: boolean;
}

export function LoadingSpinner({
  className,
  fullPage = true,
}: LoadingSpinnerProps) {
  if (!fullPage) {
    return (
      <Loader2
        className={cn("h-5 w-5 animate-spin text-muted-foreground", className)}
      />
    );
  }

  return (
    <div className="flex h-[60vh] items-center justify-center">
      <Loader2
        className={cn("h-8 w-8 animate-spin text-muted-foreground", className)}
      />
    </div>
  );
}
