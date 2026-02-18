from __future__ import annotations

from fastapi import APIRouter, Depends

from pyapi.deps import verify_secret

router = APIRouter(prefix="/py", tags=["signals"])


@router.get("/signals")
def get_signals(secret: None = Depends(verify_secret)):
    """시그널 미리보기 (dry-run) — _raw 필드 제거"""
    from dashboard.services.paper_trading_service import generate_signals_dry_run

    try:
        signals = generate_signals_dry_run()
        # _raw (TradeSignal 객체)는 JSON 직렬화 불가이므로 제거
        clean = [{k: v for k, v in s.items() if k != "_raw"} for s in signals]
        return {"data": clean, "error": None}
    except Exception as e:
        return {"data": None, "error": str(e)}
