from __future__ import annotations

"""봇 제어 서비스 — 데이터 수집, 전략 실행, Kill Switch 관리

main.py의 AlgoTrader 패턴을 재사용:
  STRATEGY_REGISTRY → 활성 전략 인스턴스 생성
  required_codes() → load_daily_prices() → prepare_signal_kwargs() → generate_signals()
"""
import io
from datetime import datetime

from loguru import logger

from src.core.config import get_config, load_env
from src.core.risk_manager import RiskManager
from src.strategies import STRATEGY_REGISTRY
from src.strategies.base import BaseStrategy


def _build_strategies() -> list[BaseStrategy]:
    """STRATEGY_REGISTRY에서 활성 전략 인스턴스를 생성합니다."""
    config = get_config()
    strategies: list[BaseStrategy] = []
    for config_key, StrategyCls in STRATEGY_REGISTRY.items():
        if config["strategies"][config_key]["enabled"]:
            strategies.append(StrategyCls())
    return strategies


def collect_data() -> str:
    """데이터 수집 실행. 로그 문자열 반환."""
    load_env()
    from src.core.broker import KISBroker
    from src.core.data_manager import DataManager
    from src.execution.collector import DataCollector

    broker = KISBroker()
    dm = DataManager(broker)
    strategies = _build_strategies()
    collector = DataCollector(broker, dm, strategies)

    log_capture = io.StringIO()
    handler_id = logger.add(log_capture, format="{time:HH:mm:ss} | {level} | {message}")
    try:
        collector.collect_all()
    finally:
        logger.remove(handler_id)

    return log_capture.getvalue() or f"데이터 수집 완료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"


def _run_strategy(strategy: BaseStrategy, dm) -> list:
    """전략 1개 실행: required_codes → load → prepare → generate (main.py 패턴)"""
    price_data = {}
    for item in strategy.required_codes():
        code = item["code"]
        market = item["market"]
        df = dm.load_daily_prices(code, market)
        if not df.empty:
            price_data[code] = df["close"]

    if not price_data:
        logger.warning(f"{strategy.name}: 데이터 부족")
        return []

    kwargs = strategy.prepare_signal_kwargs(price_data)
    if not kwargs:
        return []

    return strategy.generate_signals(**kwargs)


def run_once() -> str:
    """전략 1회 실행. 로그 문자열 반환."""
    load_env()
    from src.core.broker import KISBroker
    from src.core.data_manager import DataManager
    from src.execution.collector import DataCollector
    from src.execution.executor import OrderExecutor
    from src.utils.notifier import TelegramNotifier

    config = get_config()
    broker = KISBroker()
    dm = DataManager(broker)
    rm = RiskManager()
    notifier = TelegramNotifier()
    strategies = _build_strategies()
    collector = DataCollector(broker, dm, strategies)
    executor = OrderExecutor(broker, rm, dm, notifier)

    log_capture = io.StringIO()
    handler_id = logger.add(log_capture, format="{time:HH:mm:ss} | {level} | {message}")
    try:
        # 데이터 수집
        collector.collect_all()

        # 전략 신호 생성 (제네릭 패턴)
        all_signals = []
        for strategy in strategies:
            all_signals.extend(_run_strategy(strategy, dm))

        # 알림 + 실행
        if all_signals:
            notifier.notify_signal("AlgoTrader", all_signals)
        executor.execute_signals(all_signals)
    finally:
        logger.remove(handler_id)

    return log_capture.getvalue() or "전략 실행 완료 (신호 없음)"


def get_kill_switch_status() -> bool:
    """현재 Kill Switch 상태 (파일 기반 영속 저장소에서 조회)"""
    rm = RiskManager()
    return rm.is_killed


def activate_kill_switch(reason: str = "대시보드에서 수동 활성화") -> None:
    rm = RiskManager()
    rm.activate_kill_switch(reason)


def deactivate_kill_switch() -> None:
    rm = RiskManager()
    rm.deactivate_kill_switch()
