from __future__ import annotations

"""
AlgoTrader KR — 백테스트 성과 분석기

BacktestResult를 받아 핵심 성과 지표를 계산하고 리포트를 출력합니다.

지표: 총 수익률, CAGR, 샤프 비율, 소르티노, MDD, 승률, 손익비, 월별 수익률

Depends on:
    - src.backtest.engine (BacktestResult, Trade)

Used by:
    - main.py (CLI backtest 커맨드 후 리포트 출력)

Modification Guide:
    - 새 지표 추가: summary()에 키 추가 + print_report()에 출력 행 추가
    - 차트 출력: matplotlib 연동 시 plot_equity_curve() 메서드 추가
"""
import numpy as np
import pandas as pd
from loguru import logger

from src.backtest.engine import BacktestResult, Trade


class PerformanceAnalyzer:
    """
    백테스트 성과 분석기.

    사용법:
        analyzer = PerformanceAnalyzer(result)
        metrics = analyzer.summary()
        analyzer.print_report()
    """

    TRADING_DAYS_PER_YEAR = 252
    RISK_FREE_RATE = 0.04  # 연 4%

    def __init__(self, result: BacktestResult):
        self.result = result
        self._metrics: dict | None = None

    def summary(self) -> dict:
        """핵심 성과 지표를 계산하여 dict로 반환"""
        if self._metrics is not None:
            return self._metrics

        r = self.result

        # 기본값 (데이터 부족 시)
        if r.equity_curve is None or len(r.equity_curve) < 2:
            self._metrics = self._empty_metrics()
            return self._metrics

        # ── 수익률 지표 ──
        total_return = (r.final_equity - r.initial_capital) / r.initial_capital
        n_days = len(r.equity_curve)
        n_years = n_days / self.TRADING_DAYS_PER_YEAR

        cagr = (r.final_equity / r.initial_capital) ** (1 / n_years) - 1 if n_years > 0 else 0.0

        # ── 변동성 ──
        daily_ret = r.daily_returns
        annual_vol = daily_ret.std() * np.sqrt(self.TRADING_DAYS_PER_YEAR) if len(daily_ret) > 1 else 0.0

        # ── 샤프 비율 ──
        daily_rf = self.RISK_FREE_RATE / self.TRADING_DAYS_PER_YEAR
        excess_daily_return = daily_ret.mean() - daily_rf
        sharpe = (excess_daily_return / daily_ret.std() * np.sqrt(self.TRADING_DAYS_PER_YEAR)
                  if daily_ret.std() > 0 else 0.0)

        # ── 소르티노 비율 ──
        downside = daily_ret[daily_ret < 0]
        downside_std = downside.std() * np.sqrt(self.TRADING_DAYS_PER_YEAR) if len(downside) > 1 else 0.0
        sortino = (cagr - self.RISK_FREE_RATE) / downside_std if downside_std > 0 else 0.0

        # ── MDD ──
        equity = r.equity_curve
        cummax = equity.cummax()
        drawdown = (equity - cummax) / cummax
        mdd = drawdown.min()
        mdd_date = drawdown.idxmin().strftime("%Y-%m-%d") if len(drawdown) > 0 else ""

        # MDD 복구일
        mdd_end_idx = drawdown.idxmin()
        recovery = drawdown[mdd_end_idx:]
        recovery_dates = recovery[recovery >= 0]
        mdd_recovery = recovery_dates.index[0].strftime("%Y-%m-%d") if len(recovery_dates) > 0 else "미복구"

        # ── 거래 분석 ──
        sell_trades = [t for t in r.trades if t.side == "SELL"]
        n_trades = len(sell_trades)

        if n_trades > 0:
            winning = [t for t in sell_trades if t.pnl > 0]
            losing = [t for t in sell_trades if t.pnl <= 0]
            win_rate = len(winning) / n_trades
            avg_win = np.mean([t.pnl for t in winning]) if winning else 0.0
            avg_loss = abs(np.mean([t.pnl for t in losing])) if losing else 0.0
            profit_factor = avg_win / avg_loss if avg_loss > 0 else float("inf")
            avg_holding = np.mean([t.holding_days for t in sell_trades])
            max_win = max([t.pnl for t in sell_trades])
            max_loss = min([t.pnl for t in sell_trades])
            total_commission = sum(t.commission for t in r.trades)
        else:
            win_rate = 0.0
            avg_win = avg_loss = 0.0
            profit_factor = 0.0
            avg_holding = 0.0
            max_win = max_loss = 0.0
            total_commission = 0.0

        # ── 월별 수익률 ──
        monthly_returns = self._calc_monthly_returns(r.equity_curve)

        self._metrics = {
            # 기본 정보
            "strategy": r.strategy_name,
            "period": f"{r.start_date} ~ {r.end_date}",
            "trading_days": n_days,
            "initial_capital": r.initial_capital,
            "final_equity": r.final_equity,

            # 수익률
            "total_return": total_return,
            "cagr": cagr,
            "annual_volatility": annual_vol,

            # 위험 조정 수익률
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,

            # 낙폭
            "mdd": mdd,
            "mdd_date": mdd_date,
            "mdd_recovery": mdd_recovery,

            # 거래 분석
            "total_trades": n_trades,
            "buy_trades": len([t for t in r.trades if t.side == "BUY"]),
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
            "avg_holding_days": avg_holding,
            "max_win": max_win,
            "max_loss": max_loss,
            "total_commission": total_commission,

            # 월별 수익률
            "monthly_returns": monthly_returns,
        }

        return self._metrics

    def print_report(self) -> None:
        """성과 리포트를 콘솔에 출력"""
        m = self.summary()

        print()
        print("═" * 55)
        print(f"  📊 백테스트 리포트: {m['strategy']}")
        print("═" * 55)
        print(f"  기간:     {m['period']} ({m['trading_days']}일)")
        print(f"  초기자본:  ₩{m['initial_capital']:>14,.0f}")
        print(f"  최종자산:  ₩{m['final_equity']:>14,.0f}")
        print("─" * 55)

        # 수익률 섹션
        print("  📈 수익률")
        print(f"    총 수익률:      {m['total_return']:>+10.2%}")
        print(f"    CAGR:           {m['cagr']:>+10.2%}")
        print(f"    연 변동성:      {m['annual_volatility']:>10.2%}")
        print()

        # 위험 조정
        print("  📐 위험 조정 수익률")
        print(f"    샤프 비율:      {m['sharpe_ratio']:>10.2f}")
        print(f"    소르티노:       {m['sortino_ratio']:>10.2f}")
        print()

        # 낙폭
        print("  📉 낙폭")
        print(f"    MDD:            {m['mdd']:>+10.2%}")
        print(f"    MDD 일자:       {m['mdd_date']:>10s}")
        print(f"    복구:           {m['mdd_recovery']:>10s}")
        print()

        # 거래 분석
        print("  🔄 거래 분석")
        print(f"    총 거래:        {m['total_trades']:>10d}건")
        print(f"    승률:           {m['win_rate']:>10.1%}")
        print(f"    손익비:         {m['profit_factor']:>10.2f}")
        print(f"    평균 수익:      {m['avg_win']:>+10,.0f}")
        print(f"    평균 손실:      {m['avg_loss']:>10,.0f}")
        print(f"    최대 수익:      {m['max_win']:>+10,.0f}")
        print(f"    최대 손실:      {m['max_loss']:>+10,.0f}")
        print(f"    평균 보유일:    {m['avg_holding_days']:>10.1f}일")
        print(f"    총 수수료:      {m['total_commission']:>10,.0f}")
        print()

        # 월별 수익률 테이블
        monthly = m.get("monthly_returns")
        if monthly is not None and not monthly.empty:
            print("  📅 월별 수익률 (%)")
            print("─" * 55)
            self._print_monthly_table(monthly)

        print("═" * 55)
        print()

    # ──────────────────────────────────────
    # 내부 메서드
    # ──────────────────────────────────────

    def _calc_monthly_returns(self, equity_curve: pd.Series) -> pd.DataFrame | None:
        """월별 수익률 테이블 생성"""
        if equity_curve is None or len(equity_curve) < 2:
            return None

        monthly = equity_curve.resample("ME").last()
        monthly_ret = monthly.pct_change().dropna()

        if monthly_ret.empty:
            return None

        # year × month 피벗
        df = pd.DataFrame({
            "year": monthly_ret.index.year,
            "month": monthly_ret.index.month,
            "return": monthly_ret.values,
        })

        pivot = df.pivot_table(index="year", columns="month", values="return", aggfunc="first")
        pivot.columns = [f"{m}월" for m in pivot.columns]

        # 연간 합계
        pivot["연합계"] = pivot.sum(axis=1)

        return pivot

    def _print_monthly_table(self, monthly: pd.DataFrame) -> None:
        """월별 수익률 테이블을 콘솔에 출력"""
        # 헤더
        cols = monthly.columns.tolist()
        header = "    연도  " + " ".join(f"{c:>6s}" for c in cols)
        print(header)
        print("    " + "─" * (len(header) - 4))

        for year, row in monthly.iterrows():
            values = []
            for val in row:
                if pd.isna(val):
                    values.append(f"{'':>6s}")
                else:
                    values.append(f"{val*100:>+5.1f}%")
            print(f"    {year}  " + " ".join(values))
        print()

    @staticmethod
    def _empty_metrics() -> dict:
        """데이터 부족 시 빈 지표 반환"""
        return {
            "strategy": "", "period": "", "trading_days": 0,
            "initial_capital": 0, "final_equity": 0,
            "total_return": 0, "cagr": 0, "annual_volatility": 0,
            "sharpe_ratio": 0, "sortino_ratio": 0,
            "mdd": 0, "mdd_date": "", "mdd_recovery": "",
            "total_trades": 0, "buy_trades": 0, "win_rate": 0,
            "avg_win": 0, "avg_loss": 0, "profit_factor": 0,
            "avg_holding_days": 0, "max_win": 0, "max_loss": 0,
            "total_commission": 0, "monthly_returns": None,
        }
