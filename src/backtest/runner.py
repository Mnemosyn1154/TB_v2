"""
AlgoTrader KR — 통합 백테스트 실행기

CLI와 대시보드에서 공통으로 사용하는 백테스트 오케스트레이터.
데이터 소스: DB 우선 → 룩백 부족 시 yfinance 폴백.

사용법:
    runner = BacktestRunner()
    result, metrics = runner.run("dual_momentum", "2020-01-01", "2024-12-31")
    result, metrics = runner.run("stat_arb", "2020-01-01", "2024-12-31", capital=50_000_000)

Depends on:
    - src.core.data_feed (yfinance 데이터)
    - src.core.config (전략 설정)
    - src.backtest.engine (BacktestEngine)
    - src.backtest.analyzer (PerformanceAnalyzer)
    - src.backtest.report (리포트 생성)
    - src.strategies (STRATEGY_REGISTRY)

Used by:
    - main.py (CLI backtest / backtest-yf 명령)
    - dashboard/services/backtest_service.py (Streamlit 대시보드)
"""
from __future__ import annotations

import pandas as pd
from loguru import logger
from sqlalchemy import create_engine, text

from src.core.config import get_config, DATA_DIR
from src.backtest.engine import BacktestEngine, BacktestResult
from src.backtest.analyzer import PerformanceAnalyzer
from src.backtest.report import BacktestReporter
from src.strategies.base import BaseStrategy


# yfinance는 선택 의존성
try:
    from src.core.data_feed import DataFeed
    _YF_AVAILABLE = True
except ImportError:
    _YF_AVAILABLE = False


