from __future__ import annotations

"""Pydantic 모델 — 요청/응답 스키마"""

from pydantic import BaseModel


class BacktestRequest(BaseModel):
    strategy: str
    start_date: str
    end_date: str
    initial_capital: int = 50_000_000
    commission_rate: float = 0.00015
    slippage_rate: float = 0.001
    pair_name: str | None = None


class ApiError(BaseModel):
    data: None = None
    error: str
