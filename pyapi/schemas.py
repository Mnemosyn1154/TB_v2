from __future__ import annotations

"""Pydantic 모델 — 요청/응답 스키마"""

from typing import Literal, Optional

from pydantic import BaseModel


class ModeRequest(BaseModel):
    mode: Literal["simulation", "paper", "live"]
    confirm: bool = False  # required for "live"


class UniversePreviewRequest(BaseModel):
    min_price: float = 10
    min_avg_daily_volume: float = 10_000_000
    min_market_cap: float = 5_000_000_000


class StrategyOverrides(BaseModel):
    top_n: Optional[int] = None
    rebalance_months: Optional[int] = None
    lookback_days: Optional[int] = None
    momentum_days: Optional[int] = None
    volatility_days: Optional[int] = None
    weight_value: Optional[float] = None
    weight_quality: Optional[float] = None
    weight_momentum: Optional[float] = None
    absolute_momentum_filter: Optional[bool] = None
    abs_mom_threshold: Optional[float] = None


class BacktestRequest(BaseModel):
    strategy: str
    start_date: str
    end_date: str
    initial_capital: int = 50_000_000
    commission_rate: float = 0.00015
    slippage_rate: float = 0.001
    pair_name: Optional[str] = None
    universe_codes: Optional[list[dict]] = None
    strategy_overrides: Optional[StrategyOverrides] = None


class ApiError(BaseModel):
    data: None = None
    error: str
