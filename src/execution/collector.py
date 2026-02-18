"""
AlgoTrader KR — 데이터 수집 오케스트레이터

전략별 필요 데이터를 KIS API로 수집하여 DB에 저장합니다.
KIS API 실패 시 yfinance를 fallback 데이터 소스로 사용합니다.

Depends on:
    - src.core.config (설정 로드)
    - src.core.broker (KIS API 호출)
    - src.core.data_manager (DB 저장)
    - src.core.data_feed (yfinance fallback — 선택적)
    - src.strategies.base (BaseStrategy — required_codes)

Used by:
    - main.py (AlgoTrader.run_once)

Modification Guide:
    - 새 전략 추가 시 수정 불필요 — required_codes()가 종목을 자동 제공.
    - 거래소 매핑: settings.yaml의 exchange 필드 → src.core.exchange 유틸리티 사용.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from loguru import logger

from src.core.broker import KISBroker
from src.core.data_manager import DataManager
from src.core.exchange import get_us_exchange
from src.strategies.base import BaseStrategy


class DataCollector:
    """
    전략별 필요 데이터를 수집하고 DB에 저장하는 오케스트레이터.

    역할:
        - 활성 전략들의 required_codes()를 합산하여 필요 종목 파악
        - KISBroker를 통해 시세 데이터 수집
        - KIS API 실패 시 yfinance fallback
        - DataManager를 통해 SQLite에 저장
    """

    def __init__(self, broker: KISBroker, data_manager: DataManager,
                 strategies: list[BaseStrategy] | None = None):
        self.broker = broker
        self.data_manager = data_manager
        self.strategies = strategies or []

        # yfinance fallback (선택적 — 미설치 시에도 정상 동작)
        try:
            from src.core.data_feed import DataFeed
            self._data_feed = DataFeed()
        except (ImportError, Exception):
            self._data_feed = None

        logger.info("DataCollector 초기화 완료")

    def collect_all(self) -> None:
        """모든 활성 전략에 필요한 데이터를 일괄 수집합니다."""
        logger.info("📥 데이터 수집 시작...")

        # 전략별 required_codes()를 합산 → 중복 제거
        all_codes: dict[str, dict[str, str]] = {}  # code → {market, exchange}
        for strategy in self.strategies:
            for item in strategy.required_codes():
                code = item["code"]
                all_codes[code] = {
                    "market": item["market"],
                    "exchange": item.get("exchange", ""),
                }

        if not all_codes:
            logger.warning("수집할 종목이 없습니다.")
            return

        # yfinance fallback용 날짜 범위
        yf_end = datetime.now().strftime("%Y-%m-%d")
        yf_start = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

        # 종목별 데이터 수집
        success = 0
        for code, info in all_codes.items():
            market = info["market"]
            try:
                if market == "KR":
                    df = self.data_manager.fetch_kr_daily(code)
                    self.data_manager.save_daily_prices(df)
                elif market == "US":
                    exchange = info.get("exchange") or get_us_exchange(code)
                    df = self.data_manager.fetch_us_daily(code, exchange=exchange)
                    self.data_manager.save_daily_prices(df)
                success += 1
            except Exception as e:
                logger.warning(f"  ⚠ KIS 수집 실패: {code} ({market}) — {e}")
                # yfinance fallback
                if self._data_feed:
                    try:
                        df = self._data_feed.fetch(code, yf_start, yf_end, market=market)
                        if not df.empty:
                            self.data_manager.save_daily_prices(df)
                            success += 1
                            logger.info(f"  ✅ yfinance fallback 성공: {code} ({market}) — {len(df)}건")
                            continue
                    except Exception as yf_err:
                        logger.warning(f"  ⚠ yfinance fallback 실패: {code} ({market}) — {yf_err}")

        logger.info(f"✅ 데이터 수집 완료 ({success}/{len(all_codes)}종목)")
