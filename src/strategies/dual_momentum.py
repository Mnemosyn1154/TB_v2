from __future__ import annotations

"""
AlgoTrader KR — 듀얼 모멘텀 전략 (Dual Momentum)

한국 vs 미국 시장 수익률 비교(상대 모멘텀) + 절대 모멘텀 필터.

알고리즘 흐름:
    1. KR ETF vs US ETF 12개월 수익률 계산
    2. 승자 선택 (상대 모멘텀)
    3. 승자 수익률 > 무위험수익률? (절대 모멘텀)
       - YES → 승자 ETF 매수
       - NO → 안전자산(채권 ETF) 매수
    4. 매월 리밸런싱

배분 결과: "KR" / "US" / "SAFE"

Depends on:
    - src.strategies.base (BaseStrategy, TradeSignal)
    - src.core.config (전략 파라미터)

Used by:
    - main.py (AlgoTrader._run_dual_momentum)

Modification Guide:
    - ETF 변경: settings.yaml의 dual_momentum 섹션 수정
    - 룩백 기간: lookback_months 조정 (거래일수 추정: months × 21)
    - 리밸런싱 기준 추가: rebalance_day 이외 조건은 main.py에서 스케줄링 로직으로 제어
"""
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger

from src.strategies.base import BaseStrategy, TradeSignal, Signal
from src.core.config import get_config


