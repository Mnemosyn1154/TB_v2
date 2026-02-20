from __future__ import annotations

"""S&P 500 유니버스 관리 API

캐시 상태 조회, 강제 갱신, 종목 목록 조회를 제공합니다.

Depends on:
    - src.core.universe (UniverseManager)
    - src.core.exchange (reset_exchange_cache)
    - pyapi.deps (verify_secret)

Used by:
    - web/app/api/universe/route.ts (Next.js 프록시) — 미구현
"""

from fastapi import APIRouter, Depends
from loguru import logger

from pyapi.deps import verify_secret
from pyapi.schemas import UniversePreviewRequest

router = APIRouter(prefix="/py", tags=["universe"])


@router.get("/universe/status")
def universe_status(_: None = Depends(verify_secret)):
    """유니버스 캐시 상태 조회"""
    try:
        from src.core.universe import UniverseManager

        mgr = UniverseManager()
        return {"data": mgr.get_status(), "error": None}
    except Exception as e:
        logger.error(f"universe status 실패: {e}")
        return {"data": None, "error": str(e)}


@router.post("/universe/refresh")
def universe_refresh(_: None = Depends(verify_secret)):
    """유니버스 강제 갱신"""
    try:
        from src.core.config import get_config
        from src.core.universe import UniverseManager
        from src.core.exchange import reset_exchange_cache

        config = get_config()
        universe_cfg = config.get("strategies", {}).get("quant_factor", {}).get("universe", {})

        mgr = UniverseManager()
        stocks = mgr.refresh(universe_cfg)
        reset_exchange_cache()

        return {"data": {"refreshed": len(stocks)}, "error": None}
    except Exception as e:
        logger.error(f"universe refresh 실패: {e}")
        return {"data": None, "error": str(e)}


@router.post("/universe/preview")
def universe_preview(req: UniversePreviewRequest, _: None = Depends(verify_secret)):
    """커스텀 필터로 S&P 500 유니버스 프리뷰 (캐시 저장 안함)"""
    try:
        from src.core.universe import UniverseManager

        mgr = UniverseManager()
        stocks = mgr.preview(req.model_dump())
        return {"data": stocks, "error": None}
    except Exception as e:
        logger.error(f"universe preview 실패: {e}")
        return {"data": None, "error": str(e)}


@router.get("/universe/stocks")
def universe_stocks(_: None = Depends(verify_secret)):
    """유니버스 종목 목록 조회"""
    try:
        from src.core.config import get_config
        from src.core.universe import UniverseManager

        config = get_config()
        universe_cfg = config.get("strategies", {}).get("quant_factor", {}).get("universe", {})

        mgr = UniverseManager()
        stocks = mgr.get_stocks(universe_cfg)

        return {"data": stocks, "error": None}
    except Exception as e:
        logger.error(f"universe stocks 실패: {e}")
        return {"data": None, "error": str(e)}
