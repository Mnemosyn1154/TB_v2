from __future__ import annotations

import json
import math

from fastapi import APIRouter, Depends
from starlette.responses import Response

from pyapi.deps import verify_secret
from pyapi.schemas import BacktestRequest

router = APIRouter(prefix="/py/backtest", tags=["backtest"])


class _SafeEncoder(json.JSONEncoder):
    """inf/NaN → null, numpy/pandas 타입 → native"""
    def default(self, o):
        import numpy as np
        import pandas as pd
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            v = float(o)
            return None if math.isnan(v) or math.isinf(v) else v
        if isinstance(o, np.ndarray):
            return self._sanitize(o.tolist())
        if isinstance(o, pd.DataFrame):
            return self._sanitize(o.to_dict(orient="list"))
        if isinstance(o, pd.Series):
            return self._sanitize(o.tolist())
        return super().default(o)

    def encode(self, o):
        return super().encode(self._sanitize(o))

    def _sanitize(self, o):
        if isinstance(o, float):
            return None if math.isnan(o) or math.isinf(o) else o
        if isinstance(o, dict):
            return {k: self._sanitize(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [self._sanitize(v) for v in o]
        return o


def _json_response(data: dict) -> Response:
    """inf/NaN을 null로 치환하는 JSON 응답"""
    body = json.dumps(data, cls=_SafeEncoder, ensure_ascii=False)
    return Response(content=body, media_type="application/json")


def _to_native(obj):
    """numpy/pandas 타입 → Python 네이티브 타입으로 재귀 변환 (inf/NaN → None)"""
    import math
    import numpy as np

    if isinstance(obj, dict):
        return {k: _to_native(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_native(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        v = float(obj)
        return None if math.isnan(v) or math.isinf(v) else v
    if isinstance(obj, float):
        return None if math.isnan(obj) or math.isinf(obj) else obj
    if isinstance(obj, np.ndarray):
        return _to_native(obj.tolist())
    return obj


def _serialize_result(result, metrics: dict) -> dict:
    """BacktestResult + metrics dict → JSON-safe dict"""
    metrics = _to_native(metrics)
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

    return _to_native({
        "metrics": metrics,
        "equity_curve": equity,
        "monthly_returns": monthly,
        "trades": trades,
        "pnl_values": pnl_values,
    })


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
        return _json_response({"data": _serialize_result(result, metrics), "error": None})
    except Exception as e:
        return _json_response({"data": None, "error": str(e)})


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
        return _json_response({"data": data, "error": None})
    except Exception as e:
        return _json_response({"data": None, "error": str(e)})


@router.get("/pairs/{strategy}")
def get_pairs(strategy: str, secret: None = Depends(verify_secret)):
    """전략의 페어 목록 조회"""
    from dashboard.services.backtest_service import get_pair_names

    try:
        names = get_pair_names(strategy)
        return {"data": names, "error": None}
    except Exception as e:
        return {"data": None, "error": str(e)}
