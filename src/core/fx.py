from __future__ import annotations

"""USD/KRW 환율 유틸리티

Depends on:
    - yfinance (환율 조회)

Used by:
    - src.core.portfolio_tracker (매수/매도 시 환전)
    - src.core.risk_manager (포지션 사이징)
    - src.execution.executor (리스크 검증)
    - src.backtest.engine (백테스트 환전)
    - dashboard.services.portfolio_service (포트폴리오 표시)

Modification Guide:
    - 환율 소스 변경: get_usd_krw() 내부 로직 수정
    - 새 통화 추가: get_fx_rate(market) 확장
"""

import time

from loguru import logger

_fx_cache: dict[str, tuple[float, float]] = {}  # pair -> (rate, timestamp)
_FX_TTL = 3600  # 1-hour cache

# Fallback rate when API unavailable
_FALLBACK_USD_KRW = 1350.0


def get_usd_krw() -> float:
    """USD/KRW exchange rate (yfinance, 1-hour cache)"""
    cached = _fx_cache.get("USDKRW")
    if cached and (time.time() - cached[1]) < _FX_TTL:
        return cached[0]
    try:
        import yfinance as yf
        ticker = yf.Ticker("USDKRW=X")
        rate = ticker.fast_info.get("lastPrice", 0) or 0
        if rate > 0:
            _fx_cache["USDKRW"] = (rate, time.time())
            logger.debug(f"USD/KRW exchange rate: {rate:,.1f}")
            return rate
    except Exception as e:
        logger.warning(f"USD/KRW rate fetch failed: {e}")
    # Use expired cache if available
    if cached:
        return cached[0]
    return _FALLBACK_USD_KRW


def get_fx_rate(market: str) -> float:
    """Return KRW multiplier for the given market.

    KR -> 1.0 (already KRW)
    US -> USD/KRW rate (~1350)
    """
    if market == "US":
        return get_usd_krw()
    return 1.0


def to_krw(amount: float, market: str) -> float:
    """Convert a native-currency amount to KRW."""
    return amount * get_fx_rate(market)
