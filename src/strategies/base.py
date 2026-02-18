"""
AlgoTrader KR — 전략 베이스 클래스
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any

import pandas as pd
from loguru import logger


class Signal(Enum):
    """매매 신호"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    CLOSE = "CLOSE"     # 포지션 청산


@dataclass
class TradeSignal:
    """전략에서 생성하는 매매 신호"""
    strategy: str
    code: str
    market: str          # "KR" or "US"
    signal: Signal
    quantity: int = 0
    price: float = 0.0
    reason: str = ""
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def __str__(self) -> str:
        emoji = {"BUY": "📈", "SELL": "📉", "HOLD": "⏸️", "CLOSE": "🔒"}.get(self.signal.value, "")
        return f"{emoji} [{self.strategy}] {self.signal.value} {self.code} ({self.market}) — {self.reason}"


class BaseStrategy(ABC):
    """
    전략 베이스 클래스 — 모든 전략은 이 클래스를 상속.

    플러그인 인터페이스:
        필수 (5개 abstract):
        - get_config_key(): settings.yaml의 키 이름
        - required_codes(): 수집/로드할 종목 목록
        - prepare_signal_kwargs(): 원시 데이터 → generate_signals() kwargs 변환
        - generate_signals(): 매매 신호 생성 (핵심 로직)
        - get_status(): 현재 상태 반환

        선택적 오버라이드 (4개):
        - should_skip_date(): 백테스트 날짜 스킵 여부
        - get_pair_names(): 페어 기반 전략의 페어 이름 목록
        - filter_pairs(): 특정 페어만 사용하도록 필터링
        - on_trade_executed(): 체결 콜백 — 내부 상태 동기화
    """

    def __init__(self, name: str):
        self.name = name
        self.enabled = True
        logger.info(f"전략 초기화: {name}")

    # ── 플러그인 인터페이스 ──

    @abstractmethod
    def get_config_key(self) -> str:
        """settings.yaml의 strategies: 하위 키 이름 (예: 'stat_arb')"""
        pass

    @abstractmethod
    def required_codes(self) -> list[dict[str, str]]:
        """
        수집/로드할 종목 목록 반환.

        Returns:
            [{"code": "005930", "market": "KR"}, {"code": "MSFT", "market": "US"}, ...]
        """
        pass

    @abstractmethod
    def prepare_signal_kwargs(self, price_data: dict[str, pd.Series]) -> dict:
        """
        원시 가격 데이터를 generate_signals()에 전달할 kwargs로 변환.

        Args:
            price_data: {종목코드: 종가 시리즈} — 백테스트 시 look-ahead bias가
                        제거된 상태로 전달됨

        Returns:
            generate_signals()에 전달할 kwargs dict.
            빈 dict 반환 시 해당 기간 신호 생성을 스킵.
        """
        pass

    @abstractmethod
    def generate_signals(self, **kwargs) -> list[TradeSignal]:
        """
        시장 데이터를 분석하여 매매 신호를 생성합니다.
        Returns: list of TradeSignal
        """
        pass

    @abstractmethod
    def get_status(self) -> dict[str, Any]:
        """전략 현재 상태 반환"""
        pass

    def should_skip_date(self, date: str, equity_history: list[dict]) -> bool:
        """
        백테스트에서 특정 날짜를 스킵할지 결정 (선택적 오버라이드).

        월별 리밸런싱 등 전략별 스케줄링 로직에 사용.
        기본값: 모든 날짜에서 실행 (스킵 없음).
        """
        return False

    def get_pair_names(self) -> list[str]:
        """
        페어 기반 전략에서 사용 가능한 페어 이름 목록 반환.

        페어 개념이 없는 전략은 기본값(빈 리스트)을 반환합니다.
        페어 기반 전략은 이 메서드를 오버라이드합니다.
        """
        return []

    def filter_pairs(self, pair_names: list[str]) -> None:
        """
        특정 페어만 사용하도록 전략을 필터링.

        페어 개념이 없는 전략에서는 아무 동작도 하지 않습니다.
        페어 기반 전략은 이 메서드를 오버라이드하여
        내부 페어 목록을 축소합니다.

        Args:
            pair_names: 유지할 페어 이름 목록
        """
        pass

    def on_trade_executed(self, signal: TradeSignal, success: bool) -> None:
        """
        체결 콜백 — 전략이 내부 상태를 실제 체결 결과에 동기화.

        기본 구현은 아무 동작도 하지 않습니다.
        상태 추적이 필요한 전략만 오버라이드합니다.

        Args:
            signal: 체결된 (또는 실패한) 매매 신호
            success: 체결 성공 여부
        """
        pass

    # ── 유틸리티 ──

    def enable(self) -> None:
        self.enabled = True
        logger.info(f"전략 활성화: {self.name}")

    def disable(self) -> None:
        self.enabled = False
        logger.info(f"전략 비활성화: {self.name}")
