from __future__ import annotations

from fastapi import APIRouter, Depends

from pyapi.deps import verify_secret
from pyapi.schemas import BacktestRequest

router = APIRouter(prefix="/py/backtest", tags=["backtest"])


def _serialize_result(result, metrics: dict) -> dict:
    """BacktestResult + metrics dict → JSON-safe dict"""
    # equity_curve: pd.Series → {dates, values}
    equity = {}
    if result.equity_curve is not None and not result.equity_curve.empty:
        equity = {
            "dates": result.equity_curve.index.strftime("%Y-%m-%d").tolist(),
            "values": result.equity_curve.values.tolist(),
        }

    # monthly_returns
    monthly = {"index": [], "columns": [], "data": []}
    if hasattr(result, "monthly_returns") and result.monthly_returns is not None:
        monthly = {
            "index": result.monthly_returns.index.tolist(),
            "columns": result.monthly_returns.columns.tolist(),
            "data": result.monthly_returns.values.tolist(),
        }

    # trades
    trades = [
        {
            "date": t.date,
            "strategy": t.strategy,
            "code": t.code,
            "market": t.market,
            "side": t.side,
            "quantity": t.quantity,
            "price": t.price,
            "commission": t.commission,
            "pnl": t.pnl,
            "pnl_pct": t.pnl_pct,
            "holding_days": t.holding_days,
        }
        for t in result.trades
    ]

    pnl_values = [t.pnl for t in result.trades if t.pnl is not None and t.pnl != 0]

    return {
        "metrics": metrics,
        "equity_curve": equity,
        "monthly_returns": monthly,
        "trades": trades,
        "pnl_values": pnl_values,
    }


@router.post("/run")
def run_backtest(req: BacktestRequest, secret: None = Depends(verify_secret)):
    """백테스트 실행"""
    from dashboard.services.backtest_service import run_backtest

    try:
        result, metrics = run_backtest(
            strategy_name=req.strategy,
            initial_capital=req.initial_capital,
            start_date=req.start_date or None,
            end_date=req.end_date or None,
            commission_rate=req.commission_rate,
            slippage_rate=req.slippage_rate,
            pair_name=req.pair_name,
        )
        return {"data": _serialize_result(result, metrics), "error": None}
    except Exception as e:
        return {"data": None, "error": str(e)}


@router.post("/run-per-pair")
def run_backtest_per_pair(req: BacktestRequest, secret: None = Depends(verify_secret)):
    """페어별 백테스트 실행"""
    from dashboard.services.backtest_service import run_backtest_per_pair

    try:
        results = run_backtest_per_pair(
            strategy_name=req.strategy,
            initial_capital=req.initial_capital,
            start_date=req.start_date or None,
            end_date=req.end_date or None,
            commission_rate=req.commission_rate,
            slippage_rate=req.slippage_rate,
        )
        data = {}
        for pair_name, (result, metrics) in results.items():
            data[pair_name] = _serialize_result(result, metrics)
        return {"data": data, "error": None}
    except Exception as e:
        return {"data": None, "error": str(e)}


@router.get("/pairs/{strategy}")
def get_pairs(strategy: str, secret: None = Depends(verify_secret)):
    """전략의 페어 목록 조회"""
    from dashboard.services.backtest_service import get_pair_names

    try:
        names = get_pair_names(strategy)
        return {"data": names, "error": None}
    except Exception as e:
        return {"data": None, "error": str(e)}
