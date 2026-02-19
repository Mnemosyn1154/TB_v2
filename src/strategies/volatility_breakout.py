from __future__ import annotations

"""
AlgoTrader KR — 변동성 돌파 전략 (Volatility Breakout)

래리 윌리엄스의 변동성 돌파 전략.
오늘 시가 + 전일 (고가 - 저가) × k 이상으로 현재가가 돌파하면 매수,
장 마감 직전에 청산하는 일중 전략.

알고리즘 흐름:
    1. 전일 OHLC 추출 → 목표가 = 오늘 시가 + 전일 (고가 - 저가) × k
    2. 장중 현재가가 목표가 돌파 여부 확인
    3. 돌파 시 매수 (종목당 1회)
    4. 장 마감 직전 보유 종목 전부 청산
    5. 백테스트: 당일 고가 ≥ 목표가이면 목표가에 매수 근사

Depends on:
    - src.strategies.base (BaseStrategy, TradeSignal)
    - src.core.config (전략 파라미터)

Used by:
    - main.py (AlgoTrader)
    - src.backtest.runner (BacktestRunner)

Modification Guide:
    - k 값 조정: settings.yaml의 volatility_breakout.k
    - 유니버스 변경: settings.yaml의 volatility_breakout.universe_codes
    - 청산 시각: kr_close_time / us_close_time 수정
"""

from datetime import datetime
from typing import Any

import pandas as pd
from loguru import logger

from src.strategies.base import BaseStrategy, TradeSignal, Signal
from src.core.config import get_config


