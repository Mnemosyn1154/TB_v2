"use client";

import { useState, useCallback } from "react";
import { Loader2 } from "lucide-react";
import { useApi } from "@/hooks/use-api";
import {
  getActivePaperSession,
  getPaperSessions,
  createPaperSession,
  stopPaperSession,
  executePaperSignals,
  getPaperTrades,
} from "@/lib/api-client";
import { SignalPreview } from "./signal-preview";
import { PaperSessionPanel } from "./paper-session";
import { PaperTrades } from "./paper-trades";
import type { PaperSession, PaperTrade } from "@/types/paper";
import type { ApiResponse } from "@/types/common";

export function PaperTab() {
  const activeFetcher = useCallback(
    () => getActivePaperSession() as Promise<ApiResponse<PaperSession | null>>,
    []
  );
  const sessionsFetcher = useCallback(
    () => getPaperSessions() as Promise<ApiResponse<PaperSession[]>>,
    []
  );

  const {
    data: active,
    loading: activeLoading,
    refetch: refetchActive,
  } = useApi<PaperSession | null>(activeFetcher);
  const {
    data: sessions,
    loading: sessionsLoading,
    refetch: refetchSessions,
  } = useApi<PaperSession[]>(sessionsFetcher);

  const [trades, setTrades] = useState<PaperTrade[]>([]);
  const [creating, setCreating] = useState(false);
  const [executing, setExecuting] = useState(false);

  async function handleCreateSession() {
    setCreating(true);
    try {
      await createPaperSession();
      refetchActive();
      refetchSessions();
    } finally {
      setCreating(false);
    }
  }

  async function handleStopSession(id: string) {
    await stopPaperSession(id);
    refetchActive();
    refetchSessions();
  }

  async function handleExecute() {
    if (!active) return;
    setExecuting(true);
    try {
      await executePaperSignals(active.session_id);
      // 거래 내역 새로고침
      const res = (await getPaperTrades(
        active.session_id
      )) as ApiResponse<PaperTrade[]>;
      if (res.data) setTrades(res.data);
    } finally {
      setExecuting(false);
    }
  }

  // 활성 세션 변경 시 거래 내역 로드
  const loadTrades = useCallback(async () => {
    if (active?.session_id) {
      const res = (await getPaperTrades(
        active.session_id
      )) as ApiResponse<PaperTrade[]>;
      if (res.data) setTrades(res.data);
    }
  }, [active?.session_id]);

  // active가 로드되면 trades도 로드
  if (active?.session_id && trades.length === 0 && !executing) {
    loadTrades();
  }

  if (activeLoading && sessionsLoading) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <h2 className="text-lg font-semibold">모의거래</h2>

      <section>
        <h3 className="mb-3 text-sm font-semibold text-muted-foreground">
          세션 관리
        </h3>
        <PaperSessionPanel
          active={active ?? null}
          sessions={sessions ?? []}
          onCreateSession={handleCreateSession}
          onStopSession={handleStopSession}
          creating={creating}
        />
      </section>

      {active && (
        <section>
          <h3 className="mb-3 text-sm font-semibold text-muted-foreground">
            시그널 미리보기
          </h3>
          <SignalPreview onExecute={handleExecute} executing={executing} />
        </section>
      )}

      {active && trades.length > 0 && (
        <section>
          <h3 className="mb-3 text-sm font-semibold text-muted-foreground">
            거래 내역
          </h3>
          <PaperTrades trades={trades} />
        </section>
      )}
    </div>
  );
}
