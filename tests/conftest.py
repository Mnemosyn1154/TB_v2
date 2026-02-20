from __future__ import annotations

import pytest
from sqlalchemy import create_engine

from src.core.portfolio_tracker import PortfolioTracker


# Fixed FX rate for deterministic tests
_TEST_FX_RATE = 1350.0


def _mock_get_fx_rate(market: str) -> float:
    if market == "US":
        return _TEST_FX_RATE
    return 1.0


@pytest.fixture(autouse=True)
def _mock_fx(monkeypatch):
    """Patch FX rate globally so all tests use a deterministic rate."""
    monkeypatch.setattr("src.core.fx.get_fx_rate", _mock_get_fx_rate)
    monkeypatch.setattr("src.core.fx.get_usd_krw", lambda: _TEST_FX_RATE)


@pytest.fixture
def tracker():
    """In-memory SQLite PortfolioTracker"""
    engine = create_engine("sqlite:///:memory:")
    t = PortfolioTracker(engine=engine)
    t.set_initial_capital(10_000_000)
    return t


@pytest.fixture
def fx_rate():
    """The fixed FX rate used in tests (for computing expected values)."""
    return _TEST_FX_RATE