class VolatilityBreakoutStrategy(BaseStrategy):
    """
    변동성 돌파 전략 (Larry Williams)

    1. 목표가 = 오늘 시가 + 전일 (고가 - 저가) × k
    2. 현재가 ≥ 목표가 → 매수 (종목당 1회)
    3. 장 마감 직전 → 전량 청산
    """

    needs_ohlc = True  # OHLC DataFrame 필요

    def __init__(self, config_key: str | None = None):
        super().__init__("VolatilityBreakout", config_key=config_key)
        config = get_config()
        vb_config = config["strategies"][self.config_key]

        self.k: float = vb_config.get("k", 0.5)
        self.market: str = vb_config.get("market", "KR")
        self.universe: list[dict[str, str]] = vb_config.get("universe_codes", [])
        self.max_hold_per_stock: int = vb_config.get("max_hold_per_stock", 1)
        self.close_at_market_end: bool = vb_config.get("close_at_market_end", True)
        self.kr_close_time: str = vb_config.get("kr_close_time", "15:15")
        self.us_close_time: str = vb_config.get("us_close_time", "15:45")

        # 상태
        self.today_targets: dict[str, float] = {}
        self.today_entered: set[str] = set()
        self.current_holdings: set[str] = set()
        self.last_calc_date: str = ""

        codes = [u.get("name", u["code"]) for u in self.universe]
        logger.info(
            f"변동성 돌파 전략: k={self.k}, {len(self.universe)}개 종목, "
            f"시장={self.market}"
        )
        logger.info(f"  유니버스: {codes}")

    # ──────────────────────────────────────────────
    # 플러그인 인터페이스
    # ──────────────────────────────────────────────

    def get_config_key(self) -> str:
        return getattr(self, "config_key", "volatility_breakout")

    def required_codes(self) -> list[dict[str, str]]:
        """유니버스 종목 코드 목록"""
        codes = []
        for item in self.universe:
            entry = {"code": item["code"], "market": item.get("market", self.market)}
            if item.get("exchange"):
                entry["exchange"] = item["exchange"]
            codes.append(entry)
        return codes

    def prepare_signal_kwargs(self, price_data: dict[str, pd.DataFrame]) -> dict:
        """
        OHLC DataFrame에서 전일 데이터 + 오늘 데이터 추출.

        Args:
            price_data: {종목코드: DataFrame(date, open, high, low, close, ...)}
                        needs_ohlc=True이므로 full DataFrame이 전달됨

        Returns:
            {"ohlc_data": {code: DataFrame}} 또는 {} (스킵)
        """
        ohlc_data: dict[str, pd.DataFrame] = {}
        min_required = 2  # 최소 2일 (전일 + 오늘)

        for item in self.universe:
            code = item["code"]
            df = price_data.get(code)
            if df is None:
                continue
            # pd.Series인 경우 (호환성) — OHLC가 없으므로 스킵
            if isinstance(df, pd.Series):
                logger.warning(f"[{self.name}] {code}: Series 데이터 — OHLC 필요, 스킵")
                continue
            if len(df) < min_required:
                logger.warning(
                    f"[{self.name}] {code} 스킵: 데이터 부족 — "
                    f"{len(df)}일 (최소 {min_required}일)"
                )
                continue

            ohlc_data[code] = df

        if not ohlc_data:
            logger.warning(f"[{self.name}] 시그널 스킵: 유효한 OHLC 데이터 없음")
            return {}

        return {"ohlc_data": ohlc_data}

    def generate_signals(
        self,
        ohlc_data: dict[str, pd.DataFrame] | None = None,
        current_prices: dict[str, float] | None = None,
        **kwargs,
    ) -> list[TradeSignal]:
        """
        변동성 돌파 신호 생성.

        Args:
            ohlc_data: {종목코드: OHLC DataFrame}
            current_prices: {종목코드: 현재가} — 실시간 모드에서 외부 주입
        """
        if not self.enabled:
            return []

        if ohlc_data is None:
            ohlc_data = kwargs.get("ohlc_data", {})
        if current_prices is None:
            current_prices = kwargs.get("current_prices", {})

        if not ohlc_data:
            return []

        signals: list[TradeSignal] = []

        # 목표가 계산 (하루 1회)
        self._update_targets(ohlc_data)

        if current_prices:
            # === 실시간 모드 ===
            if self._is_close_time():
                return self._generate_close_signals()
            signals.extend(self._check_breakout_live(current_prices))
        else:
            # === 백테스트 모드 ===
            # 기존 보유 청산 (전일 진입 → 오늘 청산)
            signals.extend(self._generate_close_signals_backtest(ohlc_data))
            # 오늘 돌파 확인
            signals.extend(self._check_breakout_backtest(ohlc_data))

        return signals

    # ──────────────────────────────────────────────
    # 목표가 계산
    # ──────────────────────────────────────────────

    def _update_targets(self, ohlc_data: dict[str, pd.DataFrame]) -> None:
        """전일 OHLC로 오늘의 돌파 목표가 계산 (하루 1회)"""
        sample_df = next(iter(ohlc_data.values()))
        if "date" in sample_df.columns:
            today = str(sample_df["date"].iloc[-1])[:10]
        else:
            today = str(sample_df.index[-1])[:10]

        if today == self.last_calc_date:
            return

        self.last_calc_date = today
        self.today_entered = set()
        self.today_targets = {}

        for code, df in ohlc_data.items():
            if len(df) < 2:
                continue

            prev = df.iloc[-2]
            today_row = df.iloc[-1]

            prev_high = float(prev.get("high", 0) if isinstance(prev, dict) else prev["high"])
            prev_low = float(prev.get("low", 0) if isinstance(prev, dict) else prev["low"])
            today_open = float(
                today_row.get("open", 0) if isinstance(today_row, dict) else today_row["open"]
            )

            if prev_high <= 0 or prev_low <= 0 or today_open <= 0:
                continue

            range_val = prev_high - prev_low
            target = today_open + range_val * self.k
            self.today_targets[code] = target

            name = self._get_stock_name(code)
            logger.debug(
                f"[{self.name}] {name}({code}) 목표가: "
                f"{target:,.0f} (시가 {today_open:,.0f} + "
                f"전일레인지 {range_val:,.0f} × {self.k})"
            )

    # ──────────────────────────────────────────────
    # 실시간 모드
    # ──────────────────────────────────────────────

    def _is_close_time(self) -> bool:
        """현재 시간이 장 마감 청산 시각인지 확인"""
        if not self.close_at_market_end:
            return False
        now = datetime.now().strftime("%H:%M")
        close_time = self.kr_close_time if self.market == "KR" else self.us_close_time
        return now >= close_time

    def _check_breakout_live(self, current_prices: dict[str, float]) -> list[TradeSignal]:
        """실시간 모드: 현재가로 돌파 확인"""
        signals: list[TradeSignal] = []

        for code, target in self.today_targets.items():
            if code in self.today_entered:
                continue

            price = current_prices.get(code)
            if price is None:
                continue

            if price >= target:
                market = self._get_stock_market(code)
                name = self._get_stock_name(code)
                signals.append(TradeSignal(
                    strategy=self.name,
                    code=code,
                    market=market,
                    signal=Signal.BUY,
                    price=price,
                    reason=(
                        f"변동성 돌파: {name}({code}) "
                        f"현재가 {price:,.0f} ≥ 목표가 {target:,.0f}"
                    ),
                    metadata={
                        "target_price": target,
                        "current_price": price,
                        "k": self.k,
                    },
                ))
                logger.info(
                    f"[{self.name}] 돌파 감지: {name}({code}) "
                    f"{price:,.0f} ≥ {target:,.0f}"
                )

        return signals

    def _generate_close_signals(self) -> list[TradeSignal]:
        """보유 종목 전량 청산 신호 (실시간 장 마감용)"""
        signals: list[TradeSignal] = []
        for code in list(self.current_holdings):
            market = self._get_stock_market(code)
            name = self._get_stock_name(code)
            signals.append(TradeSignal(
                strategy=self.name,
                code=code,
                market=market,
                signal=Signal.CLOSE,
                reason=f"변동성 돌파: {name}({code}) 장 마감 청산",
                metadata={"role": "market_close"},
            ))
        return signals

    # ──────────────────────────────────────────────
    # 백테스트 모드
    # ──────────────────────────────────────────────

    def _generate_close_signals_backtest(
        self, ohlc_data: dict[str, pd.DataFrame],
    ) -> list[TradeSignal]:
        """백테스트: 기존 보유 종목 청산 (전일 진입 → 오늘 종가 청산 근사)"""
        signals: list[TradeSignal] = []

        for code in list(self.current_holdings):
            market = self._get_stock_market(code)
            name = self._get_stock_name(code)
            signals.append(TradeSignal(
                strategy=self.name,
                code=code,
                market=market,
                signal=Signal.CLOSE,
                reason=f"변동성 돌파(BT): {name}({code}) 당일 청산",
                metadata={"backtest": True},
            ))

        return signals

    def _check_breakout_backtest(
        self, ohlc_data: dict[str, pd.DataFrame],
    ) -> list[TradeSignal]:
        """
        백테스트 모드: 당일 고가 ≥ 목표가이면 목표가에 매수한 것으로 근사.
        """
        signals: list[TradeSignal] = []

        for code, target in self.today_targets.items():
            if code in self.today_entered:
                continue

            df = ohlc_data.get(code)
            if df is None or df.empty:
                continue

            today_row = df.iloc[-1]
            today_high = float(today_row["high"])

            if today_high >= target:
                market = self._get_stock_market(code)
                name = self._get_stock_name(code)
                signals.append(TradeSignal(
                    strategy=self.name,
                    code=code,
                    market=market,
                    signal=Signal.BUY,
                    price=target,
                    reason=(
                        f"변동성 돌파(BT): {name}({code}) "
                        f"고가 {today_high:,.0f} ≥ 목표가 {target:,.0f}"
                    ),
                    metadata={
                        "target_price": target,
                        "today_high": today_high,
                        "k": self.k,
                        "backtest": True,
                    },
                ))

        return signals

    # ──────────────────────────────────────────────
    # 체결 콜백
    # ──────────────────────────────────────────────

    def on_trade_executed(self, signal: TradeSignal, success: bool) -> None:
        """체결 콜백 — 보유/진입 상태 동기화"""
        if not success:
            return

        if signal.signal == Signal.BUY:
            self.today_entered.add(signal.code)
            self.current_holdings.add(signal.code)
            logger.info(f"[{self.name}] 진입: {signal.code}")
        elif signal.signal == Signal.CLOSE:
            self.current_holdings.discard(signal.code)
            logger.info(f"[{self.name}] 청산: {signal.code}")

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
            "today_targets": {
                self._get_stock_name(code): f"{target:,.0f}"
                for code, target in self.today_targets.items()
            },
            "today_entered": list(self.today_entered),
            "last_calc_date": self.last_calc_date,
            "params": {
                "k": self.k,
                "market": self.market,
                "universe_count": len(self.universe),
                "close_at_market_end": self.close_at_market_end,
            },
        }
