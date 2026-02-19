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


def _build_name_map(strategy) -> dict[str, str]:
    """전략 설정에서 종목코드→이름 매핑 구축"""
    from src.core.config import get_config

    name_map: dict[str, str] = {}
    config = get_config()
    cfg = config.get("strategies", {}).get(strategy.config_key, {})

    # universe_codes (quant_factor, volatility_breakout)
    for item in cfg.get("universe_codes", []):
        if isinstance(item, dict) and "code" in item and "name" in item:
            name_map[str(item["code"])] = item["name"]

    # sectors (sector_rotation)
    for item in cfg.get("sectors", []):
        if isinstance(item, dict) and "code" in item and "name" in item:
            name_map[str(item["code"])] = item["name"]

    # pairs (stat_arb) — use pair name as label for stock codes
    for pair in cfg.get("pairs", []):
        if isinstance(pair, dict) and "name" in pair:
            pair_name = pair["name"]
            for key in ("stock_a", "stock_b"):
                code = pair.get(key)
                if code:
                    name_map.setdefault(str(code), pair_name)
            hedge = pair.get("hedge_etf")
            if hedge:
                name_map.setdefault(str(hedge), f"{pair_name} hedge")

    # dual_momentum ETFs
    for key, label in [
        ("kr_etf", "KR ETF"), ("us_etf", "US ETF"),
        ("safe_kr_etf", "Safe KR"), ("safe_us_etf", "Safe US"),
        ("safe_asset", "Safe Asset"),
    ]:
        code = cfg.get(key)
        if code:
            name_map.setdefault(str(code), label)

    return name_map


def _serialize_result(result, metrics: dict, name_map: dict[str, str] | None = None) -> dict:
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
    nm = name_map or {}
    trades = [
        {
            "date": t.date,
            "strategy": t.strategy,
            "code": t.code,
            "name": nm.get(t.code, ""),
            "market": t.market,
            "side": t.side,
            "quantity": t.quantity,
            "price": t.price,
            "amount": t.quantity * t.price,
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


def _build_summary_logs(req: "BacktestRequest", result, metrics: dict, strategy) -> list[str]:
    """백테스트 결과를 사람이 읽기 쉬운 요약 메시지로 변환"""
    logs: list[str] = []
    data_source = metrics.get("data_source", "")
    strategy_type = getattr(strategy, "name", req.strategy)

    # 1. 데이터 수집
    codes = strategy.required_codes()
    logs.append(f"📂 데이터 수집 완료 — {len(codes)}개 종목, 소스: {data_source}")

    # 2. 전략별 상세 로그
    if strategy_type == "StatArb":
        _logs_stat_arb(logs, strategy)
    elif strategy_type == "DualMomentum":
        _logs_dual_momentum(logs, strategy)
    elif strategy_type == "QuantFactor":
        _logs_quant_factor(logs, strategy)

    # 3. 거래 결과 요약
    total = metrics.get("total_trades", 0)
    if total > 0:
        win_rate = metrics.get("win_rate", 0) or 0
        logs.append(f"📈 총 {total}건 거래 발생 (승률 {win_rate * 100:.1f}%)")
    else:
        logs.append("⚠️ 거래가 발생하지 않았습니다")
        # 거래 0건 원인 힌트
        if strategy_type == "StatArb":
            logs.append("   → 공적분 관계가 성립하지 않거나 Z-Score가 진입 조건에 도달하지 못했을 수 있습니다")
        elif strategy_type == "DualMomentum":
            logs.append("   → 리밸런싱 조건이 충족되지 않았을 수 있습니다")
        elif strategy_type == "QuantFactor":
            logs.append("   → 팩터 스코어 계산에 필요한 데이터가 부족할 수 있습니다")

    total_return = metrics.get("total_return", 0) or 0
    logs.append(f"💰 최종 수익률: {total_return * 100:+.2f}%")

    return logs


def _logs_stat_arb(logs: list[str], strategy) -> None:
    """StatArb 전략 요약 로그"""
    for pair in strategy.pairs:
        state = strategy.pair_states.get(pair.name)
        if not state:
            continue
        if state.is_cointegrated:
            logs.append(
                f"✅ {pair.name} ({pair.stock_a}/{pair.stock_b}): "
                f"공적분 발견 (p={state.p_value:.4f}), "
                f"헤지비율 β={state.beta:.4f}, Z-Score={state.current_z:.2f}"
            )
        else:
            logs.append(
                f"❌ {pair.name} ({pair.stock_a}/{pair.stock_b}): "
                f"공적분 미발견 (p={state.p_value:.4f}) — 이 페어는 거래 불가"
            )


def _logs_dual_momentum(logs: list[str], strategy) -> None:
    """DualMomentum 전략 요약 로그"""
    logs.append(
        f"📊 모멘텀 비교: KR {strategy.kr_return * 100:+.1f}% vs US {strategy.us_return * 100:+.1f}% "
        f"(무위험수익률 {strategy.risk_free_rate * 100:.1f}%)"
    )
    alloc = strategy.current_allocation
    alloc_label = {"KR": "한국 ETF", "US": "미국 ETF", "SAFE": "안전자산 (채권)", "NONE": "미배분"}
    logs.append(f"🎯 최종 배분: {alloc_label.get(alloc, alloc)}")


def _logs_quant_factor(logs: list[str], strategy) -> None:
    """QuantFactor 전략 요약 로그"""
    scored = len(strategy.last_scores)
    total = len(strategy.universe_codes)
    logs.append(f"📊 {total}개 유니버스 중 {scored}개 종목 스코어링 완료")
    if scored > 0:
        ranked = sorted(strategy.last_scores.items(), key=lambda x: x[1]["composite"], reverse=True)
        top = ranked[:min(5, len(ranked))]
        names = [code for code, _ in top]
        logs.append(f"🏆 상위 종목: {', '.join(names)}")
    holdings = len(strategy.current_holdings)
    logs.append(f"📦 현재 보유: {holdings}종목")


@router.post("/run")
def run_backtest(req: BacktestRequest, secret: None = Depends(verify_secret)):
    """백테스트 실행"""
    from src.backtest.runner import BacktestRunner

    try:
        runner = BacktestRunner()
        bt_config = runner.config.get("backtest", {})
        commission = req.commission_rate or bt_config.get("commission_rate", 0.00015)
        slippage = req.slippage_rate or bt_config.get("slippage_rate", 0.001)

        # 전략 인스턴스 직접 생성 (로그용 상태 접근)
        strategy = runner._create_strategy(req.strategy)
        if req.pair_name:
            available = strategy.get_pair_names()
            if available and req.pair_name in available:
                strategy.filter_pairs([req.pair_name])

        from src.backtest.engine import BacktestEngine
        from src.backtest.analyzer import PerformanceAnalyzer

        price_data, data_source = runner._load_data(
            strategy, req.start_date or "", req.end_date or ""
        )
        if not price_data:
            return _json_response({"data": None, "error": "데이터가 없습니다. 데이터 수집을 먼저 실행하세요."})

        engine = BacktestEngine(
            strategy=strategy,
            initial_capital=req.initial_capital,
            commission_rate=commission,
            slippage_rate=slippage,
        )
        result = engine.run(price_data, req.start_date or "", req.end_date or "")
        analyzer = PerformanceAnalyzer(result)
        metrics = analyzer.summary()
        metrics["data_source"] = data_source

        name_map = _build_name_map(strategy)
        data = _serialize_result(result, metrics, name_map)
        data["logs"] = _build_summary_logs(req, result, metrics, strategy)
        return _json_response({"data": data, "error": None})
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
