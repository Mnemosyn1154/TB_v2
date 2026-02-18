from __future__ import annotations

"""벤치마크 인덱스 데이터 API — DB 캐시 + yfinance 보충

인덱스 심볼(^KS11, ^GSPC)을 daily_prices 테이블에 market='INDEX'로 저장하여
반복 요청 시 Yahoo Finance 호출을 줄인다.

Depends on:
    - src.core.data_feed (yfinance 데이터)
    - src.backtest.runner (save_prices_to_db, get_db_engine)
    - pyapi.deps (verify_secret)

Used by:
    - web/app/api/benchmark/route.ts (Next.js 프록시)
"""

from fastapi import APIRouter, Depends, Query

from pyapi.deps import verify_secret

router = APIRouter(prefix="/py", tags=["benchmark"])

INDEX_SYMBOLS = {
    "kospi": {"code": "^KS11", "market": "INDEX"},
    "sp500": {"code": "^GSPC", "market": "INDEX"},
}

PERIOD_DAYS = {
    "1M": 30,
    "3M": 90,
    "6M": 180,
    "1Y": 365,
    "ALL": 365 * 3,
}


@router.get("/benchmark/data")
def get_benchmark_data(
    period: str = Query("3M"),
    secret: None = Depends(verify_secret),
):
    """벤치마크 인덱스 가격 데이터 (DB 캐시 우선, yfinance 보충)"""
    from datetime import datetime, timedelta

    import pandas as pd
    from loguru import logger
    from sqlalchemy import text

    from src.backtest.runner import get_db_engine, save_prices_to_db

    days = PERIOD_DAYS.get(period, 90)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    engine = get_db_engine()

    result = {}
    for key, info in INDEX_SYMBOLS.items():
        code = info["code"]
        market = info["market"]

        # 1. DB 캐시 조회
        try:
            df = pd.read_sql(
                text("""
                    SELECT date, close FROM daily_prices
                    WHERE code = :code AND market = :market AND date >= :start
                    ORDER BY date ASC
                """),
                engine,
                params={"code": code, "market": market, "start": start_str},
            )
        except Exception:
            df = pd.DataFrame()

        # 2. DB 데이터 부족 시 yfinance로 보충
        # 캘린더일 대비 약 50%가 거래일이므로 이를 기준으로 판단
        needs_fetch = df.empty or len(df) < days * 0.5

        if needs_fetch:
            try:
                from src.core.data_feed import DataFeed

                feed = DataFeed()
                yf_df = feed.fetch(code, start_str, end_str, market="US")
                if not yf_df.empty:
                    yf_df["market"] = market  # INDEX로 저장
                    save_prices_to_db(yf_df)
                    logger.info(f"벤치마크 DB 캐시: {code} — {len(yf_df)}건")
                    df = yf_df[["date", "close"]].copy()
                    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
            except Exception as e:
                logger.warning(f"벤치마크 yfinance 실패: {code} — {e}")

        if not df.empty:
            # date 컬럼이 문자열이 아닌 경우 변환
            if hasattr(df["date"].iloc[0], "strftime"):
                df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
            result[key] = {
                "dates": df["date"].tolist(),
                "prices": df["close"].tolist(),
            }
        else:
            result[key] = {"dates": [], "prices": []}

    return {"data": result, "error": None}


@router.get("/benchmark/portfolio-series")
def get_portfolio_series(
    period: str = Query("3M"),
    secret: None = Depends(verify_secret),
):
    """시뮬레이션 포트폴리오 일별 시계열 (스냅샷 기반)"""
    from datetime import datetime, timedelta

    from src.core.portfolio_tracker import PortfolioTracker

    days = PERIOD_DAYS.get(period, 90)
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    try:
        tracker = PortfolioTracker()
        snapshots = tracker.get_snapshots(start_date)
        if not snapshots:
            return {"data": {"dates": [], "values": []}, "error": None}

        dates = [s["date"] for s in snapshots]
        values = [s["total_value"] for s in snapshots]
        return {"data": {"dates": dates, "values": values}, "error": None}
    except Exception as e:
        return {"data": {"dates": [], "values": []}, "error": str(e)}
