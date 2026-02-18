"""
AlgoTrader KR — 데이터 매니저

KIS API → DataFrame 변환 → SQLite 저장/조회를 담당합니다.
DB 스키마: docs/DATA_DICTIONARY.md 참조

Depends on:
    - src.core.config (DB 경로, 디렉토리 상수)
    - src.core.broker (KIS API 호출)
    - sqlalchemy (ORM/DB 엔진)
    - pandas (DataFrame 처리)

Used by:
    - src.execution.collector (데이터 수집 오케스트레이션)
    - src.execution.executor (거래 기록 저장)
    - main.py (전략 실행 시 데이터 로드)

Modification Guide:
    - 새 테이블 추가: _init_db()에 CREATE TABLE 추가 + DATA_DICTIONARY.md 업데이트
    - 새 시장 지원: fetch_xxx_daily() 메서드 추가
    - API 응답 필드 변경: fetch 메서드 내 매핑 딕셔너리 수정
"""
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger
from sqlalchemy import create_engine, text

from src.core.config import get_config, DATA_DIR
from src.core.broker import KISBroker


class DataManager:
    """시세 데이터 수집/정규화/저장"""

    def __init__(self, broker: KISBroker):
        self.broker = broker
        config = get_config()

        # DB 초기화
        db_config = config["database"]
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        db_path = DATA_DIR / "trading_bot.db"
        self.engine = create_engine(f"sqlite:///{db_path}")
        self._init_db()

        logger.info("DataManager 초기화 완료")

    def _init_db(self) -> None:
        """DB 테이블 생성"""
        with self.engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS daily_prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL,
                    market TEXT NOT NULL,
                    date TEXT NOT NULL,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(code, market, date)
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy TEXT NOT NULL,
                    code TEXT NOT NULL,
                    market TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    price REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    reason TEXT
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS sim_positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL UNIQUE,
                    market TEXT NOT NULL,
                    side TEXT NOT NULL DEFAULT 'LONG',
                    quantity INTEGER NOT NULL,
                    entry_price REAL NOT NULL,
                    current_price REAL NOT NULL DEFAULT 0,
                    strategy TEXT NOT NULL DEFAULT '',
                    entry_time TEXT NOT NULL,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS sim_portfolio (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()

    # ──────────────────────────────────────────────
    # 가격 데이터 수집
    # ──────────────────────────────────────────────

    # KIS API 응답 → 정규화 필드 매핑
    _KR_FIELD_MAP = {
        "date": "stck_bsop_date",
        "open": "stck_oprc",
        "high": "stck_hgpr",
        "low": "stck_lwpr",
        "close": "stck_clpr",
        "volume": "acml_vol",
    }
    _US_FIELD_MAP = {
        "date": "xymd",
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "clos",
        "volume": "tvol",
    }

    def _normalize_ohlcv(self, raw: list[dict], field_map: dict[str, str],
                         code: str, market: str) -> pd.DataFrame:
        """KIS API 원시 데이터 → 정규화된 DataFrame"""
        records = []
        for r in raw:
            try:
                records.append({
                    "date": pd.to_datetime(r[field_map["date"]]),
                    "open": float(r[field_map["open"]]),
                    "high": float(r[field_map["high"]]),
                    "low": float(r[field_map["low"]]),
                    "close": float(r[field_map["close"]]),
                    "volume": int(r[field_map["volume"]]),
                })
            except (KeyError, ValueError):
                continue

        df = pd.DataFrame(records)
        if not df.empty:
            df = df.sort_values("date").reset_index(drop=True)
            df["code"] = code
            df["market"] = market

        return df

    def fetch_kr_daily(self, stock_code: str, days: int = 365) -> pd.DataFrame:
        """국내 주식 일봉 데이터 → DataFrame"""
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")

        raw = self.broker.get_kr_daily_prices(stock_code, start_date=start_date, end_date=end_date)
        if not raw:
            logger.warning(f"KR 일봉 데이터 없음: {stock_code}")
            return pd.DataFrame()

        return self._normalize_ohlcv(raw, self._KR_FIELD_MAP, stock_code, "KR")

    def fetch_us_daily(self, ticker: str, exchange: str = "NAS",
                       count: int = 120) -> pd.DataFrame:
        """미국 주식 일봉 데이터 → DataFrame"""
        raw = self.broker.get_us_daily_prices(ticker, exchange=exchange, count=count)
        if not raw:
            logger.warning(f"US 일봉 데이터 없음: {ticker}")
            return pd.DataFrame()

        return self._normalize_ohlcv(raw, self._US_FIELD_MAP, ticker, "US")

    # ──────────────────────────────────────────────
    # DB 저장/조회
    # ──────────────────────────────────────────────

    def save_daily_prices(self, df: pd.DataFrame) -> int:
        """일봉 데이터를 DB에 저장 (중복 무시, 벌크 삽입)"""
        if df.empty:
            return 0

        records = []
        for _, row in df.iterrows():
            try:
                records.append({
                    "code": row["code"],
                    "market": row["market"],
                    "date": row["date"].strftime("%Y-%m-%d"),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": int(row["volume"]),
                })
            except Exception as e:
                logger.warning(f"레코드 변환 스킵: {e}")

        if not records:
            return 0

        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT OR IGNORE INTO daily_prices (code, market, date, open, high, low, close, volume)
                VALUES (:code, :market, :date, :open, :high, :low, :close, :volume)
            """), records)
            conn.commit()

        logger.info(f"DB 저장 완료: {df['code'].iloc[0]} — {len(records)}건")
        return len(records)

    def load_daily_prices(self, code: str, market: str = "KR",
                          days: int = 365) -> pd.DataFrame:
        """DB에서 일봉 데이터 로드"""
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        query = text("""
            SELECT date, open, high, low, close, volume
            FROM daily_prices
            WHERE code = :code AND market = :market AND date >= :start_date
            ORDER BY date ASC
        """)

        df = pd.read_sql(query, self.engine, params={
            "code": code, "market": market, "start_date": start_date,
        })

        if not df.empty:
            df["date"] = pd.to_datetime(df["date"])

        return df

    def save_trade(self, strategy: str, code: str, market: str,
                   side: str, quantity: int, price: float, reason: str = "") -> None:
        """거래 기록 저장"""
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO trades (strategy, code, market, side, quantity, price, timestamp, reason)
                VALUES (:strategy, :code, :market, :side, :quantity, :price, :timestamp, :reason)
            """), {
                "strategy": strategy,
                "code": code,
                "market": market,
                "side": side,
                "quantity": quantity,
                "price": price,
                "timestamp": datetime.now().isoformat(),
                "reason": reason,
            })
            conn.commit()
