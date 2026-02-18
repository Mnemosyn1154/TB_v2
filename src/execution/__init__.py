"""
AlgoTrader KR — Execution 패키지

데이터 수집 오케스트레이션과 주문 실행을 담당합니다.

공개 API:
    - DataCollector: 전략별 데이터 수집 오케스트레이터
    - OrderExecutor: 매매 신호 → 주문 실행 엔진
"""
from src.execution.collector import DataCollector
from src.execution.executor import OrderExecutor

__all__ = [
    "DataCollector",
    "OrderExecutor",
]
