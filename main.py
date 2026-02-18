from __future__ import annotations

"""
AlgoTrader KR — 메인 진입점

CLI를 통해 트레이딩 사이클을 실행하는 얇은 오케스트레이터.
직접적인 비즈니스 로직은 포함하지 않으며, 각 모듈에 위임합니다.

실행 흐름:
    1. DataCollector.collect_all() — 시세 데이터 수집
    2. Strategy.generate_signals() — 매매 신호 생성
    3. OrderExecutor.execute_signals() — 리스크 검증 + 주문 실행
    4. BacktestEngine.run() — 과거 데이터 시뮬레이션 (backtest 모드)

Depends on:
    - src.execution.collector (데이터 수집)
    - src.execution.executor (주문 실행)
    - src.backtest.* (백테스팅)
    - src.strategies.* (전략 분석)
    - src.core.* (인프라)
    - src.utils.* (로깅/알림)

Modification Guide:
    - 새 전략 추가: STRATEGY_REGISTRY에 1줄 + settings.yaml 설정만 추가
    - CLI 커맨드 추가: main()의 argparse에 choices 추가
    - 상세 로직 변경: 해당 모듈(collector/executor/strategy)에서 직접 수정
"""
import sys
import json
from datetime import datetime
from pathlib import Path

from loguru import logger

# 프로젝트 루트를 sys.path에 추가
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

from src.utils.logger import setup_logger
from src.core.config import get_config, load_env
from src.core.broker import KISBroker
from src.core.data_manager import DataManager
from src.core.risk_manager import RiskManager
from src.execution.collector import DataCollector
from src.execution.executor import OrderExecutor
from src.strategies import STRATEGY_REGISTRY, resolve_strategy
from src.strategies.base import BaseStrategy
from src.utils.notifier import TelegramNotifier


