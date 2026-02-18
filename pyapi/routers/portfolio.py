from __future__ import annotations

from fastapi import APIRouter, Depends

from pyapi.deps import verify_secret

router = APIRouter(prefix="/py", tags=["portfolio"])


@router.get("/portfolio")
def get_portfolio(secret: None = Depends(verify_secret)):
    """KIS API 잔고 + 리스크 상태 조회"""
    from dashboard.services.portfolio_service import get_portfolio_status

    result = get_portfolio_status()
    error = result.pop("error", None)
    return {"data": result, "error": error}
