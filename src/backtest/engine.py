from __future__ import annotations

"""
AlgoTrader KR — 백테스팅 엔진

이벤트 드리븐 방식으로 과거 데이터에 대해 전략을 시뮬레이션합니다.
일별 루프: 가격 업데이트 → 손절 체크 → 전략 신호 → 리스크 검증 → 가상 체결

Depends on:
    - src.strategies.base (BaseStrategy, TradeSignal, Signal)
    - src.core.risk_manager (RiskManager, Position)
    - src.core.config (백테스트 설정)

Used by:
    - main.py (CLI backtest 커맨드)

Modification Guide:
    - 분봉 백테스트: _simulate_day()를 시간 단위로 세분화
    - 실시간 체결 시뮬레이션: _execute_signal()에 체결량 모델 추가
    - 새 전략 백테스트: 전략이 prepare_signal_kwargs() 구현하면 자동 호환
"""
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger

from src.core.risk_manager import RiskManager, Position
from src.strategies.base import BaseStrategy, TradeSignal, Signal


# ──────────────────────────────────────────────
# 데이터 클래스
# ──────────────────────────────────────────────

@dataclass
class Trade:
    """체결된 거래 기록"""
    date: str
    strategy: str
    code: str
    market: str
    side: str               # "BUY" / "SELL"
    quantity: int
    price: float
    commission: float
    slippage: float
    net_amount: float        # 실제 비용/수입 (수수료+슬리피지 반영)
    reason: str = ""

    # 청산 시 계산되는 필드
    pnl: float = 0.0        # 실현 손익
    pnl_pct: float = 0.0    # 수익률 (%)
    holding_days: int = 0    # 보유일수


@dataclass
class BacktestResult:
    """백테스트 결과"""
    strategy_name: str
    start_date: str
    end_date: str
    initial_capital: float

    # 시계열 데이터
    equity_curve: pd.Series = None          # 일별 총 자산
    daily_returns: pd.Series = None         # 일별 수익률

    # 거래 기록
    trades: list[Trade] = field(default_factory=list)

    # 최종 상태
    final_equity: float = 0.0
    total_trades: int = 0


# ──────────────────────────────────────────────
# 백테스트 엔진
# ──────────────────────────────────────────────

