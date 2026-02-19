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
    - SectorRotationStrategy: 섹터 로테이션 (모멘텀 기반 섹터 ETF 순환)
    - VolatilityBreakoutStrategy: 변동성 돌파 (래리 윌리엄스)
    - BollingerBandStrategy: 볼린저 밴드 (평균 회귀)
"""
from src.strategies.base import BaseStrategy, TradeSignal, Signal
from src.strategies.stat_arb import StatArbStrategy
from src.strategies.dual_momentum import DualMomentumStrategy
from src.strategies.quant_factor import QuantFactorStrategy
from src.strategies.sector_rotation import SectorRotationStrategy
from src.strategies.volatility_breakout import VolatilityBreakoutStrategy
from src.strategies.bollinger_band import BollingerBandStrategy

STRATEGY_REGISTRY: dict[str, type[BaseStrategy]] = {
    "stat_arb": StatArbStrategy,
    "dual_momentum": DualMomentumStrategy,
    "quant_factor": QuantFactorStrategy,
    "sector_rotation": SectorRotationStrategy,
    "volatility_breakout": VolatilityBreakoutStrategy,
    "bollinger_band": BollingerBandStrategy,
}


def resolve_strategy(config_key: str, strat_config: dict) -> BaseStrategy:
    """config_key와 설정으로부터 전략 인스턴스 생성.

    strat_config에 'type' 필드가 있으면 해당 타입의 클래스를 사용하고,
    없으면 config_key 자체를 타입으로 사용 (하위 호환).
    """
    type_name = strat_config.get("type", config_key)
    cls = STRATEGY_REGISTRY.get(type_name)
    if not cls:
        raise ValueError(f"Unknown strategy type: {type_name}")
    return cls(config_key=config_key)


__all__ = [
    "BaseStrategy",
    "TradeSignal",
    "Signal",
    "StatArbStrategy",
    "DualMomentumStrategy",
    "QuantFactorStrategy",
    "SectorRotationStrategy",
    "VolatilityBreakoutStrategy",
    "BollingerBandStrategy",
    "STRATEGY_REGISTRY",
    "resolve_strategy",
]