class AlgoTrader:
    """
    메인 트레이딩 오케스트레이터.

    각 모듈을 초기화하고 트레이딩 사이클 (수집 → 분석 → 실행)을 조율합니다.
    직접적인 비즈니스 로직은 수행하지 않습니다.
    """

    def __init__(self):
        setup_logger()
        load_env()

        logger.info("=" * 60)
        logger.info("🤖 AlgoTrader KR 시작")
        logger.info("=" * 60)

        self.config = get_config()

        # ── 핵심 인프라 초기화 ──
        self.broker = KISBroker()
        self.data_manager = DataManager(self.broker)
        self.risk_manager = RiskManager()
        self.notifier = TelegramNotifier()

        # ── 전략 초기화 (레지스트리 기반) ──
        self.strategies: list[BaseStrategy] = []
        for config_key, strat_config in self.config["strategies"].items():
            if strat_config.get("enabled", False):
                self.strategies.append(resolve_strategy(config_key, strat_config))

        logger.info(f"활성 전략: {[s.name for s in self.strategies]}")

        # ── 실행 엔진 초기화 (전략 리스트 전달) ──
        self.collector = DataCollector(self.broker, self.data_manager, self.strategies)
        self.executor = OrderExecutor(
            self.broker, self.risk_manager, self.data_manager, self.notifier,
            strategies=self.strategies,
        )

    # ──────────────────────────────────────────────
    # 전략 실행 — 제네릭 데이터 로드 + 신호 생성
    # ──────────────────────────────────────────────

    def _run_strategy(self, strategy: BaseStrategy) -> list:
        """전략 1개 실행: DB에서 데이터 로드 → prepare → generate_signals"""
        price_data = {}
        for item in strategy.required_codes():
            code = item["code"]
            market = item["market"]
            df = self.data_manager.load_daily_prices(code, market)
            if not df.empty:
                price_data[code] = df["close"]

        if not price_data:
            logger.warning(f"{strategy.name}: 데이터 부족")
            return []

        kwargs = strategy.prepare_signal_kwargs(price_data)
        if not kwargs:
            return []

        return strategy.generate_signals(**kwargs)

    # ──────────────────────────────────────────────
    # 메인 사이클
    # ──────────────────────────────────────────────

    def run_once(self) -> None:
        """
        전체 트레이딩 사이클 1회 실행.

        흐름: 데이터 수집 → 전략 분석 → 알림 → 주문 실행 → 상태 로깅
        """
        logger.info("─" * 40)
        logger.info(f"🔄 트레이딩 사이클 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        try:
            # 1. 데이터 수집 (DataCollector에 위임)
            self.collector.collect_all()

            # 2. 전략 실행 → 신호 생성
            all_signals = []
            for strategy in self.strategies:
                all_signals.extend(self._run_strategy(strategy))

            # 3. 신호 알림
            if all_signals:
                self.notifier.notify_signal("AlgoTrader", all_signals)

            # 4. 주문 실행 (OrderExecutor에 위임)
            self.executor.execute_signals(all_signals)

            # 5. 상태 로깅
            risk_summary = self.risk_manager.get_risk_summary()
            logger.info(f"리스크 요약: {json.dumps(risk_summary, indent=2, ensure_ascii=False)}")

        except Exception as e:
            logger.error(f"트레이딩 사이클 에러: {e}")
            self.notifier.notify_error(str(e))

        logger.info("✅ 트레이딩 사이클 완료")

    def show_status(self) -> None:
        """활성 전략 + 리스크 상태를 콘솔에 출력합니다."""
        print("\n" + "=" * 60)
        print("🤖 AlgoTrader KR — 현재 상태")
        print("=" * 60)

        for strategy in self.strategies:
            status = strategy.get_status()
            print(f"\n📈 {status['strategy']} ({'활성' if status['enabled'] else '비활성'})")
            print(json.dumps(status, indent=2, ensure_ascii=False))

        risk = self.risk_manager.get_risk_summary()
        print(f"\n🛡️ 리스크 상태")
        print(json.dumps(risk, indent=2, ensure_ascii=False))
        print("=" * 60)

    def run_backtest(self, strategy_name: str | None = None) -> None:
        """
        백테스트 실행 (통합 BacktestRunner 사용, DB 우선 → yfinance 폴백).

        Args:
            strategy_name: 실행할 전략 키 (stat_arb / dual_momentum / quant_factor).
                           None이면 모든 활성 전략.
        """
        from src.backtest.runner import BacktestRunner

        bt_config = self.config.get("backtest", {})
        initial_capital = bt_config.get("initial_capital", 10_000_000)
        start_date = bt_config.get("start_date")
        end_date = bt_config.get("end_date")

        runner = BacktestRunner()

        # 실행할 전략 키 목록 결정
        if strategy_name:
            keys_to_test = [strategy_name]
        else:
            keys_to_test = [
                key for key, cfg in self.config["strategies"].items()
                if cfg.get("enabled", False)
            ]

        if not keys_to_test:
            logger.warning("활성 전략이 없습니다.")
            return

        for key in keys_to_test:
            try:
                result, metrics = runner.run(key, start_date, end_date, initial_capital)
                runner.report(result)
            except Exception as e:
                logger.error(f"{key} 백테스트 실패: {e}")


def run_backtest_yf(args):
    """
    yfinance 백테스트 실행 (AlgoTrader 인스턴스 없이 독립 실행).

    통합 BacktestRunner를 사용하며, DB 데이터 부족 시 자동으로 yfinance 폴백.
    --pair: 특정 페어만 백테스트
    --per-pair: 모든 페어를 개별 백테스트 후 비교 테이블 출력
    """
    setup_logger()
    load_env()

    from src.backtest.runner import BacktestRunner

    runner = BacktestRunner()

    strategy = args.strategy
    start = args.start
    end = args.end
    capital = args.capital
    pair = getattr(args, "pair", None)
    per_pair = getattr(args, "per_pair", False)

    logger.info(f"백테스트: {strategy} | {start} ~ {end} | 자본금 ₩{capital:,.0f}")

    if strategy == "all":
        if per_pair or pair:
            logger.warning("--pair / --per-pair 옵션은 'all' 전략에서 사용할 수 없습니다.")
        results = runner.run_all(start, end, capital)
        for name, (result, metrics) in results.items():
            runner.report(result, charts=args.chart, csv=args.csv)
    elif per_pair:
        # 페어별 개별 백테스트 + 비교
        results = runner.run_per_pair(strategy, start, end, capital)
        runner.print_pair_comparison(results, strategy, start, end)
        for pname, (result, metrics) in results.items():
            runner.report(result, charts=args.chart, csv=args.csv)
    elif pair:
        # 특정 페어만 백테스트
        try:
            result, metrics = runner.run(strategy, start, end, capital, pair_name=pair)
            runner.report(result, charts=args.chart, csv=args.csv)
        except ValueError as e:
            logger.error(str(e))
    else:
        # 기존 동작 (전체 페어 합산)
        try:
            result, metrics = runner.run(strategy, start, end, capital)
            runner.report(result, charts=args.chart, csv=args.csv)
        except ValueError as e:
            logger.error(str(e))


def main():
    """
    CLI 진입점.

    사용법:
        python3 main.py run                           # 전략 1회 실행
        python3 main.py status                        # 현재 상태 조회
        python3 main.py collect                       # 데이터 수집만
        python3 main.py backtest --strategy stat_arb  # DB 백테스트
        python3 main.py backtest-yf -s dual_momentum --start 2020-01-01 --end 2024-12-31
        python3 main.py backtest-yf -s all --start 2020-01-01 --end 2024-12-31 --capital 50000000
        python3 main.py backtest-yf -s stat_arb --per-pair --start 2020-01-01 --end 2024-12-31
        python3 main.py backtest-yf -s stat_arb --pair Samsung_Hynix --start 2020-01-01 --end 2024-12-31
    """
    import argparse

    parser = argparse.ArgumentParser(description="AlgoTrader KR — 자동 트레이딩 봇")
    subparsers = parser.add_subparsers(dest="command", help="실행 명령")

    # 기존 명령
    subparsers.add_parser("run", help="전략 1회 실행")
    subparsers.add_parser("status", help="현재 상태 조회")
    subparsers.add_parser("collect", help="데이터 수집만")

    # DB 백테스트 (main 엔진)
    bt_parser = subparsers.add_parser("backtest", help="백테스트 (DB 데이터)")
    bt_parser.add_argument("--strategy", type=str, default=None,
                           help="백테스트할 전략 (stat_arb / dual_momentum)")

    # yfinance 백테스트 (독립 실행)
    bt_yf_parser = subparsers.add_parser("backtest-yf", help="백테스트 (yfinance 데이터, API 키 불필요)")
    bt_yf_parser.add_argument("-s", "--strategy", required=True,
                              choices=["stat_arb", "dual_momentum", "quant_factor", "all"],
                              help="백테스트할 전략")
    bt_yf_parser.add_argument("--start", required=True,
                              help="시작일 (YYYY-MM-DD)")
    bt_yf_parser.add_argument("--end", required=True,
                              help="종료일 (YYYY-MM-DD)")
    bt_yf_parser.add_argument("--capital", type=float, default=10_000_000,
                              help="초기 자본금 KRW (기본: 10,000,000원)")
    bt_yf_parser.add_argument("--chart", action="store_true", default=True,
                              help="차트 생성 (기본: 활성)")
    bt_yf_parser.add_argument("--no-chart", dest="chart", action="store_false",
                              help="차트 생성 비활성")
    bt_yf_parser.add_argument("--csv", action="store_true", default=False,
                              help="거래 내역 CSV 내보내기")
    bt_yf_parser.add_argument("--pair", type=str, default=None,
                              help="특정 페어만 백테스트 (예: Samsung_Hynix)")
    bt_yf_parser.add_argument("--per-pair", action="store_true", default=False,
                              help="모든 페어를 개별 백테스트 후 비교")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    # yfinance 백테스트 (AlgoTrader 인스턴스 불필요)
    if args.command == "backtest-yf":
        run_backtest_yf(args)
        return

    # 이하 명령은 AlgoTrader 인스턴스 필요
    trader = AlgoTrader()

    if args.command == "run":
        trader.run_once()
    elif args.command == "status":
        trader.show_status()
    elif args.command == "collect":
        trader.collector.collect_all()
        logger.info("데이터 수집 완료")
    elif args.command == "backtest":
        trader.run_backtest(args.strategy)


if __name__ == "__main__":
    main()
