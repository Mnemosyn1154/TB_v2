from __future__ import annotations

"""S&P 500 유니버스 자동 갱신 모듈

Wikipedia에서 S&P 500 구성종목을 가져오고, yfinance로 필터링하여
DB에 캐시합니다. quant_factor 전략에서 유니버스로 사용됩니다.

Depends on:
    - src.core.config (DATA_DIR)
    - pandas, yfinance (데이터 수집)
    - sqlalchemy (DB 캐시)

Used by:
    - src.strategies.quant_factor (유니버스 로딩)
    - pyapi.routers.universe (API 엔드포인트)

Modification Guide:
    - 필터 조건 추가: _filter_and_enrich()의 Phase 1/2에 조건 추가
    - 새 유니버스 소스: get_stocks()에 분기 추가
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import pandas as pd
from loguru import logger
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.core.config import DATA_DIR

_SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

# yfinance exchange → KIS query exchange 매핑
_YF_EXCHANGE_MAP = {
    "NMS": "NAS", "NGM": "NAS", "NCM": "NAS",  # NASDAQ variants
    "NYQ": "NYS",                                  # NYSE
    "PCX": "AMS", "ASE": "AMS",                   # AMEX/Arca
    "BTS": "NYS",                                  # BATS → NYS
}


class UniverseManager:
    """S&P 500 유니버스 관리 — fetch, filter, cache"""

    def __init__(self, engine: Engine | None = None):
        if engine is not None:
            self.engine = engine
        else:
            db_path = DATA_DIR / "trading_bot.db"
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            self.engine = create_engine(f"sqlite:///{db_path}")

        self._init_tables()

    def _init_tables(self) -> None:
        """universe_cache, universe_meta 테이블 생성 (멱등)"""
        with self.engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS universe_cache (
                    ticker TEXT NOT NULL,
                    name TEXT NOT NULL DEFAULT '',
                    market TEXT NOT NULL DEFAULT 'US',
                    exchange TEXT NOT NULL DEFAULT 'NYS',
                    sector TEXT NOT NULL DEFAULT '',
                    market_cap REAL DEFAULT 0,
                    avg_volume REAL DEFAULT 0,
                    last_price REAL DEFAULT 0,
                    source TEXT NOT NULL DEFAULT 'sp500',
                    refreshed_at TEXT NOT NULL,
                    UNIQUE(ticker, source)
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS universe_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """))
            conn.commit()

    # ──────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────

    def get_stocks(self, config: dict | None = None) -> list[dict]:
        """메인 진입점: 유니버스 종목 목록 반환

        Args:
            config: universe 설정 블록 (settings.yaml quant_factor.universe)

        Returns:
            [{"code": "AAPL", "market": "US", "exchange": "NAS", "name": "Apple"}, ...]
        """
        config = config or {}
        source = config.get("source", "manual")

        if source == "manual":
            return config.get("manual_codes", [])

        if source == "sp500":
            try:
                interval = config.get("refresh_interval_days", 7)
                if self._is_cache_fresh(interval):
                    return self.load_from_cache("sp500")

                if config.get("auto_refresh", True):
                    return self.refresh(config)

                cached = self.load_from_cache("sp500")
                if cached:
                    return cached
            except Exception as e:
                logger.warning(f"S&P 500 유니버스 로딩 실패: {e}")
                cached = self.load_from_cache("sp500")
                if cached:
                    logger.info(f"캐시에서 {len(cached)}개 종목 사용")
                    return cached

            # 최종 fallback
            logger.warning("S&P 500 캐시 없음 → manual_codes fallback")
            return config.get("manual_codes", [])

        return config.get("manual_codes", [])

    def refresh(self, config: dict | None = None) -> list[dict]:
        """강제 갱신: Wikipedia fetch → yfinance 필터 → DB 저장"""
        config = config or {}
        filters = config.get("filters", {})

        logger.info("S&P 500 유니버스 갱신 시작...")

        tickers = self._fetch_sp500_tickers()
        if not tickers:
            raise RuntimeError("Wikipedia에서 S&P 500 목록을 가져올 수 없습니다")

        logger.info(f"Wikipedia에서 {len(tickers)}개 티커 가져옴")

        stocks = self._filter_and_enrich(tickers, filters)
        if not stocks:
            raise RuntimeError("필터링 후 종목이 0개입니다")

        self._save_to_cache(stocks, "sp500")
        logger.info(f"S&P 500 유니버스 갱신 완료: {len(stocks)}개 종목")

        return self.load_from_cache("sp500")

    def preview(self, filters: dict | None = None) -> list[dict]:
        """필터 파라미터로 S&P 500 프리뷰 (캐시 저장 안함)"""
        tickers = self._fetch_sp500_tickers()
        if not tickers:
            raise RuntimeError("Wikipedia에서 S&P 500 목록을 가져올 수 없습니다")

        stocks = self._filter_and_enrich(tickers, filters or {})
        return [
            {
                "code": s["ticker"], "market": "US",
                "exchange": s.get("exchange", "NYS"),
                "name": s.get("name", ""),
                "sector": s.get("sector", ""),
                "market_cap": s.get("market_cap", 0),
                "avg_volume": s.get("avg_volume", 0),
                "last_price": s.get("last_price", 0),
            }
            for s in stocks
        ]

    def get_status(self) -> dict:
        """캐시 상태 반환"""
        cached = self.load_from_cache("sp500")
        last_refresh = self._get_meta("sp500_last_refresh")

        age_days = None
        if last_refresh:
            try:
                dt = datetime.fromisoformat(last_refresh)
                age_days = (datetime.now(timezone.utc) - dt.replace(tzinfo=timezone.utc)).days
            except (ValueError, TypeError):
                pass

        return {
            "stock_count": len(cached),
            "last_refresh": last_refresh,
            "cache_age_days": age_days,
        }

    # ──────────────────────────────────────────────
    # Data Fetching
    # ──────────────────────────────────────────────

    def _fetch_sp500_tickers(self) -> list[str]:
        """Wikipedia에서 S&P 500 티커 목록 가져오기"""
        try:
            import urllib.request

            req = urllib.request.Request(_SP500_URL, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                html = resp.read()
            tables = pd.read_html(html)
            df = tables[0]
            tickers = df["Symbol"].tolist()
            # BRK.B → BRK-B (yfinance 호환)
            tickers = [t.replace(".", "-") for t in tickers]
            return tickers
        except Exception as e:
            logger.error(f"Wikipedia S&P 500 fetch 실패: {e}")
            return []

    def _filter_and_enrich(self, tickers: list[str], filters: dict) -> list[dict]:
        """2단계 필터링으로 유니버스 구축

        Phase 1: 배치 다운로드로 price/volume 필터 (빠름)
        Phase 2: 개별 info 호출로 market_cap/exchange/sector 수집 (느림, 소수만)
        """
        import yfinance as yf

        min_price = filters.get("min_price", 10)
        min_volume = filters.get("min_avg_daily_volume", 10_000_000)
        min_cap = filters.get("min_market_cap", 5_000_000_000)

        # Phase 1: 배치 다운로드
        logger.info(f"Phase 1: {len(tickers)}개 종목 배치 다운로드...")
        try:
            data = yf.download(tickers, period="1mo", progress=False, threads=True)
        except Exception as e:
            logger.error(f"yf.download 실패: {e}")
            return []

        passed_phase1: list[str] = []

        for ticker in tickers:
            try:
                if len(tickers) > 1 and isinstance(data.columns, pd.MultiIndex):
                    close = data["Close"][ticker].dropna()
                    volume = data["Volume"][ticker].dropna()
                else:
                    close = data["Close"].dropna()
                    volume = data["Volume"].dropna()

                if close.empty or volume.empty:
                    continue

                last_price = float(close.iloc[-1])
                avg_vol_dollar = float(volume.mean()) * last_price

                if last_price >= min_price and avg_vol_dollar >= min_volume:
                    passed_phase1.append(ticker)
            except Exception:
                continue

        logger.info(f"Phase 1 통과: {len(passed_phase1)}/{len(tickers)}개")

        # Phase 2: 개별 info 호출 (남은 종목만)
        logger.info(f"Phase 2: {len(passed_phase1)}개 종목 상세 정보 수집...")
        stocks: list[dict] = []

        def _fetch_info(ticker: str) -> dict | None:
            try:
                info = yf.Ticker(ticker).info
                cap = info.get("marketCap", 0) or 0
                if cap < min_cap:
                    return None

                yf_exchange = info.get("exchange", "")
                exchange = _YF_EXCHANGE_MAP.get(yf_exchange, "NYS")

                return {
                    "ticker": ticker,
                    "name": info.get("shortName", ""),
                    "exchange": exchange,
                    "sector": info.get("sector", ""),
                    "market_cap": cap,
                    "avg_volume": info.get("averageVolume", 0) or 0,
                    "last_price": info.get("currentPrice") or info.get("regularMarketPrice", 0) or 0,
                }
            except Exception as e:
                logger.debug(f"{ticker} info 실패: {e}")
                return None

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(_fetch_info, t): t for t in passed_phase1}
            for future in as_completed(futures):
                result = future.result()
                if result is not None:
                    stocks.append(result)

        logger.info(f"Phase 2 통과: {len(stocks)}/{len(passed_phase1)}개")
        return stocks

    # ──────────────────────────────────────────────
    # Cache
    # ──────────────────────────────────────────────

    def _save_to_cache(self, stocks: list[dict], source: str) -> None:
        """DB에 유니버스 캐시 저장 (upsert)"""
        now = datetime.now(timezone.utc).isoformat()

        with self.engine.connect() as conn:
            # 기존 캐시 삭제
            conn.execute(text("DELETE FROM universe_cache WHERE source = :source"),
                         {"source": source})

            for s in stocks:
                conn.execute(text("""
                    INSERT INTO universe_cache
                        (ticker, name, market, exchange, sector, market_cap,
                         avg_volume, last_price, source, refreshed_at)
                    VALUES (:ticker, :name, 'US', :exchange, :sector, :market_cap,
                            :avg_volume, :last_price, :source, :refreshed_at)
                """), {
                    "ticker": s["ticker"],
                    "name": s.get("name", ""),
                    "exchange": s.get("exchange", "NYS"),
                    "sector": s.get("sector", ""),
                    "market_cap": s.get("market_cap", 0),
                    "avg_volume": s.get("avg_volume", 0),
                    "last_price": s.get("last_price", 0),
                    "source": source,
                    "refreshed_at": now,
                })

            # 메타 업데이트
            conn.execute(text("""
                INSERT OR REPLACE INTO universe_meta (key, value)
                VALUES (:key, :value)
            """), {"key": f"{source}_last_refresh", "value": now})

            conn.commit()

    def load_from_cache(self, source: str) -> list[dict]:
        """DB 캐시에서 종목 목록 읽기"""
        with self.engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT ticker, name, market, exchange, sector, market_cap, "
                "avg_volume, last_price FROM universe_cache WHERE source = :source"
            ), {"source": source}).fetchall()

        return [
            {
                "code": r[0],
                "market": r[2],
                "exchange": r[3],
                "name": r[1],
                "sector": r[4],
                "market_cap": r[5],
                "avg_volume": r[6],
                "last_price": r[7],
            }
            for r in rows
        ]

    def _is_cache_fresh(self, interval_days: int) -> bool:
        """캐시 TTL 체크"""
        last_refresh = self._get_meta("sp500_last_refresh")
        if not last_refresh:
            return False

        try:
            dt = datetime.fromisoformat(last_refresh)
            age = datetime.now(timezone.utc) - dt.replace(tzinfo=timezone.utc)
            return age.days < interval_days
        except (ValueError, TypeError):
            return False

    def _get_meta(self, key: str) -> str | None:
        """universe_meta 테이블에서 값 조회"""
        with self.engine.connect() as conn:
            row = conn.execute(
                text("SELECT value FROM universe_meta WHERE key = :key"),
                {"key": key},
            ).fetchone()
        return row[0] if row else None
