"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Settings } from "lucide-react";
import { cn } from "@/lib/utils";
import { snakeToTitle, summarizeConfig } from "@/lib/strategy-utils";

interface StrategyListProps {
  strategies: Record<string, Record<string, unknown>>;
  onToggle: (key: string) => void;
  onEdit: (key: string) => void;
}

export function StrategyList({
  strategies,
  onToggle,
  onEdit,
}: StrategyListProps) {
  return (
    <div className="flex flex-col gap-4">
      {Object.entries(strategies).map(([key, config]) => {
        const enabled = config.enabled as boolean;
        return (
          <Card
            key={key}
            className={cn("gap-0 py-4", !enabled && "opacity-60")}
          >
            <CardContent className="flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="font-semibold">
                    {snakeToTitle(key)}
                  </span>
                  <Badge variant={enabled ? "default" : "secondary"}>
                    {enabled ? "ON" : "OFF"}
                  </Badge>
                </div>
                <Switch
                  checked={enabled}
                  onCheckedChange={() => onToggle(key)}
                />
              </div>
              <p className="text-sm text-muted-foreground">
                {summarizeConfig(config)}
              </p>
              <div className="flex justify-end">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onEdit(key)}
                >
                  <Settings className="mr-1.5 h-3.5 w-3.5" />
                  파라미터 편집
                </Button>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