class BacktestRunner:
    """통합 백테스트 실행기 — DB 우선, yfinance 폴백"""

    LOOKBACK_EXTRA = 400  # 전략 룩백 기간 버퍼 (캘린더일)

    def __init__(self):
        self.config = get_config()
        self.reporter = BacktestReporter()

    # ──────────────────────────────────────────────
    # 핵심 API
    # ──────────────────────────────────────────────

    def run(
        self,
        strategy_name: str,
        start_date: str,
        end_date: str,
        initial_capital: float = 10_000_000,
        commission_rate: float | None = None,
        slippage_rate: float | None = None,
        pair_name: str | None = None,
    ) -> tuple[BacktestResult, dict]:
        """
        백테스트 실행. DB 우선 → 룩백 부족 시 yfinance 폴백.

        Args:
            strategy_name: 전략 키 (stat_arb / dual_momentum / quant_factor)
            start_date: 시작일 (YYYY-MM-DD)
            end_date: 종료일 (YYYY-MM-DD)
            initial_capital: 초기 자본금 (KRW)
            commission_rate: 수수료율 (None이면 설정 파일 값)
            slippage_rate: 슬리피지율 (None이면 설정 파일 값)
            pair_name: 특정 페어만 백테스트 (None이면 전체 페어)

        Returns:
            (BacktestResult, metrics dict)

        Raises:
            ValueError: 전략을 찾을 수 없거나 데이터가 없을 때
        """
        bt_config = self.config.get("backtest", {})
        commission = commission_rate if commission_rate is not None else bt_config.get("commission_rate", 0.00015)
        slippage = slippage_rate if slippage_rate is not None else bt_config.get("slippage_rate", 0.001)

        # 1. 전략 인스턴스 생성
        strategy = self._create_strategy(strategy_name)

        # 1.5. 페어 필터링 (per-pair 백테스트)
        if pair_name is not None:
            available_pairs = strategy.get_pair_names()
            if available_pairs and pair_name not in available_pairs:
                raise ValueError(
                    f"알 수 없는 페어: {pair_name} "
                    f"(사용 가능: {available_pairs})"
                )
            if available_pairs:
                strategy.filter_pairs([pair_name])

        pair_label = f" [{pair_name}]" if pair_name else ""
        logger.info(f"{'='*50}")
        logger.info(f"💻 백테스트 시작: {strategy.name}{pair_label} ({start_date} ~ {end_date})")
        logger.info(f"{'='*50}")

        # 2. 데이터 로드 (DB 우선 → yfinance 폴백)
        price_data, data_source = self._load_data(strategy, start_date, end_date)
        if not price_data:
            raise ValueError(
                "데이터가 없습니다. '봇 제어' 탭에서 데이터를 수집하거나 "
                "yfinance 설치를 확인하세요. (pip install yfinance)"
            )

        logger.info(f"📂 데이터 소스: {data_source} | "
                     f"종목: {list(price_data.keys())} | "
                     f"총 {sum(len(df) for df in price_data.values())}행")

        # 3. 엔진 실행
        engine = BacktestEngine(
            strategy=strategy,
            initial_capital=initial_capital,
            commission_rate=commission,
            slippage_rate=slippage,
        )
        result = engine.run(price_data, start_date, end_date)

        # 4. 분석
        analyzer = PerformanceAnalyzer(result)
        metrics = analyzer.summary()
        metrics["data_source"] = data_source

        return result, metrics

    def run_all(
        self,
        start_date: str,
        end_date: str,
        initial_capital: float = 10_000_000,
    ) -> dict[str, tuple[BacktestResult, dict]]:
        """모든 활성 전략 백테스트"""
        from src.strategies import STRATEGY_REGISTRY

        results = {}
        for name in STRATEGY_REGISTRY:
            if self.config["strategies"].get(name, {}).get("enabled", False):
                try:
                    results[name] = self.run(name, start_date, end_date, initial_capital)
                except Exception as e:
                    logger.error(f"{name} 백테스트 실패: {e}")
        return results

    def run_per_pair(
        self,
        strategy_name: str,
        start_date: str,
        end_date: str,
        initial_capital: float = 10_000_000,
        commission_rate: float | None = None,
        slippage_rate: float | None = None,
    ) -> dict[str, tuple[BacktestResult, dict]]:
        """
        전략의 각 페어를 개별적으로 백테스트하고 결과 비교.

        페어 개념이 없는 전략은 전체 전략을 1회 실행.

        Args:
            strategy_name: 전략 키
            start_date: 시작일
            end_date: 종료일
            initial_capital: 초기 자본금
            commission_rate: 수수료율
            slippage_rate: 슬리피지율

        Returns:
            {pair_name: (BacktestResult, metrics)} 딕셔너리
        """
        # 임시 인스턴스로 페어 목록 확인
        temp_strategy = self._create_strategy(strategy_name)
        pair_names = temp_strategy.get_pair_names()

        if not pair_names:
            # 페어 기반이 아닌 전략 → 전체 실행
            logger.info(f"{strategy_name}은 페어 기반 전략이 아닙니다. 전체 백테스트 실행.")
            result, metrics = self.run(
                strategy_name, start_date, end_date,
                initial_capital, commission_rate, slippage_rate,
            )
            return {strategy_name: (result, metrics)}

        logger.info(f"페어별 백테스트 시작: {strategy_name} | {len(pair_names)}개 페어")

        results: dict[str, tuple[BacktestResult, dict]] = {}
        for pname in pair_names:
            try:
                result, metrics = self.run(
                    strategy_name, start_date, end_date,
                    initial_capital, commission_rate, slippage_rate,
                    pair_name=pname,
                )
                results[pname] = (result, metrics)
                logger.info(f"  {pname}: 수익률={metrics['total_return']:.2%}, "
                            f"샤프={metrics['sharpe_ratio']:.2f}")
            except Exception as e:
                logger.error(f"  {pname} 백테스트 실패: {e}")

        return results

    def print_pair_comparison(
        self,
        results: dict[str, tuple[BacktestResult, dict]],
        strategy_name: str,
        start_date: str,
        end_date: str,
    ) -> None:
        """페어별 백테스트 결과 비교 테이블 출력"""
        if not results:
            logger.warning("비교할 결과가 없습니다.")
            return

        print()
        print("=" * 75)
        print(f"  페어별 백테스트 비교: {strategy_name} ({start_date} ~ {end_date})")
        print("=" * 75)
        print(f"  {'페어':<20s} {'수익률':>8s} {'CAGR':>8s} {'샤프':>6s} "
              f"{'MDD':>8s} {'거래':>5s} {'승률':>6s}")
        print(f"  {'─' * 69}")

        for pair_name, (result, metrics) in results.items():
            total_return = metrics.get("total_return", 0)
            cagr = metrics.get("cagr", 0)
            sharpe = metrics.get("sharpe_ratio", 0)
            mdd = metrics.get("mdd", 0)
            trades = metrics.get("total_trades", 0)
            win_rate = metrics.get("win_rate", 0)

            print(f"  {pair_name:<20s} {total_return:>+7.1%} {cagr:>+7.1%} "
                  f"{sharpe:>6.2f} {mdd:>+7.1%} {trades:>5d} {win_rate:>5.1%}")

        print("=" * 75)
        print()

    def report(self, result: BacktestResult, charts: bool = True,
               csv: bool = False) -> None:
        """백테스트 결과 리포트 출력 (CLI용)"""
        analyzer = PerformanceAnalyzer(result)
        analyzer.print_report()

        if charts:
            self.reporter.plot_equity_curve(result)
            self.reporter.plot_monthly_returns(result)

        if csv:
            self.reporter.export_trades_csv(result)

    # ──────────────────────────────────────────────
    # 데이터 로드
    # ──────────────────────────────────────────────

    def _load_data(
        self,
        strategy: BaseStrategy,
        start_date: str,
        end_date: str,
    ) -> tuple[dict[str, pd.DataFrame], str]:
        """DB 우선 → 룩백 부족 시 yfinance 폴백"""
        # DB 시도
        db_data = self._load_from_db(strategy)
        if db_data and self._has_enough_lookback(db_data, start_date):
            return db_data, "DB"

        # yfinance 폴백
        if _YF_AVAILABLE:
            try:
                yf_data = self._load_from_yfinance(strategy, start_date, end_date)
                if yf_data:
                    logger.info("DB 데이터 부족 → yfinance 폴백 사용")
                    return yf_data, "yfinance"
            except Exception as e:
                logger.warning(f"yfinance 폴백 실패: {e}")

        # DB 데이터라도 있으면 사용 (거래 0건 가능)
        if db_data:
            logger.warning("DB 데이터 룩백 부족 — 거래가 발생하지 않을 수 있습니다")
            return db_data, "DB (룩백 부족)"

        return {}, ""

    def _load_from_db(self, strategy: BaseStrategy) -> dict[str, pd.DataFrame]:
        """DB에서 전략 필요 종목 데이터 로드"""
        price_data: dict[str, pd.DataFrame] = {}

        for item in strategy.required_codes():
            code = item["code"]
            market = item["market"]
            df = _load_prices_from_db(code, market)
            if not df.empty:
                price_data[code] = df

        return price_data

    def _load_from_yfinance(
        self,
        strategy: BaseStrategy,
        start_date: str,
        end_date: str,
    ) -> dict[str, pd.DataFrame]:
        """yfinance에서 룩백 포함 데이터 로드"""
        feed = DataFeed()
        fetch_start = pd.to_datetime(start_date) - pd.Timedelta(days=self.LOOKBACK_EXTRA)

        symbols: dict[str, str] = {}
        for item in strategy.required_codes():
            symbols[item["code"]] = item["market"]

        return feed.fetch_multiple(symbols, str(fetch_start.date()), end_date)

    def _has_enough_lookback(
        self,
        price_data: dict[str, pd.DataFrame],
        start_date: str,
    ) -> bool:
        """DB 데이터가 start_date 이전 충분한 룩백 기간을 포함하는지 확인"""
        if not price_data or not start_date:
            return False

        start_dt = pd.to_datetime(start_date)
        earliest_needed = start_dt - pd.Timedelta(days=self.LOOKBACK_EXTRA)

        for code, df in price_data.items():
            if df.empty:
                continue
            earliest_date = pd.to_datetime(df["date"]).min()
            if earliest_date > earliest_needed:
                return False

        return True

    # ──────────────────────────────────────────────
    # 전략 생성
    # ──────────────────────────────────────────────

    @staticmethod
    def _create_strategy(name: str) -> BaseStrategy:
        """STRATEGY_REGISTRY에서 전략 인스턴스 생성"""
        from src.strategies import STRATEGY_REGISTRY

        cls = STRATEGY_REGISTRY.get(name)
        if cls is None:
            available = list(STRATEGY_REGISTRY.keys())
            raise ValueError(f"알 수 없는 전략: {name} (사용 가능: {available})")
        return cls()


# ──────────────────────────────────────────────
# DB 유틸리티 (대시보드 서비스에서 이전)
# ──────────────────────────────────────────────

def _get_db_engine():
    """SQLite 엔진"""
    db_path = DATA_DIR / "trading_bot.db"
    return create_engine(f"sqlite:///{db_path}")


def _load_prices_from_db(code: str, market: str) -> pd.DataFrame:
    """SQLite에서 종가 데이터 로드"""
    engine = _get_db_engine()
    query = text("""
        SELECT date, open, high, low, close, volume
        FROM daily_prices
        WHERE code = :code AND market = :market
        ORDER BY date ASC
    """)
    try:
        df = pd.read_sql(query, engine, params={"code": code, "market": market})
    except Exception:
        return pd.DataFrame()

    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df
