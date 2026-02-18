from __future__ import annotations

import pytest
from sqlalchemy import create_engine

from src.core.portfolio_tracker import PortfolioTracker


@pytest.fixture
def tracker():
    """In-memory SQLite PortfolioTracker"""
    engine = create_engine("sqlite:///:memory:")
    t = PortfolioTracker(engine=engine)
    t.set_initial_capital(10_000_000)
    return t
