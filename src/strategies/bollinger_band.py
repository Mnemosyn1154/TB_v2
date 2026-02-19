from __future__ import annotations

"""
AlgoTrader KR — 볼린저 밴드 전략 (Bollinger Band Mean Reversion)

볼린저 밴드 평균 회귀 전략.
종가가 하단 밴드 아래로 내려가면 과매도로 판단하여 매수,
상단 밴드 위로 올라가면 과매수로 판단하여 청산.

알고리즘 흐름:
    1. SMA(N) 계산 (N일 이동평균)
    2. 상단 밴드 = SMA + K × σ(N)
    3. 하단 밴드 = SMA - K × σ(N)
    4. 종가 < 하단 밴드 → BUY (과매도 → 반등 기대)
    5. 종가 > 상단 밴드 → CLOSE (과매수 → 차익 실현)
    6. %B, Bandwidth를 metadata에 포함

Depends on:
    - src.strategies.base (BaseStrategy, TradeSignal)
    - src.core.config (전략 파라미터)

Used by:
    - main.py (AlgoTrader)
    - src.backtest.runner (BacktestRunner)

Modification Guide:
    - SMA 기간 조정: settings.yaml의 bollinger_band.window
    - 표준편차 배수: settings.yaml의 bollinger_band.num_std
    - 유니버스 변경: settings.yaml의 bollinger_band.universe_codes
"""

from typing import Any

import pandas as pd
from loguru import logger

from src.strategies.base import BaseStrategy, TradeSignal, Signal
from src.core.config import get_config


