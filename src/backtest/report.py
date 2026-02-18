from __future__ import annotations

"""
AlgoTrader KR — 백테스트 리포트

차트(equity curve, drawdown, 월별 수익률), CSV 내보내기.
콘솔 리포트는 PerformanceAnalyzer.print_report()를 사용합니다.

Depends on:
    - src.backtest.engine (BacktestResult)
    - src.backtest.analyzer (PerformanceAnalyzer)
    - matplotlib (차트)
    - pandas

Used by:
    - src.backtest.runner (백테스트 실행 후 리포트 생성)
"""
import numpy as np
import pandas as pd
from loguru import logger

from src.backtest.engine import BacktestResult

try:
    import matplotlib
    matplotlib.use("Agg")  # 비대화형 백엔드
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    MPL_AVAILABLE = True
except ImportError:
    MPL_AVAILABLE = False
    logger.warning("matplotlib 미설치 — 차트 기능 비활성")


class BacktestReporter:
    """백테스트 결과 리포트 생성 (차트 + CSV)"""

    def plot_equity_curve(self, result: BacktestResult,
                          save_path: str | None = None) -> str | None:
        """
        자산 곡선 + 드로다운 차트 생성

        Args:
            result: 백테스트 결과
            save_path: 저장 경로 (None이면 자동 생성)

        Returns:
            저장된 파일 경로 또는 None
        """
        if not MPL_AVAILABLE:
            logger.warning("matplotlib 없음 — 차트 생성 불가")
            return None

        ec = result.equity_curve
        if ec is None or ec.empty:
            return None

        # 드로다운 계산
        cummax = ec.cummax()
        dd = (ec - cummax) / cummax

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8),
                                        gridspec_kw={"height_ratios": [3, 1]},
                                        sharex=True)
        fig.suptitle(f"{result.strategy_name} Backtest", fontsize=14, fontweight="bold")

        # 상단: Equity Curve
        ax1.plot(ec.index, ec.values, color="#2196F3", linewidth=1.5, label="Portfolio")
        ax1.set_ylabel("Equity")
        ax1.legend(loc="upper left")
        ax1.grid(True, alpha=0.3)
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(
            lambda x, _: f"{x:,.0f}"
        ))

        # 하단: Drawdown
        ax2.fill_between(dd.index, dd.values * 100, 0,
                         color="#F44336", alpha=0.3)
        ax2.plot(dd.index, dd.values * 100, color="#F44336", linewidth=0.8)
        ax2.set_ylabel("Drawdown (%)")
        ax2.set_xlabel("Date")
        ax2.grid(True, alpha=0.3)

        # X축 포맷
        ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax2.xaxis.set_major_locator(mdates.YearLocator())
        plt.xticks(rotation=45)

        plt.tight_layout()

        # 저장
        if save_path is None:
            save_path = f"backtest_{result.strategy_name.lower().replace(' ', '_')}_equity.png"

        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        logger.info(f"차트 저장: {save_path}")
        return save_path

    def plot_monthly_returns(self, result: BacktestResult,
                             save_path: str | None = None) -> str | None:
        """월별 수익률 히트맵"""
        if not MPL_AVAILABLE:
            return None

        ec = result.equity_curve
        if ec is None or len(ec) < 2:
            return None

        # 월별 수익률 계산
        monthly = ec.resample("ME").last()
        monthly_ret = monthly.pct_change().dropna()

        if monthly_ret.empty:
            return None

        df = pd.DataFrame({
            "year": monthly_ret.index.year,
            "month": monthly_ret.index.month,
            "return": monthly_ret.values * 100,
        })
        pivot = df.pivot_table(index="year", columns="month", values="return", aggfunc="first")

        fig, ax = plt.subplots(figsize=(14, max(3, len(pivot) * 0.6)))
        fig.suptitle(f"{result.strategy_name} — Monthly Returns (%)",
                     fontsize=13, fontweight="bold")

        # 히트맵
        cmap = plt.cm.RdYlGn
        data = pivot.values
        im = ax.imshow(data, cmap=cmap, aspect="auto",
                       vmin=-10, vmax=10)

        # 라벨
        ax.set_xticks(range(len(pivot.columns)))
        ax.set_xticklabels([f"{m}월" for m in pivot.columns])
        ax.set_yticks(range(len(pivot)))
        ax.set_yticklabels(pivot.index)

        # 셀 값 표시
        for i in range(len(pivot)):
            for j in range(len(pivot.columns)):
                val = data[i, j]
                if not np.isnan(val):
                    color = "white" if abs(val) > 5 else "black"
                    ax.text(j, i, f"{val:.1f}", ha="center", va="center",
                            fontsize=8, color=color)

        plt.colorbar(im, ax=ax, label="Return (%)", shrink=0.8)
        plt.tight_layout()

        if save_path is None:
            save_path = f"backtest_{result.strategy_name.lower().replace(' ', '_')}_monthly.png"

        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        logger.info(f"월별 수익률 차트 저장: {save_path}")
        return save_path

    def export_trades_csv(self, result: BacktestResult,
                          path: str | None = None) -> str:
        """거래 내역 CSV 내보내기"""
        if path is None:
            path = f"backtest_{result.strategy_name.lower().replace(' ', '_')}_trades.csv"

        records = []
        for t in result.trades:
            records.append({
                "date": t.date,
                "strategy": t.strategy,
                "code": t.code,
                "market": t.market,
                "side": t.side,
                "quantity": t.quantity,
                "price": round(t.price, 2),
                "commission": round(t.commission, 2),
                "pnl": round(t.pnl, 2),
                "reason": t.reason,
            })

        df = pd.DataFrame(records)
        df.to_csv(path, index=False, encoding="utf-8-sig")
        logger.info(f"거래 내역 저장: {path} ({len(records)}건)")
        return path
