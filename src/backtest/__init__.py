"""
AlgoTrader KR — Backtest 패키지

과거 데이터 기반 전략 시뮬레이션 및 성과 분석.

공개 API:
    - BacktestEngine: 이벤트 드리븐 시뮬레이터
    - PerformanceAnalyzer: 성과 지표 계산 + 리포트
    - BacktestResult: 시뮬레이션 결과 컨테이너
    - Trade: 개별 거래 기록
    - BacktestRunner: yfinance 기반 독립 백테스트 실행기
    - BacktestReporter: 차트/CSV 리포트 생성
"""
from src.backtest.engine import BacktestEngine, BacktestResult, Trade
from src.backtest.analyzer import PerformanceAnalyzer

__all__ = [
    "BacktestEngine",
    "BacktestResult",
    "Trade",
    "PerformanceAnalyzer",
]
