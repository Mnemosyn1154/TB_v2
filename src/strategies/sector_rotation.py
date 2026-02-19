from __future__ import annotations

"""
AlgoTrader KR — 섹터 로테이션 전략 (Sector Rotation)

미국/한국 섹터 ETF 중 모멘텀 상위 N개에 투자.
절대 모멘텀 필터로 하락장 방어 (수익률 < 무위험수익률 → 안전자산 전환).

알고리즘 흐름:
    1. 각 섹터 ETF의 N개월 수익률 계산
    2. 수익률 내림차순 정렬 → 상위 top_n개 선택
    3. 절대 모멘텀: 수익률 < risk_free_rate → 안전자산(SHY) 대체
    4. 기존 보유와 비교 → CLOSE/BUY 신호 생성
    5. 매월 리밸런싱

Depends on:
    - src.strategies.base (BaseStrategy, TradeSignal)
    - src.core.config (전략 파라미터)

Used by:
    - main.py (AlgoTrader)
    - src.backtest.runner (BacktestRunner)

Modification Guide:
    - 섹터 추가/삭제: settings.yaml의 sector_rotation.sectors 리스트 수정
    - 투자 섹터 수: top_n 파라미터 조정
    - 룩백 기간: lookback_months 조정
"""
from datetime import datetime
from typing import Any

import pandas as pd
from loguru import logger

from src.strategies.base import BaseStrategy, TradeSignal, Signal
from src.core.config import get_config


