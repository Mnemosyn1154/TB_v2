"use client";

import { useState, useCallback, useEffect } from "react";
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
  const [error, setError] = useState<string | null>(null);

  async function handleCreateSession() {
    setCreating(true);
    setError(null);
    try {
      const res = await createPaperSession();
      if (res.error) {
        setError(res.error);
        return;
      }
      refetchActive();
      refetchSessions();
    } finally {
      setCreating(false);
    }
  }

  async function handleStopSession(id: string) {
    setError(null);
    const res = await stopPaperSession(id);
    if (res.error) {
      setError(res.error);
      return;
    }
    refetchActive();
    refetchSessions();
  }

  async function handleExecute() {
    if (!active) return;
    setExecuting(true);
    setError(null);
    try {
      const res = await executePaperSignals(active.session_id);
      if (res.error) {
        setError(res.error);
        return;
      }
      // 거래 내역 새로고침
      const tradesRes = (await getPaperTrades(
        active.session_id
      )) as ApiResponse<PaperTrade[]>;
      if (tradesRes.data) setTrades(tradesRes.data);
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

  useEffect(() => {
    if (active?.session_id) {
      loadTrades();
    }
  }, [active?.session_id, loadTrades]);

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

      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

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
