from __future__ import annotations

"""UniverseManager 단위 테스트 — DB 캐시 CRUD + fallback 로직"""

import pytest
from sqlalchemy import create_engine

from src.core.universe import UniverseManager


@pytest.fixture
def mgr():
    """In-memory SQLite UniverseManager"""
    engine = create_engine("sqlite:///:memory:")
    return UniverseManager(engine=engine)


class TestUniverseCache:
    """DB 캐시 저장/조회/상태"""

    def test_empty_cache(self, mgr):
        """빈 캐시 조회 시 빈 리스트"""
        assert mgr.load_from_cache("sp500") == []

    def test_save_and_load(self, mgr):
        """캐시 저장 후 조회"""
        stocks = [
            {"ticker": "AAPL", "name": "Apple", "exchange": "NAS",
             "sector": "Tech", "market_cap": 3e12, "avg_volume": 5e7, "last_price": 190},
            {"ticker": "MSFT", "name": "Microsoft", "exchange": "NAS",
             "sector": "Tech", "market_cap": 2.8e12, "avg_volume": 3e7, "last_price": 420},
        ]
        mgr._save_to_cache(stocks, "sp500")
        cached = mgr.load_from_cache("sp500")
        assert len(cached) == 2
        codes = {s["code"] for s in cached}
        assert codes == {"AAPL", "MSFT"}
        assert all(s["market"] == "US" for s in cached)

    def test_save_overwrites(self, mgr):
        """동일 source 재저장 시 이전 데이터 교체"""
        mgr._save_to_cache([{"ticker": "AAPL", "name": "Apple", "exchange": "NAS"}], "sp500")
        mgr._save_to_cache([{"ticker": "MSFT", "name": "Microsoft", "exchange": "NAS"}], "sp500")
        cached = mgr.load_from_cache("sp500")
        assert len(cached) == 1
        assert cached[0]["code"] == "MSFT"

    def test_status_empty(self, mgr):
        """빈 상태 조회"""
        status = mgr.get_status()
        assert status["stock_count"] == 0
        assert status["last_refresh"] is None
        assert status["cache_age_days"] is None

    def test_status_after_save(self, mgr):
        """저장 후 상태 조회"""
        mgr._save_to_cache([{"ticker": "AAPL", "name": "Apple", "exchange": "NAS"}], "sp500")
        status = mgr.get_status()
        assert status["stock_count"] == 1
        assert status["last_refresh"] is not None
        assert status["cache_age_days"] == 0


class TestGetStocks:
    """get_stocks() fallback 체인"""

    def test_manual_source(self, mgr):
        """source=manual → manual_codes 그대로 반환"""
        config = {
            "source": "manual",
            "manual_codes": [{"code": "AAPL", "market": "US", "exchange": "NAS"}],
        }
        result = mgr.get_stocks(config)
        assert len(result) == 1
        assert result[0]["code"] == "AAPL"

    def test_sp500_no_cache_falls_back_to_manual(self, mgr):
        """sp500 source + 캐시 없음 + auto_refresh=False → manual_codes fallback"""
        config = {
            "source": "sp500",
            "auto_refresh": False,
            "manual_codes": [{"code": "MSFT", "market": "US", "exchange": "NAS"}],
        }
        result = mgr.get_stocks(config)
        assert len(result) == 1
        assert result[0]["code"] == "MSFT"

    def test_sp500_uses_fresh_cache(self, mgr):
        """sp500 source + fresh 캐시 → 캐시에서 반환"""
        mgr._save_to_cache(
            [{"ticker": "GOOGL", "name": "Alphabet", "exchange": "NAS"}],
            "sp500",
        )
        config = {
            "source": "sp500",
            "refresh_interval_days": 7,
            "auto_refresh": False,
            "manual_codes": [{"code": "MSFT", "market": "US"}],
        }
        result = mgr.get_stocks(config)
        assert len(result) == 1
        assert result[0]["code"] == "GOOGL"

    def test_empty_config_returns_empty(self, mgr):
        """설정 없으면 빈 리스트"""
        assert mgr.get_stocks({}) == []
        assert mgr.get_stocks(None) == []


class TestCacheFreshness:
    """캐시 TTL 체크"""

    def test_no_meta_not_fresh(self, mgr):
        """메타 없으면 fresh 아님"""
        assert mgr._is_cache_fresh(7) is False

    def test_just_saved_is_fresh(self, mgr):
        """방금 저장하면 fresh"""
        mgr._save_to_cache([{"ticker": "X", "name": "X", "exchange": "NAS"}], "sp500")
        assert mgr._is_cache_fresh(7) is True

    def test_zero_interval_not_fresh(self, mgr):
        """interval=0이면 항상 not fresh"""
        mgr._save_to_cache([{"ticker": "X", "name": "X", "exchange": "NAS"}], "sp500")
        assert mgr._is_cache_fresh(0) is False