class SectorRotationStrategy(BaseStrategy):
    """
    섹터 로테이션 전략

    1. 각 섹터 ETF의 N개월 모멘텀 계산
    2. 상위 top_n개 섹터 선택
    3. 절대 모멘텀 필터: 수익률 < 무위험수익률 → 안전자산
    4. 매월 리밸런싱
    """

    def __init__(self, config_key: str | None = None):
        super().__init__("SectorRotation", config_key=config_key)
        config = get_config()
        sr_config = config["strategies"][self.config_key]

        self.lookback_months = sr_config["lookback_months"]
        self.rebalance_day = sr_config["rebalance_day"]
        self.top_n = sr_config["top_n"]
        self.risk_free_rate = sr_config["risk_free_rate"]
        self.safe_asset = sr_config["safe_asset"]
        self.safe_asset_exchange = sr_config.get("safe_asset_exchange", "")

        # 섹터 목록 로드
        self.sectors: list[dict[str, str]] = sr_config["sectors"]

        # 현재 상태
        self.current_holdings: set[str] = set()  # 현재 보유 종목 코드
        self.sector_returns: dict[str, float] = {}  # 최근 계산된 섹터별 수익률

        sector_names = [s.get("name", s["code"]) for s in self.sectors]
        logger.info(
            f"섹터 로테이션 전략: {len(self.sectors)}개 섹터, "
            f"상위 {self.top_n}개 투자, 룩백={self.lookback_months}개월"
        )
        logger.info(f"  섹터: {sector_names}")

    # ──────────────────────────────────────────────
    # 플러그인 인터페이스
    # ──────────────────────────────────────────────

    def get_config_key(self) -> str:
        return getattr(self, "config_key", "sector_rotation")

    def required_codes(self) -> list[dict[str, str]]:
        """섹터 ETF + 안전자산 코드 목록"""
        codes = []
        for sector in self.sectors:
            entry = {"code": sector["code"], "market": sector["market"]}
            if sector.get("exchange"):
                entry["exchange"] = sector["exchange"]
            codes.append(entry)

        # 안전자산
        safe_entry = {"code": self.safe_asset, "market": "US"}
        if self.safe_asset_exchange:
            safe_entry["exchange"] = self.safe_asset_exchange
        codes.append(safe_entry)

        return codes

    def prepare_signal_kwargs(self, price_data: dict[str, pd.Series]) -> dict:
        """가격 데이터 검증 후 전달"""
        sector_prices: dict[str, pd.Series] = {}
        min_required = 60

        for sector in self.sectors:
            code = sector["code"]
            prices = price_data.get(code)
            if prices is None:
                logger.warning(f"[{self.name}] 섹터 {sector.get('name', code)} 스킵: 데이터 없음")
                continue
            if len(prices) < min_required:
                logger.warning(
                    f"[{self.name}] 섹터 {sector.get('name', code)} 스킵: "
                    f"데이터 부족 — {len(prices)}일 (최소 {min_required}일)"
                )
                continue
            sector_prices[code] = prices

        if not sector_prices:
            logger.warning(f"[{self.name}] 시그널 스킵: 유효한 섹터 데이터 없음")
            return {}

        return {"sector_prices": sector_prices}

    def should_skip_date(self, date: str, equity_history: list[dict]) -> bool:
        """월별 리밸런싱: 매월 1회만 실행"""
        if not equity_history:
            return False

        last_date = equity_history[-1]["date"]
        try:
            current = datetime.strptime(date, "%Y-%m-%d")
            previous = datetime.strptime(last_date, "%Y-%m-%d")
            if current.year == previous.year and current.month == previous.month:
                return True
            return False
        except Exception:
            return False

    # ──────────────────────────────────────────────
    # 수익률 계산
    # ──────────────────────────────────────────────

    def calculate_return(self, prices: pd.Series, months: int = 6) -> float:
        """N개월 수익률 계산"""
        if prices.empty or len(prices) < 20:
            return 0.0

        trading_days = months * 21
        if len(prices) < trading_days:
            trading_days = len(prices) - 1

        if trading_days <= 0:
            return 0.0

        current = prices.iloc[-1]
        past = prices.iloc[-trading_days]

        if past == 0:
            return 0.0

        return (current - past) / past

    # ──────────────────────────────────────────────
    # 신호 생성
    # ──────────────────────────────────────────────

    def generate_signals(self, sector_prices: dict[str, pd.Series] | None = None,
                         **kwargs) -> list[TradeSignal]:
        """
        섹터 로테이션 신호 생성

        Args:
            sector_prices: {섹터코드: 종가 시리즈}
        """
        if not self.enabled:
            return []

        if sector_prices is None:
            sector_prices = kwargs.get("sector_prices", {})

        if not sector_prices:
            return []

        # 1. 각 섹터 모멘텀 계산
        self.sector_returns = {}
        for code, prices in sector_prices.items():
            self.sector_returns[code] = self.calculate_return(prices, self.lookback_months)

        # 2. 수익률 내림차순 정렬
        ranked = sorted(self.sector_returns.items(), key=lambda x: x[1], reverse=True)

        logger.info(f"📊 섹터 모멘텀 랭킹:")
        for i, (code, ret) in enumerate(ranked):
            name = self._get_sector_name(code)
            marker = " ← TOP" if i < self.top_n else ""
            logger.info(f"  {i+1}. {name}({code}): {ret*100:+.1f}%{marker}")

        # 3. 상위 top_n 선택 + 절대 모멘텀 필터
        new_holdings: set[str] = set()
        for code, ret in ranked[:self.top_n]:
            if ret > self.risk_free_rate:
                new_holdings.add(code)
            else:
                new_holdings.add(self.safe_asset)
                name = self._get_sector_name(code)
                logger.info(
                    f"  ⚠️ {name}({code}) 수익률 {ret*100:+.1f}% < "
                    f"무위험 {self.risk_free_rate*100:.1f}% → 안전자산({self.safe_asset}) 대체"
                )

        # 4. 기존 보유와 비교
        if new_holdings == self.current_holdings:
            logger.info(f"섹터 로테이션: 변동 없음 — 유지 ({self.current_holdings})")
            return []

        signals: list[TradeSignal] = []

        # 5. 빠진 종목 → CLOSE
        to_close = self.current_holdings - new_holdings
        for code in to_close:
            market = self._get_sector_market(code)
            signals.append(TradeSignal(
                strategy=self.name,
                code=code,
                market=market,
                signal=Signal.CLOSE,
                reason=f"섹터 로테이션: {self._get_sector_name(code)} 제외",
                metadata={"role": "close"},
            ))

        # 6. 새 종목 → BUY
        to_buy = new_holdings - self.current_holdings
        for code in to_buy:
            market = self._get_sector_market(code)
            ret = self.sector_returns.get(code, 0.0)
            signals.append(TradeSignal(
                strategy=self.name,
                code=code,
                market=market,
                signal=Signal.BUY,
                reason=(
                    f"섹터 로테이션: {self._get_sector_name(code)} 진입 "
                    f"(모멘텀 {ret*100:+.1f}%)"
                ),
                metadata={
                    "target_code": code,
                    "momentum": ret,
                },
            ))

        old_names = {self._get_sector_name(c) for c in self.current_holdings}
        new_names = {self._get_sector_name(c) for c in new_holdings}
        logger.info(f"🔄 섹터 리밸런싱: {old_names or '{없음}'} → {new_names}")

        return signals

    def on_trade_executed(self, signal: TradeSignal, success: bool) -> None:
        """체결 콜백 — 보유 종목 상태 동기화"""
        if not success:
            return

        if signal.signal == Signal.BUY:
            self.current_holdings.add(signal.code)
            logger.info(f"[SectorRotation] 보유 추가: {signal.code}")
        elif signal.signal == Signal.CLOSE:
            self.current_holdings.discard(signal.code)
            logger.info(f"[SectorRotation] 보유 제거: {signal.code}")

    # ──────────────────────────────────────────────
    # 유틸리티
    # ──────────────────────────────────────────────

    def _get_sector_name(self, code: str) -> str:
        """코드 → 섹터 이름"""
        if code == self.safe_asset:
            return "안전자산"
        for sector in self.sectors:
            if sector["code"] == code:
                return sector.get("name", code)
        return code

    def _get_sector_market(self, code: str) -> str:
        """코드 → 시장"""
        if code == self.safe_asset:
            return "US"
        for sector in self.sectors:
            if sector["code"] == code:
                return sector["market"]
        return "US"

    def get_status(self) -> dict[str, Any]:
        """현재 전략 상태"""
        return {
            "strategy": self.name,
            "enabled": self.enabled,
            "current_holdings": list(self.current_holdings),
            "sector_returns": {
                self._get_sector_name(code): f"{ret*100:+.1f}%"
                for code, ret in sorted(
                    self.sector_returns.items(), key=lambda x: x[1], reverse=True
                )
            },
            "params": {
                "lookback_months": self.lookback_months,
                "top_n": self.top_n,
                "risk_free_rate": f"{self.risk_free_rate*100:.1f}%",
                "safe_asset": self.safe_asset,
            },
        }
