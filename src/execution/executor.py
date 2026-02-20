"""
AlgoTrader KR — 주문 실행 엔진

전략에서 생성된 TradeSignal을 리스크 검증 후 실제 주문으로 실행합니다.

Depends on:
    - src.core.broker (주문 실행)
    - src.core.risk_manager (위험 검증 + 포지션 관리)
    - src.core.data_manager (거래 기록 저장)
    - src.utils.notifier (매매 알림)

Used by:
    - main.py (AlgoTrader.run_once)

Modification Guide:
    - 주문 실행 로직을 변경하려면 _execute_buy()/_execute_sell()을 수정하세요.
    - 새로운 Signal 타입을 처리하려면 execute_signals()의 분기를 추가하세요.
    - 현재가 조회의 거래소 매핑은 src.core.exchange 유틸리티를 참조하세요.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from loguru import logger

from src.core.broker import KISBroker
from src.core.config import get_config
from src.core.data_manager import DataManager
from src.core.exchange import get_us_exchange
from src.core.fx import get_fx_rate
from src.core.portfolio_tracker import PortfolioTracker
from src.core.risk_manager import RiskManager, Position
from src.strategies.base import BaseStrategy, TradeSignal, Signal
from src.utils.notifier import TelegramNotifier


class OrderExecutor:
    """
    매매 신호를 실제 주문으로 변환하는 실행 엔진.

    실행 흐름:
        1. TradeSignal 수신
        2. 현재가 조회 (price == 0인 경우)
        3. RiskManager로 포지션 오픈 가능 여부 검증
        4. KISBroker로 주문 전송
        5. 포지션/거래 기록 업데이트
        6. 텔레그램 알림 전송
    """

    def __init__(self, broker: KISBroker, risk_manager: RiskManager,
                 data_manager: DataManager, notifier: TelegramNotifier,
                 strategies: list[BaseStrategy] | None = None,
                 portfolio_tracker: PortfolioTracker | None = None,
                 simulation_mode: bool = False):
        self.broker = broker
        self.risk_manager = risk_manager
        self.data_manager = data_manager
        self.notifier = notifier
        self.portfolio_tracker = portfolio_tracker
        self.simulation_mode = simulation_mode

        # 전략 이름 → 인스턴스 매핑 (체결 콜백용)
        self._strategies_by_name: dict[str, BaseStrategy] = {}
        if strategies:
            for s in strategies:
                self._strategies_by_name[s.name] = s

        mode_label = "시뮬레이션" if simulation_mode else "실거래"
        logger.info(f"OrderExecutor 초기화 완료 (모드: {mode_label})")

    def _update_sim_prices(self) -> None:
        """시뮬레이션 포지션의 현재가를 갱신합니다."""
        if not (self.simulation_mode and self.portfolio_tracker):
            return
        positions = self.portfolio_tracker.get_all_positions()
        if not positions:
            return
        for pos in positions:
            try:
                price = self.get_current_price(pos["code"], pos["market"])
                if price > 0:
                    self.portfolio_tracker.update_position_price(pos["code"], price)
            except Exception as e:
                logger.warning(f"시뮬레이션 가격 갱신 실패: {pos['code']} — {e}")

    def scan_stop_losses(self) -> list[TradeSignal]:
        """보유 포지션 중 손절 조건에 해당하는 종목의 SELL 시그널을 생성합니다."""
        sell_signals: list[TradeSignal] = []
        for pos in self.risk_manager.state.positions:
            if self.risk_manager.check_stop_loss(pos):
                sell_signals.append(TradeSignal(
                    code=pos.code,
                    market=pos.market,
                    signal=Signal.SELL,
                    strategy=pos.strategy,
                    reason=(f"손절: {pos.pnl_pct:.1f}% <= "
                            f"{self.risk_manager.stop_loss_pct}%"),
                ))
        return sell_signals

    def execute_signals(self, signals: list[TradeSignal]) -> None:
        """
        매매 신호 리스트를 순차적으로 실행합니다.

        Args:
            signals: Strategy에서 생성한 TradeSignal 리스트
        """
        # 1. 시뮬레이션 모드: 기존 포지션 현재가 갱신
        self._update_sim_prices()

        # 2. 포트폴리오 리스크 체크 (MDD/일일손실 초과 시 킬스위치 자동 발동)
        safe, reason = self.risk_manager.check_portfolio_risk()
        if not safe:
            logger.critical(f"포트폴리오 리스크 위반 — 전체 실행 중단: {reason}")
            self.notifier.notify_risk(f"🚨 KILL SWITCH AUTO: {reason}")
            return

        # 3. 손절 스캔 — 전략 시그널보다 우선 실행
        stop_signals = self.scan_stop_losses()
        if stop_signals:
            logger.warning(f"손절 시그널 {len(stop_signals)}건 — 우선 실행")
            for sig in stop_signals:
                try:
                    self._execute_sell(sig)
                except Exception as e:
                    logger.error(f"손절 실행 실패: {sig.code} — {e}")

        # 4. 전략 시그널 실행
        if not signals:
            return

        for signal in signals:
            logger.info(f"신호 처리: {signal}")

            try:
                if signal.signal == Signal.BUY:
                    self._execute_buy(signal)
                elif signal.signal in (Signal.CLOSE, Signal.SELL):
                    self._execute_sell(signal)
                elif signal.signal == Signal.HOLD:
                    pass  # 명시적 무시
            except Exception as e:
                logger.error(f"신호 실행 실패: {signal.code} — {e}")
                self.notifier.notify_error(f"주문 실패: {signal.code} — {e}")
                strategy = self._strategies_by_name.get(signal.strategy)
                if strategy:
                    strategy.on_trade_executed(signal, success=False)

    def _execute_buy(self, signal: TradeSignal) -> None:
        """매수 신호 실행"""
        # 1. 가격 결정
        price = signal.price or self.get_current_price(signal.code, signal.market)
        if price <= 0:
            logger.warning(f"가격 조회 실패, 매수 스킵: {signal.code}")
            return

        # 2. 수량 결정
        quantity = signal.quantity or self.risk_manager.calculate_position_size(
            price, signal.market, signal.strategy
        )
        if quantity <= 0:
            logger.warning(f"포지션 사이즈 0, 매수 스킵: {signal.code}")
            return

        market_value_krw = price * quantity * get_fx_rate(signal.market)

        # 3. 리스크 검증 (KRW 기준)
        can_trade, reason = self.risk_manager.can_open_position(
            signal.code, market_value_krw, signal.strategy
        )
        if not can_trade:
            logger.warning(f"리스크 거부: {reason}")
            self.notifier.notify_risk(f"{signal.code}: {reason}")
            return

        # 4. 주문 실행
        if self.simulation_mode and self.portfolio_tracker:
            success = self.portfolio_tracker.execute_buy(
                signal.code, signal.market, quantity, price, signal.strategy,
            )
            if not success:
                logger.warning(f"시뮬레이션 매수 실패 (현금 부족): {signal.code}")
                return
        else:
            # 안전장치: simulation.enabled=true인데 실주문 경로 진입 시 차단
            config = get_config()
            if config.get("simulation", {}).get("enabled", False):
                logger.critical(
                    f"실주문 차단: simulation.enabled=true인데 simulation_mode=False로 "
                    f"OrderExecutor 생성됨. {signal.code} 매수 스킵"
                )
                return
            if signal.market == "KR":
                result = self.broker.order_kr_buy(signal.code, quantity)
            else:
                exchange = get_us_exchange(signal.code, purpose="order")
                result = self.broker.order_us_buy(signal.code, quantity, exchange=exchange)
            # 주문 결과 저장
            order_no = result.get("output", {}).get("ODNO", "")
            self.data_manager.save_order(
                order_no=order_no, strategy=signal.strategy,
                code=signal.code, market=signal.market, side="BUY",
                quantity=quantity, price=price,
                response_json=json.dumps(result, ensure_ascii=False),
            )

        # 5. 포지션 등록
        self.risk_manager.add_position(Position(
            code=signal.code,
            market=signal.market,
            side="LONG",
            quantity=quantity,
            entry_price=price,
            current_price=price,
            strategy=signal.strategy,
            entry_time=datetime.now().isoformat(),
        ))

        # 6. 거래 기록 + 알림
        self.data_manager.save_trade(
            signal.strategy, signal.code, signal.market,
            "BUY", quantity, price, signal.reason,
        )
        self.notifier.notify_trade(
            signal.strategy, signal.code, "BUY",
            quantity, price, signal.reason,
        )

        # 7. 전략 체결 콜백
        strategy = self._strategies_by_name.get(signal.strategy)
        if strategy:
            strategy.on_trade_executed(signal, success=True)

    def _execute_sell(self, signal: TradeSignal) -> None:
        """매도/청산 신호 실행"""
        price = self.get_current_price(signal.code, signal.market)

        # 보유 포지션 조회
        pos = next(
            (p for p in self.risk_manager.state.positions if p.code == signal.code),
            None,
        )
        quantity = pos.quantity if pos else 0

        if quantity <= 0:
            logger.warning(f"보유 수량 없음, 매도 스킵: {signal.code}")
            return

        # 주문 실행
        if self.simulation_mode and self.portfolio_tracker:
            proceeds = self.portfolio_tracker.execute_sell(signal.code, price)
            if proceeds == 0:
                logger.warning(f"시뮬레이션 매도 실패 (포지션 없음): {signal.code}")
                return
        else:
            # 안전장치: simulation.enabled=true인데 실주문 경로 진입 시 차단
            config = get_config()
            if config.get("simulation", {}).get("enabled", False):
                logger.critical(
                    f"실주문 차단: simulation.enabled=true인데 simulation_mode=False로 "
                    f"OrderExecutor 생성됨. {signal.code} 매도 스킵"
                )
                return
            if signal.market == "KR":
                result = self.broker.order_kr_sell(signal.code, quantity)
            else:
                exchange = get_us_exchange(signal.code, purpose="order")
                result = self.broker.order_us_sell(signal.code, quantity, exchange=exchange)
            # 주문 결과 저장
            order_no = result.get("output", {}).get("ODNO", "")
            self.data_manager.save_order(
                order_no=order_no, strategy=signal.strategy,
                code=signal.code, market=signal.market, side="SELL",
                quantity=quantity, price=price,
                response_json=json.dumps(result, ensure_ascii=False),
            )

        # 포지션 제거 + 기록 + 알림
        self.risk_manager.remove_position(signal.code)
        self.data_manager.save_trade(
            signal.strategy, signal.code, signal.market,
            "SELL", quantity, price, signal.reason,
        )
        self.notifier.notify_trade(
            signal.strategy, signal.code, "SELL",
            quantity, price, signal.reason,
        )

        # 전략 체결 콜백
        strategy = self._strategies_by_name.get(signal.strategy)
        if strategy:
            strategy.on_trade_executed(signal, success=True)

    def get_current_price(self, code: str, market: str) -> float:
        """
        현재가를 조회합니다 (KIS API → yfinance 폴백).

        Args:
            code: 종목코드/티커
            market: "KR" 또는 "US"

        Returns:
            현재가 (float). 실패 시 0.0.
        """
        try:
            if market == "KR":
                data = self.broker.get_kr_price(code)
                return float(data["price"])
            else:
                exchange = get_us_exchange(code)
                data = self.broker.get_us_price(code, exchange=exchange)
                return float(data["price"])
        except Exception as e:
            logger.warning(f"KIS 가격 조회 실패: {code} — {e}, yfinance 폴백 시도")
            return self._get_price_yfinance(code, market)

    @staticmethod
    def _get_price_yfinance(code: str, market: str) -> float:
        """yfinance를 이용한 현재가 폴백"""
        try:
            from src.core.data_feed import DataFeed
            import yfinance as yf

            symbol = DataFeed._to_yf_symbol(code, market)
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d")
            if not hist.empty:
                price = float(hist["Close"].iloc[-1])
                logger.info(f"yfinance 가격 조회 성공: {code} = {price}")
                return price
        except Exception as e:
            logger.error(f"yfinance 가격 조회 실패: {code} — {e}")
        return 0.0