class BacktestEngine:
    """
    이벤트 드리븐 백테스트 시뮬레이터.

    사용법:
        engine = BacktestEngine(strategy, initial_capital=10_000_000)
        result = engine.run(price_data)
        # price_data: {"MSFT": DataFrame(date, open, high, low, close, volume), ...}
    """

    def __init__(self, strategy: BaseStrategy,
                 initial_capital: float = 10_000_000,
                 commission_rate: float = 0.00015,
                 slippage_rate: float = 0.001):
        """
        Args:
            strategy: 실행할 전략 인스턴스
            initial_capital: 초기 자본금 (KRW)
            commission_rate: 편도 수수료율 (기본 0.015%)
            slippage_rate: 슬리피지율 (기본 0.1%)
        """
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate

        # 시뮬레이션 상태
        self.cash = initial_capital
        self.positions: dict[str, dict] = {}   # code → {quantity, entry_price, entry_date, ...}
        self.equity_history: list[dict] = []
        self.trades: list[Trade] = []

        # 리스크 매니저 (백테스트 모드: 킬스위치/MDD/일일손실 체크 비활성화)
        self.risk_manager = RiskManager(backtest_mode=True)
        self.risk_manager.state.total_equity = initial_capital
        self.risk_manager.state.cash = initial_capital
        self.risk_manager.state.peak_equity = initial_capital

        logger.info(f"💻 BacktestEngine 초기화: {strategy.name}, "
                    f"자본=₩{initial_capital:,.0f}, "
                    f"수수료={commission_rate*100:.3f}%, "
                    f"슬리피지={slippage_rate*100:.1f}%")

    def run(self, price_data: dict[str, pd.DataFrame],
            start_date: str | None = None,
            end_date: str | None = None) -> BacktestResult:
        """
        백테스트 실행.

        Args:
            price_data: {종목코드: DataFrame(date, close, ...)} 형태
            start_date: 시작일 (YYYY-MM-DD). None이면 데이터 시작일
            end_date: 종료일 (YYYY-MM-DD). None이면 데이터 종료일

        Returns:
            BacktestResult — 에퀴티 커브, 거래 기록, 성과 지표
        """
        # 날짜 인덱스 정렬 및 범위 계산
        all_dates = self._build_date_index(price_data, start_date, end_date)

        if len(all_dates) == 0:
            logger.warning("백테스트 실행할 날짜 범위가 없습니다.")
            return BacktestResult(
                strategy_name=self.strategy.name,
                start_date=start_date or "",
                end_date=end_date or "",
                initial_capital=self.initial_capital,
            )

        logger.info(f"📅 백테스트 기간: {all_dates[0]} ~ {all_dates[-1]} ({len(all_dates)}일)")

        # ── 가격 룩업 캐시 구축 (성능 최적화) ──
        # 매일 pd.to_datetime 변환을 반복하지 않도록, 한 번에 {code: {date_str: close}} 구축
        self._price_lookup = self._build_price_lookup(price_data)
        # {code: [(date_str, close), ...]} 정렬된 리스트 (look-ahead bias 방지용)
        self._price_series_cache = self._build_price_series_cache(price_data)
        # OHLC 전략용 날짜 캐시 (needs_ohlc=True인 전략만)
        if getattr(self.strategy, "needs_ohlc", False):
            self._ohlc_dates_cache = self._build_ohlc_dates_cache(price_data)

        # ── 일별 시뮬레이션 루프 ──
        for date in all_dates:
            day_prices = self._get_day_prices(price_data, date)
            if not day_prices:
                continue

            self._simulate_day(date, day_prices, price_data)

        # ── 백테스트 종료 시 미결 포지션 자동 청산 ──
        if self.positions and all_dates:
            last_date = all_dates[-1]
            last_prices = self._get_day_prices(price_data, last_date)
            remaining = list(self.positions.keys())
            logger.info(f"백테스트 종료 — 미결 포지션 {len(remaining)}건 자동 청산")
            for code in remaining:
                pos = self.positions[code]
                signal = TradeSignal(
                    strategy=pos["strategy"], code=code,
                    market=pos["market"], signal=Signal.CLOSE,
                    reason="백테스트 종료 자동 청산",
                )
                self._execute_sell(
                    last_date, signal,
                    last_prices.get(code, pos["current_price"]),
                )
            # 청산 후 최종 equity 재계산
            if self.equity_history:
                final_equity = self._calculate_equity(last_prices)
                self.equity_history[-1]["equity"] = final_equity

        # ── 결과 생성 ──
        result = self._build_result(all_dates)
        logger.info(f"✅ 백테스트 완료: {result.total_trades}건 거래, "
                    f"최종 자산={result.final_equity:,.0f}")

        return result

    # ──────────────────────────────────────
    # 핵심 시뮬레이션 로직
    # ──────────────────────────────────────

    def _simulate_day(self, date: str, day_prices: dict[str, float],
                      price_data: dict[str, pd.DataFrame]) -> None:
        """하루 시뮬레이션"""
        # 1. 보유 포지션 현재가 업데이트
        self._update_positions(day_prices)

        # 2. 손절 체크
        self._check_stop_losses(date, day_prices)

        # 3. 전략 신호 생성 (전략별 데이터 형식 맞춤)
        signals = self._generate_strategy_signals(date, price_data)

        # 4. 신호 실행 (리스크 검증 + 가상 체결)
        for signal in signals:
            self._execute_signal(date, signal, day_prices)

        # 5. 에퀴티 기록
        equity = self._calculate_equity(day_prices)
        self.equity_history.append({
            "date": date,
            "equity": equity,
            "cash": self.cash,
            "positions_value": equity - self.cash,
            "positions_count": len(self.positions),
        })

        # 리스크 매니저 상태 동기화
        self.risk_manager.state.total_equity = equity
        self.risk_manager.state.cash = self.cash
        if equity > self.risk_manager.state.peak_equity:
            self.risk_manager.state.peak_equity = equity

    def _generate_strategy_signals(self, date: str,
                                   price_data: dict[str, pd.DataFrame]) -> list[TradeSignal]:
        """
        제네릭 신호 생성 파이프라인.

        1. should_skip_date() → 날짜 스킵 여부 (리밸런싱 주기 등)
        2. _get_prices_until() → look-ahead bias 방지
        3. prepare_signal_kwargs() → 전략별 데이터 변환
        4. generate_signals() → 매매 신호 생성
        """
        # 1. 전략 스케줄링 체크
        if self.strategy.should_skip_date(date, self.equity_history):
            return []

        # 2. 현재 날짜까지의 데이터 (look-ahead bias 방지)
        truncated: dict = {}
        if getattr(self.strategy, "needs_ohlc", False):
            # OHLC 전략: 전체 DataFrame 전달
            for code, df in price_data.items():
                ohlc = self._get_ohlc_until(df, code, date)
                if len(ohlc) > 0:
                    truncated[code] = ohlc
        else:
            # 일반 전략: 종가 시리즈만 전달
            for code, df in price_data.items():
                prices = self._get_prices_until(df, date)
                if len(prices) > 0:
                    truncated[code] = prices

        if not truncated:
            return []

        # 3. 전략별 데이터 변환
        kwargs = self.strategy.prepare_signal_kwargs(truncated)
        if not kwargs:
            return []

        # 4. 신호 생성
        return self.strategy.generate_signals(**kwargs)

    def _execute_signal(self, date: str, signal: TradeSignal,
                        day_prices: dict[str, float]) -> None:
        """신호를 가상 체결"""
        # signal.price > 0이면 전략이 지정한 가격 우선 (예: 변동성 돌파 목표가)
        price = signal.price if signal.price > 0 else day_prices.get(signal.code, 0)
        if price <= 0:
            return

        if signal.signal == Signal.BUY:
            self._execute_buy(date, signal, price)
        elif signal.signal in (Signal.SELL, Signal.CLOSE):
            self._execute_sell(date, signal, price)

    def _execute_buy(self, date: str, signal: TradeSignal, price: float) -> None:
        """매수 가상 체결"""
        # 이미 보유 중이면 스킵 (중복 방지)
        if signal.code in self.positions:
            return

        # 슬리피지 반영 (매수 시 불리하게)
        exec_price = price * (1 + self.slippage_rate)

        # 포지션 사이즈 계산
        quantity = signal.quantity
        if quantity <= 0:
            quantity = self.risk_manager.calculate_position_size(exec_price, signal.market)
        if quantity <= 0:
            return

        # 총 비용
        gross_amount = exec_price * quantity
        commission = gross_amount * self.commission_rate
        net_amount = gross_amount + commission

        # 현금 체크
        if net_amount > self.cash:
            # 현금 내에서 가능한 수량으로 조정
            quantity = int(self.cash * 0.95 / (exec_price * (1 + self.commission_rate)))
            if quantity <= 0:
                return
            gross_amount = exec_price * quantity
            commission = gross_amount * self.commission_rate
            net_amount = gross_amount + commission

        # 리스크 검증
        can_trade, reason = self.risk_manager.can_open_position(signal.code, gross_amount)
        if not can_trade:
            logger.debug(f"[BT] 리스크 거부: {signal.code} — {reason}")
            return

        # 체결
        self.cash -= net_amount
        self.positions[signal.code] = {
            "quantity": quantity,
            "entry_price": exec_price,
            "entry_date": date,
            "market": signal.market,
            "strategy": signal.strategy,
            "current_price": exec_price,
        }

        # 리스크 매니저에 포지션 등록
        self.risk_manager.add_position(Position(
            code=signal.code, market=signal.market, side="LONG",
            quantity=quantity, entry_price=exec_price,
            current_price=exec_price, strategy=signal.strategy,
            entry_time=date,
        ))

        # 거래 기록
        self.trades.append(Trade(
            date=date, strategy=signal.strategy,
            code=signal.code, market=signal.market,
            side="BUY", quantity=quantity,
            price=exec_price, commission=commission,
            slippage=exec_price - price,
            net_amount=net_amount, reason=signal.reason,
        ))

        logger.debug(f"[BT] 매수: {signal.code} x{quantity} @ {exec_price:,.2f} "
                     f"(수수료={commission:,.0f})")

        # 전략 체결 콜백
        self.strategy.on_trade_executed(signal, success=True)

    def _execute_sell(self, date: str, signal: TradeSignal, price: float) -> None:
        """매도/청산 가상 체결"""
        pos = self.positions.get(signal.code)
        if pos is None:
            return

        quantity = pos["quantity"]
        entry_price = pos["entry_price"]
        entry_date = pos["entry_date"]

        # 슬리피지 반영 (매도 시 불리하게)
        exec_price = price * (1 - self.slippage_rate)

        gross_amount = exec_price * quantity
        commission = gross_amount * self.commission_rate
        net_amount = gross_amount - commission

        # 손익 계산
        cost_basis = entry_price * quantity
        pnl = net_amount - cost_basis - (cost_basis * self.commission_rate)
        pnl_pct = pnl / cost_basis * 100 if cost_basis > 0 else 0.0

        # 보유일수
        try:
            d1 = datetime.strptime(entry_date, "%Y-%m-%d")
            d2 = datetime.strptime(date, "%Y-%m-%d")
            holding_days = (d2 - d1).days
        except Exception:
            holding_days = 0

        # 체결
        self.cash += net_amount
        del self.positions[signal.code]

        # 리스크 매니저 포지션 제거
        self.risk_manager.remove_position(signal.code)

        # 거래 기록
        self.trades.append(Trade(
            date=date, strategy=signal.strategy,
            code=signal.code, market=signal.market,
            side="SELL", quantity=quantity,
            price=exec_price, commission=commission,
            slippage=price - exec_price,
            net_amount=net_amount, reason=signal.reason,
            pnl=pnl, pnl_pct=pnl_pct,
            holding_days=holding_days,
        ))

        logger.debug(f"[BT] 매도: {signal.code} x{quantity} @ {exec_price:,.2f} "
                     f"(PnL={pnl:+,.0f}, {pnl_pct:+.2f}%)")

        # 전략 체결 콜백
        self.strategy.on_trade_executed(signal, success=True)

    # ──────────────────────────────────────
    # 유틸리티 메서드
    # ──────────────────────────────────────

    def _update_positions(self, day_prices: dict[str, float]) -> None:
        """보유 포지션 현재가 업데이트"""
        price_updates = {}
        for code, pos in self.positions.items():
            if code in day_prices:
                pos["current_price"] = day_prices[code]
                price_updates[code] = day_prices[code]

        if price_updates:
            self.risk_manager.update_prices(price_updates)

    def _check_stop_losses(self, date: str, day_prices: dict[str, float]) -> None:
        """손절 체크 — 손절 조건 충족 시 자동 청산"""
        codes_to_close = []
        for code, pos in self.positions.items():
            if code not in day_prices:
                continue
            current_price = day_prices[code]
            entry_price = pos["entry_price"]
            pnl_pct = (current_price - entry_price) / entry_price * 100

            if pnl_pct <= self.risk_manager.stop_loss_pct:
                codes_to_close.append((code, pos))

        for code, pos in codes_to_close:
            signal = TradeSignal(
                strategy=pos["strategy"], code=code,
                market=pos["market"], signal=Signal.CLOSE,
                reason=f"손절 ({pos['current_price']:,.2f}, "
                       f"진입={pos['entry_price']:,.2f})",
            )
            self._execute_sell(date, signal, day_prices[code])

    def _calculate_equity(self, day_prices: dict[str, float]) -> float:
        """현재 총 자산 계산 (현금 + 포지션 평가)"""
        positions_value = sum(
            pos["quantity"] * day_prices.get(code, pos["current_price"])
            for code, pos in self.positions.items()
        )
        return self.cash + positions_value

    def _build_date_index(self, price_data: dict[str, pd.DataFrame],
                          start_date: str | None,
                          end_date: str | None) -> list[str]:
        """모든 종목의 날짜를 합쳐 공통 날짜 인덱스 생성"""
        all_dates = set()
        for code, df in price_data.items():
            if "date" in df.columns:
                dates = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d").tolist()
            elif isinstance(df.index, pd.DatetimeIndex):
                dates = df.index.strftime("%Y-%m-%d").tolist()
            else:
                continue
            all_dates.update(dates)

        all_dates = sorted(all_dates)

        # 범위 필터
        if start_date:
            all_dates = [d for d in all_dates if d >= start_date]
        if end_date:
            all_dates = [d for d in all_dates if d <= end_date]

        return all_dates

    def _build_price_lookup(self, price_data: dict[str, pd.DataFrame]) -> dict[str, dict[str, float]]:
        """가격 룩업 테이블 구축: {code: {date_str: close_price}}

        run() 시작 시 1회 구축하여, 매일 반복되는 날짜 변환을 제거합니다.
        """
        lookup: dict[str, dict[str, float]] = {}
        for code, df in price_data.items():
            code_prices: dict[str, float] = {}
            if "date" in df.columns:
                dates = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
                for d, c in zip(dates, df["close"]):
                    code_prices[d] = float(c)
            elif isinstance(df.index, pd.DatetimeIndex):
                dates = df.index.strftime("%Y-%m-%d")
                for d, c in zip(dates, df["close"]):
                    code_prices[d] = float(c)
            lookup[code] = code_prices
        return lookup

    def _build_price_series_cache(self, price_data: dict[str, pd.DataFrame]) -> dict[str, list[tuple[str, float]]]:
        """종가 시리즈 캐시 구축: {code: [(date_str, close), ...]} 날짜 오름차순 정렬

        _get_prices_until()에서 bisect로 O(log n) 슬라이싱에 사용합니다.
        """
        cache: dict[str, list[tuple[str, float]]] = {}
        for code, df in price_data.items():
            pairs: list[tuple[str, float]] = []
            if "date" in df.columns:
                dates = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
                for d, c in zip(dates, df["close"]):
                    pairs.append((d, float(c)))
            elif isinstance(df.index, pd.DatetimeIndex):
                dates = df.index.strftime("%Y-%m-%d")
                for d, c in zip(dates, df["close"]):
                    pairs.append((d, float(c)))
            pairs.sort(key=lambda x: x[0])
            cache[code] = pairs
        return cache

    def _get_day_prices(self, price_data: dict[str, pd.DataFrame],
                        date: str) -> dict[str, float]:
        """특정 날짜의 종목별 종가를 반환 (캐시 룩업 O(1))"""
        prices = {}
        for code, date_map in self._price_lookup.items():
            price = date_map.get(date)
            if price is not None:
                prices[code] = price
        return prices

    def _get_prices_until(self, df: pd.DataFrame, date: str) -> pd.Series:
        """특정 날짜까지의 종가 시리즈 반환 (look-ahead bias 방지, bisect O(log n))"""
        from bisect import bisect_right

        # df에서 code를 추출하여 캐시 참조
        code = None
        if "code" in df.columns and not df.empty:
            code = df["code"].iloc[0]

        if code and hasattr(self, "_price_series_cache") and code in self._price_series_cache:
            pairs = self._price_series_cache[code]
            # bisect_right: date 이하의 모든 항목을 슬라이싱
            idx = bisect_right(pairs, (date, float("inf")))
            if idx == 0:
                return pd.Series(dtype=float)
            values = [c for _, c in pairs[:idx]]
            return pd.Series(values, dtype=float)

        # 캐시 미스 시 기존 로직 폴백
        if "date" in df.columns:
            mask = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d") <= date
            return df.loc[mask, "close"].reset_index(drop=True)
        elif isinstance(df.index, pd.DatetimeIndex):
            mask = df.index.strftime("%Y-%m-%d") <= date
            return df.loc[mask, "close"]
        return pd.Series(dtype=float)

    def _build_ohlc_dates_cache(
        self, price_data: dict[str, pd.DataFrame],
    ) -> dict[str, list[str]]:
        """OHLC 날짜 캐시: {code: [sorted_date_strings]}

        _get_ohlc_until()에서 bisect로 O(log n) 슬라이싱에 사용합니다.
        """
        cache: dict[str, list[str]] = {}
        for code, df in price_data.items():
            if "date" in df.columns:
                dates = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d").tolist()
            elif isinstance(df.index, pd.DatetimeIndex):
                dates = df.index.strftime("%Y-%m-%d").tolist()
            else:
                continue
            cache[code] = sorted(dates)
        return cache

    def _get_ohlc_until(self, df: pd.DataFrame, code: str,
                        date: str) -> pd.DataFrame:
        """특정 날짜까지의 OHLC DataFrame 반환 (look-ahead bias 방지, bisect O(log n))"""
        from bisect import bisect_right

        if hasattr(self, "_ohlc_dates_cache") and code in self._ohlc_dates_cache:
            dates = self._ohlc_dates_cache[code]
            idx = bisect_right(dates, date)
            if idx == 0:
                return pd.DataFrame()
            return df.iloc[:idx]

        # 캐시 미스 시 폴백
        if "date" in df.columns:
            mask = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d") <= date
            return df.loc[mask].reset_index(drop=True)
        elif isinstance(df.index, pd.DatetimeIndex):
            mask = df.index.strftime("%Y-%m-%d") <= date
            return df.loc[mask]
        return pd.DataFrame()

    def _build_result(self, all_dates: list[str]) -> BacktestResult:
        """시뮬레이션 결과를 BacktestResult로 변환"""
        eq_df = pd.DataFrame(self.equity_history)

        if eq_df.empty:
            return BacktestResult(
                strategy_name=self.strategy.name,
                start_date=all_dates[0] if all_dates else "",
                end_date=all_dates[-1] if all_dates else "",
                initial_capital=self.initial_capital,
            )

        equity_curve = pd.Series(
            eq_df["equity"].values,
            index=pd.to_datetime(eq_df["date"]),
            name="equity",
        )
        daily_returns = equity_curve.pct_change().dropna()

        return BacktestResult(
            strategy_name=self.strategy.name,
            start_date=all_dates[0],
            end_date=all_dates[-1],
            initial_capital=self.initial_capital,
            equity_curve=equity_curve,
            daily_returns=daily_returns,
            trades=self.trades,
            final_equity=equity_curve.iloc[-1] if len(equity_curve) > 0 else self.initial_capital,
            total_trades=len(self.trades),
        )
