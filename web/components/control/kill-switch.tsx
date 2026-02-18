"use client";

import { useState } from "react";
import { ShieldAlert, ShieldCheck } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface KillSwitchProps {
  active: boolean;
  toggling: boolean;
  onToggle: () => void;
}

export function KillSwitch({ active, toggling, onToggle }: KillSwitchProps) {
  const [confirmOpen, setConfirmOpen] = useState(false);

  const handleClick = () => {
    if (!active) {
      // Activating kill switch — needs confirmation
      setConfirmOpen(true);
    } else {
      // Deactivating kill switch — direct
      onToggle();
    }
  };

  const confirmActivate = () => {
    setConfirmOpen(false);
    onToggle();
  };

  return (
    <>
      <Card
        className={
          active
            ? "border-red-500/50 bg-red-500/5"
            : "border-green-500/50 bg-green-500/5"
        }
      >
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            {active ? (
              <ShieldAlert className="h-5 w-5 text-red-500" />
            ) : (
              <ShieldCheck className="h-5 w-5 text-green-500" />
            )}
            Kill Switch
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col items-center gap-4">
          <div className="text-center">
            <p className="text-sm text-muted-foreground">
              {active
                ? "Kill Switch가 활성화되어 모든 전략 실행이 중단됩니다"
                : "정상 운영 중입니다"}
            </p>
          </div>

          <Button
            size="lg"
            variant={active ? "outline" : "destructive"}
            className={`w-full max-w-xs text-base font-semibold ${
              active
                ? "border-green-500 text-green-600 hover:bg-green-500/10"
                : "bg-red-600 hover:bg-red-700"
            }`}
            onClick={handleClick}
            disabled={toggling}
          >
            {toggling
              ? "처리 중..."
              : active
                ? "Kill Switch 해제"
                : "Kill Switch 활성화"}
          </Button>

          <span
            className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium ${
              active
                ? "bg-red-500/10 text-red-600"
                : "bg-green-500/10 text-green-600"
            }`}
          >
            {active ? "ON — 전략 중단됨" : "OFF — 정상 운영"}
          </span>
        </CardContent>
      </Card>

      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Kill Switch 활성화</DialogTitle>
            <DialogDescription>
              Kill Switch를 활성화하면 모든 전략 실행이 즉시 중단됩니다. 계속
              하시겠습니까?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmOpen(false)}>
              취소
            </Button>
            <Button variant="destructive" onClick={confirmActivate}>
              활성화
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
