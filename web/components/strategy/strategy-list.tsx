"use client";

import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Settings, Trash2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import { snakeToTitle, summarizeConfig } from "@/lib/strategy-utils";

interface StrategyListProps {
  strategies: Record<string, Record<string, unknown>>;
  onToggle: (key: string) => void;
  onEdit: (key: string) => void;
  onDelete: (key: string) => void;
}

export function StrategyList({
  strategies,
  onToggle,
  onEdit,
  onDelete,
}: StrategyListProps) {
  const [deleteKey, setDeleteKey] = useState<string | null>(null);

  function handleConfirmDelete() {
    if (deleteKey) {
      onDelete(deleteKey);
      setDeleteKey(null);
    }
  }

  return (
    <>
      <div className="flex flex-col gap-4">
        {Object.entries(strategies).map(([key, config]) => {
          const enabled = config.enabled as boolean;
          const typeName = config.type as string | undefined;
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
                    {typeName && (
                      <Badge variant="outline" className="text-xs">
                        {typeName}
                      </Badge>
                    )}
                  </div>
                  <Switch
                    checked={enabled}
                    onCheckedChange={() => onToggle(key)}
                  />
                </div>
                <p className="text-sm text-muted-foreground">
                  {summarizeConfig(config)}
                </p>
                <div className="flex justify-end gap-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-destructive hover:text-destructive"
                    onClick={() => setDeleteKey(key)}
                  >
                    <Trash2 className="mr-1.5 h-3.5 w-3.5" />
                    삭제
                  </Button>
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

      <Dialog open={!!deleteKey} onOpenChange={(v) => !v && setDeleteKey(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>전략 삭제</DialogTitle>
            <DialogDescription>
              &apos;{deleteKey}&apos; 전략을 삭제하시겠습니까? settings.yaml에서
              해당 설정이 제거됩니다. 이 작업은 되돌릴 수 없습니다.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setDeleteKey(null)}>
              취소
            </Button>
            <Button variant="destructive" onClick={handleConfirmDelete}>
              삭제
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