class BollingerBandStrategy(BaseStrategy):
    """
    볼린저 밴드 평균 회귀 전략

    1. 상단 밴드 = SMA(N) + K × σ(N)
    2. 하단 밴드 = SMA(N) - K × σ(N)
    3. 종가 < 하단 밴드 → BUY (과매도)
    4. 종가 > 상단 밴드 → CLOSE (과매수)
    """

    def __init__(self, config_key: str | None = None):
        super().__init__("BollingerBand", config_key=config_key)
        config = get_config()
        bb_config = config["strategies"][self.config_key]

        self.window: int = bb_config.get("window", 20)
        self.num_std: float = bb_config.get("num_std", 2.0)
        self.market: str = bb_config.get("market", "KR")
        self.universe: list[dict[str, str]] = bb_config.get("universe_codes", [])
        self.max_hold_per_stock: int = bb_config.get("max_hold_per_stock", 1)

        # 상태
        self.current_holdings: set[str] = set()

        codes = [u.get("name", u["code"]) for u in self.universe]
        logger.info(
            f"볼린저 밴드 전략: window={self.window}, num_std={self.num_std}, "
            f"{len(self.universe)}개 종목, 시장={self.market}"
        )
        logger.info(f"  유니버스: {codes}")

    # ──────────────────────────────────────────────
    # 플러그인 인터페이스
    # ──────────────────────────────────────────────

    def get_config_key(self) -> str:
        return getattr(self, "config_key", "bollinger_band")

    def required_codes(self) -> list[dict[str, str]]:
        """유니버스 종목 코드 목록"""
        codes = []
        for item in self.universe:
            entry = {"code": item["code"], "market": item.get("market", self.market)}
            if item.get("exchange"):
                entry["exchange"] = item["exchange"]
            codes.append(entry)
        return codes

    def prepare_signal_kwargs(self, price_data: dict[str, pd.Series]) -> dict:
        """
        종가 Series를 generate_signals()에 전달할 kwargs로 변환.

        Args:
            price_data: {종목코드: 종가 시리즈}

        Returns:
            {"close_data": {code: Series}} 또는 {} (스킵)
        """
        close_data: dict[str, pd.Series] = {}

        for item in self.universe:
            code = item["code"]
            series = price_data.get(code)
            if series is None:
                continue
            if not isinstance(series, pd.Series):
                logger.warning(f"[{self.name}] {code}: Series가 아님, 스킵")
                continue
            if len(series) < self.window:
                logger.warning(
                    f"[{self.name}] {code} 스킵: 데이터 부족 — "
                    f"{len(series)}일 (최소 {self.window}일)"
                )
                continue

            close_data[code] = series

        if not close_data:
            logger.warning(f"[{self.name}] 시그널 스킵: 유효한 종가 데이터 없음")
            return {}

        return {"close_data": close_data}

    def generate_signals(
        self,
        close_data: dict[str, pd.Series] | None = None,
        **kwargs,
    ) -> list[TradeSignal]:
        """
        볼린저 밴드 시그널 생성.

        Args:
            close_data: {종목코드: 종가 Series}
        """
        if not self.enabled:
            return []

        if close_data is None:
            close_data = kwargs.get("close_data", {})

        if not close_data:
            return []

        signals: list[TradeSignal] = []

        for code, prices in close_data.items():
            if len(prices) < self.window:
                continue

            sma = prices.rolling(window=self.window).mean()
            std = prices.rolling(window=self.window).std()

            current_sma = float(sma.iloc[-1])
            current_std = float(std.iloc[-1])
            upper_band = current_sma + self.num_std * current_std
            lower_band = current_sma - self.num_std * current_std
            close_price = float(prices.iloc[-1])

            # %B = (종가 - 하단밴드) / (상단밴드 - 하단밴드)
            band_width_val = upper_band - lower_band
            if band_width_val > 0:
                percent_b = (close_price - lower_band) / band_width_val
                bandwidth = band_width_val / current_sma
            else:
                percent_b = 0.5
                bandwidth = 0.0

            metadata = {
                "sma": round(current_sma, 2),
                "upper_band": round(upper_band, 2),
                "lower_band": round(lower_band, 2),
                "percent_b": round(percent_b, 4),
                "bandwidth": round(bandwidth, 4),
            }

            market = self._get_stock_market(code)
            name = self._get_stock_name(code)

            if close_price < lower_band and code not in self.current_holdings:
                signals.append(TradeSignal(
                    strategy=self.name,
                    code=code,
                    market=market,
                    signal=Signal.BUY,
                    price=close_price,
                    reason=(
                        f"볼린저 밴드: {name}({code}) "
                        f"종가 {close_price:,.0f} < 하단밴드 {lower_band:,.0f} (과매도)"
                    ),
                    metadata=metadata,
                ))
                logger.info(
                    f"[{self.name}] BUY: {name}({code}) "
                    f"종가 {close_price:,.0f} < 하단 {lower_band:,.0f}"
                )

            elif close_price > upper_band and code in self.current_holdings:
                signals.append(TradeSignal(
                    strategy=self.name,
                    code=code,
                    market=market,
                    signal=Signal.CLOSE,
                    price=close_price,
                    reason=(
                        f"볼린저 밴드: {name}({code}) "
                        f"종가 {close_price:,.0f} > 상단밴드 {upper_band:,.0f} (과매수)"
                    ),
                    metadata=metadata,
                ))
                logger.info(
                    f"[{self.name}] CLOSE: {name}({code}) "
                    f"종가 {close_price:,.0f} > 상단 {upper_band:,.0f}"
                )

        return signals

    # ──────────────────────────────────────────────
    # 체결 콜백
    # ──────────────────────────────────────────────

    def on_trade_executed(self, signal: TradeSignal, success: bool) -> None:
        """체결 콜백 — 보유 종목 동기화"""
        if not success:
            return

        if signal.signal == Signal.BUY:
            self.current_holdings.add(signal.code)
            logger.info(f"[{self.name}] 매수 체결: {signal.code}")
        elif signal.signal == Signal.CLOSE:
            self.current_holdings.discard(signal.code)
            logger.info(f"[{self.name}] 청산 체결: {signal.code}")

    # ──────────────────────────────────────────────
    # 유틸리티
    # ──────────────────────────────────────────────

    def _get_stock_name(self, code: str) -> str:
        """코드 → 종목명"""
        for item in self.universe:
            if item["code"] == code:
                return item.get("name", code)
        return code

    def _get_stock_market(self, code: str) -> str:
        """코드 → 시장"""
        for item in self.universe:
            if item["code"] == code:
                return item.get("market", self.market)
        return self.market

    def get_status(self) -> dict[str, Any]:
        """현재 전략 상태"""
        return {
            "strategy": self.name,
            "enabled": self.enabled,
            "current_holdings": list(self.current_holdings),
            "params": {
                "window": self.window,
                "num_std": self.num_std,
                "market": self.market,
                "universe_count": len(self.universe),
                "max_hold_per_stock": self.max_hold_per_stock,
            },
        }
