from __future__ import annotations

"""
백테스트 서비스 — 통합 BacktestRunner를 통해 백테스트 실행

데이터 소스: DB 우선 → 룩백 부족 시 yfinance 자동 폴백.
"""
from src.backtest.engine import BacktestResult
from src.backtest.runner import BacktestRunner
from src.backtest.runner import _get_db_engine, _load_prices_from_db as load_prices_from_db


def run_backtest(
    strategy_name: str,
    initial_capital: float,
    start_date: str | None,
    end_date: str | None,
    commission_rate: float = 0.00015,
    slippage_rate: float = 0.001,
    pair_name: str | None = None,
) -> tuple[BacktestResult, dict]:
    """
    백테스트 실행 후 (BacktestResult, metrics dict) 반환.

    Args:
        pair_name: 특정 페어만 백테스트 (None이면 전체 페어)

    Raises:
        ValueError: 데이터 없음
    """
    runner = BacktestRunner()
    return runner.run(
        strategy_name=strategy_name,
        start_date=start_date or "",
        end_date=end_date or "",
        initial_capital=initial_capital,
        commission_rate=commission_rate,
        slippage_rate=slippage_rate,
        pair_name=pair_name,
    )


def run_backtest_per_pair(
    strategy_name: str,
    initial_capital: float,
    start_date: str | None,
    end_date: str | None,
    commission_rate: float = 0.00015,
    slippage_rate: float = 0.001,
) -> dict[str, tuple[BacktestResult, dict]]:
    """
    페어별 개별 백테스트 실행 후 결과 딕셔너리 반환.

    Returns:
        {pair_name: (BacktestResult, metrics)}
    """
    runner = BacktestRunner()
    return runner.run_per_pair(
        strategy_name=strategy_name,
        start_date=start_date or "",
        end_date=end_date or "",
        initial_capital=initial_capital,
        commission_rate=commission_rate,
        slippage_rate=slippage_rate,
    )


def get_pair_names(strategy_name: str) -> list[str]:
    """전략의 페어 이름 목록 반환 (페어 기반이 아니면 빈 리스트)"""
    runner = BacktestRunner()
    strategy = runner._create_strategy(strategy_name)
    return strategy.get_pair_names()
