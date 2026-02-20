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


class BacktestRequest(BaseModel):
    strategy: str
    start_date: str
    end_date: str
    initial_capital: int = 50_000_000
    commission_rate: float = 0.00015
    slippage_rate: float = 0.001
    pair_name: Optional[str] = None
    universe_codes: Optional[list[dict]] = None


class ApiError(BaseModel):
    data: None = None
    error: str
