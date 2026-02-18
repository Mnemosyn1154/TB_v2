"""
AlgoTrader KR — Strategies 패키지

매매 전략 모듈. 모든 전략은 BaseStrategy를 상속합니다.

공개 API:
    - BaseStrategy: 전략 추상 클래스
    - TradeSignal: 매매 신호 데이터 클래스
    - Signal: 매매 방향 Enum (BUY/SELL/HOLD/CLOSE)
    - StatArbStrategy: 통계적 차익거래 (공적분 기반)
    - DualMomentumStrategy: 듀얼 모멘텀 (상대+절대)
    - QuantFactorStrategy: 퀀트 팩터 (멀티팩터 스코어링)
"""
from src.strategies.base import BaseStrategy, TradeSignal, Signal
from src.strategies.stat_arb import StatArbStrategy
from src.strategies.dual_momentum import DualMomentumStrategy
from src.strategies.quant_factor import QuantFactorStrategy

STRATEGY_REGISTRY: dict[str, type[BaseStrategy]] = {
    "stat_arb": StatArbStrategy,
    "dual_momentum": DualMomentumStrategy,
    "quant_factor": QuantFactorStrategy,
}

__all__ = [
    "BaseStrategy",
    "TradeSignal",
    "Signal",
    "StatArbStrategy",
    "DualMomentumStrategy",
    "QuantFactorStrategy",
    "STRATEGY_REGISTRY",
]
