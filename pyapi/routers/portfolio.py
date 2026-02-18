from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from pyapi.deps import verify_secret

router = APIRouter(prefix="/py", tags=["portfolio"])


class SetCapitalRequest(BaseModel):
    amount: float


@router.get("/portfolio/capital")
def get_capital(secret: None = Depends(verify_secret)):
    """초기 자본금 + 현금 잔고 조회"""
    from src.core.portfolio_tracker import PortfolioTracker

    tracker = PortfolioTracker()
    return {
        "data": {
            "initial_capital": tracker.get_initial_capital(),
            "cash": tracker.get_cash(),
        },
        "error": None,
    }


@router.post("/portfolio/capital")
def set_capital(req: SetCapitalRequest, secret: None = Depends(verify_secret)):
    """초기 자본금 설정 (포트폴리오 리셋)"""
    from src.core.portfolio_tracker import PortfolioTracker

    tracker = PortfolioTracker()
    tracker.set_initial_capital(req.amount)
    return {
        "data": {
            "initial_capital": req.amount,
            "cash": req.amount,
        },
        "error": None,
    }


@router.post("/portfolio/reset")
def reset_portfolio(secret: None = Depends(verify_secret)):
    """포트폴리오 리셋 (초기 자본금 유지, 포지션 삭제)"""
    from src.core.portfolio_tracker import PortfolioTracker

    tracker = PortfolioTracker()
    tracker.reset()
    return {
        "data": {"message": "포트폴리오가 초기화되었습니다."},
        "error": None,
    }


@router.get("/portfolio")
def get_portfolio(secret: None = Depends(verify_secret)):
    """포트폴리오 상태 조회 (시뮬레이션/실거래 자동 분기)"""
    from dashboard.services.portfolio_service import get_portfolio_status

    result = get_portfolio_status()
    error = result.pop("error", None)
    return {"data": result, "error": error}
