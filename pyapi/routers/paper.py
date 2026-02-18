from __future__ import annotations

from fastapi import APIRouter, Depends
from typing import Optional

from pydantic import BaseModel

from pyapi.deps import verify_secret

router = APIRouter(prefix="/py/paper", tags=["paper"])


class ExecuteRequest(BaseModel):
    session_id: str
    signal_index: Optional[int] = None  # None이면 전체 실행


@router.post("/sessions")
def create_session(secret: None = Depends(verify_secret)):
    """새 모의거래 세션 생성"""
    from dashboard.services.paper_trading_service import create_session

    try:
        session = create_session()
        return {"data": session, "error": None}
    except Exception as e:
        return {"data": None, "error": str(e)}


@router.get("/sessions/active")
def get_active_session(secret: None = Depends(verify_secret)):
    """활성 세션 조회"""
    from dashboard.services.paper_trading_service import get_active_session

    session = get_active_session()
    return {"data": session, "error": None}


@router.post("/sessions/{session_id}/stop")
def stop_session(session_id: str, secret: None = Depends(verify_secret)):
    """세션 종료"""
    from dashboard.services.paper_trading_service import stop_session

    try:
        stop_session(session_id)
        return {"data": {"stopped": True}, "error": None}
    except Exception as e:
        return {"data": None, "error": str(e)}


@router.get("/sessions")
def get_sessions(secret: None = Depends(verify_secret)):
    """세션 목록 조회"""
    from dashboard.services.paper_trading_service import get_session_history

    try:
        sessions = get_session_history()
        return {"data": sessions, "error": None}
    except Exception as e:
        return {"data": None, "error": str(e)}


@router.post("/execute")
def execute_signal(req: ExecuteRequest, secret: None = Depends(verify_secret)):
    """시그널 실행 (단건 또는 전체)"""
    from dashboard.services.paper_trading_service import (
        generate_signals_dry_run,
        execute_signal,
        execute_all_signals,
    )

    try:
        signals = generate_signals_dry_run()
        if not signals:
            return {"data": {"results": [], "message": "실행할 시그널이 없습니다"}, "error": None}

        if req.signal_index is not None:
            if req.signal_index >= len(signals):
                return {"data": None, "error": f"시그널 인덱스 {req.signal_index} 범위 초과"}
            result = execute_signal(req.session_id, signals[req.signal_index])
            return {"data": {"results": [result]}, "error": None}
        else:
            results = execute_all_signals(req.session_id, signals)
            return {"data": {"results": results}, "error": None}
    except Exception as e:
        return {"data": None, "error": str(e)}


@router.get("/sessions/{session_id}/trades")
def get_trades(session_id: str, secret: None = Depends(verify_secret)):
    """세션 거래 내역 조회"""
    from dashboard.services.paper_trading_service import get_paper_trades

    try:
        df = get_paper_trades(session_id)
        trades = df.to_dict("records") if not df.empty else []
        return {"data": trades, "error": None}
    except Exception as e:
        return {"data": None, "error": str(e)}


@router.get("/sessions/{session_id}/summary")
def get_summary(session_id: str, secret: None = Depends(verify_secret)):
    """세션 거래 요약"""
    from dashboard.services.paper_trading_service import get_session_trade_summary

    try:
        summary = get_session_trade_summary(session_id)
        return {"data": summary, "error": None}
    except Exception as e:
        return {"data": None, "error": str(e)}