class DualMomentumStrategy(BaseStrategy):
    """
    듀얼 모멘텀 전략

    1. 상대 모멘텀: 한국 vs 미국 수익률 비교 → 강한 시장 선택
    2. 절대 모멘텀: 선택된 시장 > 무위험수익률? → YES: 투자, NO: 안전자산
    """

    def __init__(self, config_key: str | None = None):
        super().__init__("DualMomentum", config_key=config_key)
        config = get_config()
        dm_config = config["strategies"][self.config_key]

        self.lookback_months = dm_config["lookback_months"]
        self.rebalance_day = dm_config["rebalance_day"]
        self.kr_etf = dm_config["kr_etf"]           # KODEX 200
        self.us_etf = dm_config["us_etf"]            # SPY
        self.safe_kr_etf = dm_config["safe_kr_etf"]  # KOSEF 국고채
        self.safe_us_etf = dm_config["safe_us_etf"]  # SHY
        self.us_etf_exchange = dm_config.get("us_etf_exchange", "")
        self.safe_us_etf_exchange = dm_config.get("safe_us_etf_exchange", "")
        self.risk_free_rate = dm_config["risk_free_rate"]

        # 현재 상태
        self.current_allocation: str = "NONE"  # "KR", "US", "SAFE", "NONE"
        self.kr_return: float = 0.0
        self.us_return: float = 0.0

        logger.info(f"듀얼 모멘텀 전략: 룩백={self.lookback_months}개월, "
                    f"무위험수익률={self.risk_free_rate*100}%")

    # ──────────────────────────────────────────────
    # 플러그인 인터페이스
    # ──────────────────────────────────────────────

    def get_config_key(self) -> str:
        return getattr(self, "config_key", "dual_momentum")

    def required_codes(self) -> list[dict[str, str]]:
        """필요 종목 코드 목록 (exchange 포함)"""
        us_entry = {"code": self.us_etf, "market": "US"}
        if self.us_etf_exchange:
            us_entry["exchange"] = self.us_etf_exchange

        safe_us_entry = {"code": self.safe_us_etf, "market": "US"}
        if self.safe_us_etf_exchange:
            safe_us_entry["exchange"] = self.safe_us_etf_exchange

        return [
            {"code": self.kr_etf, "market": "KR"},
            us_entry,
            {"code": self.safe_kr_etf, "market": "KR"},
            safe_us_entry,
        ]

    def prepare_signal_kwargs(self, price_data: dict[str, pd.Series]) -> dict:
        kr_prices = price_data.get(self.kr_etf)
        us_prices = price_data.get(self.us_etf)

        if kr_prices is None or us_prices is None:
            return {}

        # 최소 60일 이상이면 진행 (가용 데이터로 수익률 계산)
        min_required = 60
        if len(kr_prices) < min_required or len(us_prices) < min_required:
            return {}

        return {"kr_prices": kr_prices, "us_prices": us_prices}

    def should_skip_date(self, date: str, equity_history: list[dict]) -> bool:
        """월별 리밸런싱: rebalance_day 기준으로 매월 1회만 실행"""
        if not equity_history:
            return False

        last_date = equity_history[-1]["date"]
        try:
            from datetime import datetime
            current = datetime.strptime(date, "%Y-%m-%d")
            previous = datetime.strptime(last_date, "%Y-%m-%d")
            # 같은 월이면 스킵
            if current.year == previous.year and current.month == previous.month:
                return True
            return False
        except Exception:
            return False

    # ──────────────────────────────────────────────
    # 수익률 계산
    # ──────────────────────────────────────────────

    def calculate_return(self, prices: pd.Series, months: int = 12) -> float:
        """N개월 수익률 계산"""
        if prices.empty or len(prices) < 20:
            return 0.0

        trading_days = months * 21  # 대략적인 거래일 수
        if len(prices) < trading_days:
            trading_days = len(prices) - 1

        if trading_days <= 0:
            return 0.0

        current = prices.iloc[-1]
        past = prices.iloc[-trading_days]

        if past == 0:
            return 0.0

        return (current - past) / past

    def generate_signals(self, kr_prices: pd.Series | None = None,
                         us_prices: pd.Series | None = None,
                         **kwargs) -> list[TradeSignal]:
        """
        듀얼 모멘텀 신호 생성

        Args:
            kr_prices: KODEX 200 종가 시리즈
            us_prices: SPY 종가 시리즈
        """
        if not self.enabled:
            return []

        if kr_prices is None or us_prices is None:
            kr_prices = kwargs.get("kr_prices")
            us_prices = kwargs.get("us_prices")

        if kr_prices is None or us_prices is None:
            logger.warning("듀얼 모멘텀: 가격 데이터 없음")
            return []

        # 수익률 계산
        self.kr_return = self.calculate_return(kr_prices, self.lookback_months)
        self.us_return = self.calculate_return(us_prices, self.lookback_months)

        logger.info(f"📊 듀얼 모멘텀: KR 수익률={self.kr_return*100:.1f}%, "
                    f"US 수익률={self.us_return*100:.1f}%, "
                    f"무위험={self.risk_free_rate*100:.1f}%")

        # 듀얼 모멘텀 판단
        new_allocation = self._determine_allocation()
        signals: list[TradeSignal] = []

        if new_allocation == self.current_allocation:
            logger.info(f"듀얼 모멘텀: 변동 없음 — 유지 ({self.current_allocation})")
            return []

        # 기존 포지션 청산
        if self.current_allocation != "NONE":
            close_code = self._get_etf_code(self.current_allocation)
            close_market = "KR" if self.current_allocation in ("KR", "SAFE_KR") else "US"
            signals.append(TradeSignal(
                strategy=self.name,
                code=close_code,
                market=close_market,
                signal=Signal.CLOSE,
                reason=f"리밸런싱: {self.current_allocation} → {new_allocation}",
            ))

        # 새 포지션 오픈
        new_code = self._get_etf_code(new_allocation)
        new_market = "KR" if new_allocation in ("KR", "SAFE") else "US"
        signals.append(TradeSignal(
            strategy=self.name,
            code=new_code,
            market=new_market,
            signal=Signal.BUY,
            reason=(
                f"듀얼 모멘텀: {new_allocation} 선택 "
                f"(KR={self.kr_return*100:.1f}%, US={self.us_return*100:.1f}%)"
            ),
            metadata={
                "kr_return": self.kr_return,
                "us_return": self.us_return,
                "allocation": new_allocation,
                "target_allocation": new_allocation,
            },
        ))

        # 주의: current_allocation은 on_trade_executed()에서 체결 성공 시 업데이트
        logger.info(f"🔄 듀얼 모멘텀 리밸런싱 신호: {self.current_allocation} → {new_allocation}")

        return signals

    def on_trade_executed(self, signal: TradeSignal, success: bool) -> None:
        """체결 콜백 — 실제 체결 성공 시에만 배분 상태 업데이트"""
        if not success:
            return

        target = signal.metadata.get("target_allocation") if signal.metadata else None

        if signal.signal == Signal.BUY and target:
            self.current_allocation = target
            logger.info(f"[DualMomentum] 배분 확정: {target}")
        elif signal.signal == Signal.CLOSE:
            # 청산 후 BUY가 이어지므로, 청산 단독 시에만 NONE으로
            # (BUY 신호의 target_allocation이 최종 상태를 결정)
            pass

    def _determine_allocation(self) -> str:
        """듀얼 모멘텀 판단 로직"""
        if self.kr_return > self.us_return:
            # 한국이 상대적으로 강함
            if self.kr_return > self.risk_free_rate:
                return "KR"
            else:
                return "SAFE"
        else:
            # 미국이 상대적으로 강함
            if self.us_return > self.risk_free_rate:
                return "US"
            else:
                return "SAFE"

    def _get_etf_code(self, allocation: str) -> str:
        """배분에 해당하는 ETF 코드 반환"""
        mapping = {
            "KR": self.kr_etf,
            "US": self.us_etf,
            "SAFE": self.safe_kr_etf,  # 안전자산은 한국 채권 ETF 기본
        }
        return mapping.get(allocation, self.safe_kr_etf)

    def get_status(self) -> dict[str, Any]:
        """현재 전략 상태"""
        return {
            "strategy": self.name,
            "enabled": self.enabled,
            "current_allocation": self.current_allocation,
            "kr_return_12m": f"{self.kr_return*100:.1f}%",
            "us_return_12m": f"{self.us_return*100:.1f}%",
            "risk_free_rate": f"{self.risk_free_rate*100:.1f}%",
            "etfs": {
                "kr": self.kr_etf,
                "us": self.us_etf,
                "safe_kr": self.safe_kr_etf,
                "safe_us": self.safe_us_etf,
            },
        }
