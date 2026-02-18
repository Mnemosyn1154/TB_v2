"""
AlgoTrader KR -- 미국 종목 거래소 매핑 유틸리티

settings.yaml의 전략 설정에서 미국 종목의 거래소(NAS/NYS) 정보를 조회합니다.
하드코딩 대신 설정 파일 기반으로 관리하여 종목 추가 시 자동 반영됩니다.

Depends on:
    - src.core.config (설정 로드)

Used by:
    - src.execution.collector (데이터 수집 시 거래소 코드)
    - src.execution.executor (주문 실행 시 거래소 코드)

Modification Guide:
    - 새 거래소 지원: _QUERY_TO_ORDER 매핑에 추가
    - 조회 우선순위 변경: _build_cache() 내부 순서 조정
"""
from __future__ import annotations

from loguru import logger

from src.core.config import get_config

# 조회용(NAS/NYS) → 주문용(NASD/NYSE) 변환
_QUERY_TO_ORDER = {"NAS": "NASD", "NYS": "NYSE", "AMS": "AMEX"}

_DEFAULT_EXCHANGE = "NYS"

# 모듈 레벨 캐시 — 첫 호출 시 구축
_EXCHANGE_CACHE: dict[str, str] | None = None


def _build_cache(config: dict) -> dict[str, str]:
    """settings.yaml 전략 설정에서 전체 거래소 매핑을 일괄 구축"""
    cache: dict[str, str] = {}
    strategies = config.get("strategies", {})

    # 1. StatArb pairs
    for pair in strategies.get("stat_arb", {}).get("pairs", []):
        if pair.get("market") != "US":
            continue
        if pair.get("exchange_a"):
            cache[pair["stock_a"]] = pair["exchange_a"]
        if pair.get("exchange_b"):
            cache[pair["stock_b"]] = pair["exchange_b"]
        if pair.get("exchange_hedge"):
            cache[pair["hedge_etf"]] = pair["exchange_hedge"]

    # 2. DualMomentum
    dm = strategies.get("dual_momentum", {})
    if dm.get("us_etf_exchange"):
        cache[dm["us_etf"]] = dm["us_etf_exchange"]
    if dm.get("safe_us_etf_exchange"):
        cache[dm["safe_us_etf"]] = dm["safe_us_etf_exchange"]

    # 3. QuantFactor universe
    for item in strategies.get("quant_factor", {}).get("universe_codes", []):
        if item.get("market") == "US" and item.get("exchange"):
            cache[item["code"]] = item["exchange"]

    return cache


def get_us_exchange(ticker: str, purpose: str = "query") -> str:
    """
    미국 종목의 거래소 코드를 반환합니다.

    settings.yaml의 전략 설정(StatArb, DualMomentum, QuantFactor)에서
    해당 종목의 exchange 정보를 조회합니다.
    첫 호출 시 캐시를 구축하여 이후 O(1) 조회합니다.

    Args:
        ticker: 미국 종목 티커 (예: "AAPL", "SPY")
        purpose: "query" -> 조회용 코드 (NAS/NYS)
                 "order" -> 주문용 코드 (NASD/NYSE)

    Returns:
        거래소 코드 문자열
    """
    global _EXCHANGE_CACHE
    if _EXCHANGE_CACHE is None:
        _EXCHANGE_CACHE = _build_cache(get_config())

    exchange = _EXCHANGE_CACHE.get(ticker)
    if exchange is None:
        logger.warning(
            f"거래소 매핑 없음: {ticker} -> 기본값 '{_DEFAULT_EXCHANGE}' 사용. "
            f"settings.yaml에 exchange 설정을 추가하세요."
        )
        exchange = _DEFAULT_EXCHANGE

    if purpose == "order":
        return _QUERY_TO_ORDER.get(exchange, "NYSE")
    return exchange
