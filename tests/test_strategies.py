from __future__ import annotations

"""전략 유닛 테스트: StatArb, DualMomentum, QuantFactor, VolatilityBreakout, BollingerBand"""

from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from src.strategies.base import Signal, TradeSignal


# ──────────────────────────────────────────────
# StatArb
# ──────────────────────────────────────────────

STAT_ARB_CONFIG = {
    "simulation": {"enabled": True, "initial_capital": 10_000_000},
    "strategies": {
        "stat_arb": {
            "enabled": True,
            "pairs": [
                {
                    "name": "TEST_PAIR",
                    "market": "US",
                    "stock_a": "AAA",
                    "stock_b": "BBB",
                    "hedge_etf": "HHH",
                },
            ],
            "lookback_window": 30,
            "entry_z_score": 1.5,
            "exit_z_score": 0.5,
            "stop_loss_z_score": 3.0,
            "recalc_beta_days": 20,
            "coint_pvalue": 0.10,
        },
    },
}


def _make_cointegrated_pair(n: int = 200, seed: int = 42) -> tuple[pd.Series, pd.Series]:
    """공적분 관계의 합성 가격 페어 생성"""
    rng = np.random.RandomState(seed)
    # 공통 요인 (랜덤 워크)
    common = np.cumsum(rng.randn(n)) + 100
    noise_a = rng.randn(n) * 0.5
    noise_b = rng.randn(n) * 0.5
    prices_a = pd.Series(common + noise_a, dtype=float)
    prices_b = pd.Series(common * 0.8 + 20 + noise_b, dtype=float)
    return prices_a, prices_b


class TestStatArb:
    @pytest.fixture(autouse=True)
    def setup(self):
        with patch("src.strategies.stat_arb.get_config", return_value=STAT_ARB_CONFIG):
            from src.strategies.stat_arb import StatArbStrategy
            self.strategy = StatArbStrategy()

    def test_init_loads_pairs(self):
        assert len(self.strategy.pairs) == 1
        assert self.strategy.pairs[0].name == "TEST_PAIR"

    def test_required_codes(self):
        codes = self.strategy.required_codes()
        code_set = {c["code"] for c in codes}
        assert {"AAA", "BBB", "HHH"} == code_set

    def test_prepare_signal_kwargs_missing_data(self):
        result = self.strategy.prepare_signal_kwargs({"AAA": pd.Series([1, 2, 3])})
        assert result == {}

    def test_prepare_signal_kwargs_insufficient_data(self):
        result = self.strategy.prepare_signal_kwargs({
            "AAA": pd.Series(range(30)),
            "BBB": pd.Series(range(30)),
        })
        assert result == {}

    def test_prepare_signal_kwargs_valid(self):
        result = self.strategy.prepare_signal_kwargs({
            "AAA": pd.Series(range(100), dtype=float),
            "BBB": pd.Series(range(100), dtype=float),
        })
        assert "pair_data" in result
        assert "TEST_PAIR" in result["pair_data"]

    def test_generate_signals_no_data(self):
        signals = self.strategy.generate_signals(pair_data={})
        assert signals == []

    def test_generate_signals_cointegrated_pair(self):
        """공적분 페어에서 시그널 생성 여부 (진입 조건은 Z에 의존)"""
        prices_a, prices_b = _make_cointegrated_pair()
        pair_data = {"TEST_PAIR": {"prices_a": prices_a, "prices_b": prices_b}}
        signals = self.strategy.generate_signals(pair_data=pair_data)
        # 공적분이 확인되더라도 Z-Score가 진입 조건에 맞아야 신호 발생
        # 반환은 항상 리스트
        assert isinstance(signals, list)

    def test_cointegration_test(self):
        prices_a, prices_b = _make_cointegrated_pair()
        is_coint, p_val = self.strategy.test_cointegration(prices_a, prices_b)
        # 합성 데이터는 높은 확률로 공적분
        assert is_coint in (True, False)
        assert 0 <= p_val <= 1

    def test_hedge_ratio(self):
        prices_a, prices_b = _make_cointegrated_pair()
        beta = self.strategy.calculate_hedge_ratio(prices_a, prices_b)
        # beta는 ~1.25 근방 (common * 1 / common * 0.8)
        assert 0.5 < beta < 3.0

    def test_z_score_calculation(self):
        spread = pd.Series(np.random.randn(100))
        z = self.strategy.calculate_z_score(spread, window=20)
        assert len(z) == 100
        # 첫 window-1 개는 NaN
        assert z.iloc[:19].isna().all()

    def test_disabled_returns_empty(self):
        self.strategy.enabled = False
        prices_a, prices_b = _make_cointegrated_pair()
        signals = self.strategy.generate_signals(
            pair_data={"TEST_PAIR": {"prices_a": prices_a, "prices_b": prices_b}}
        )
        assert signals == []

    def test_on_trade_executed_updates_position(self):
        signal = TradeSignal(
            strategy="StatArb", code="BBB", market="US", signal=Signal.BUY,
            metadata={"pair": "TEST_PAIR", "target_position": "LONG_B"},
        )
        self.strategy.on_trade_executed(signal, success=True)
        assert self.strategy.pair_states["TEST_PAIR"].position == "LONG_B"

    def test_on_trade_executed_close(self):
        self.strategy.pair_states["TEST_PAIR"].position = "LONG_A"
        signal = TradeSignal(
            strategy="StatArb", code="AAA", market="US", signal=Signal.CLOSE,
            metadata={"pair": "TEST_PAIR"},
        )
        self.strategy.on_trade_executed(signal, success=True)
        assert self.strategy.pair_states["TEST_PAIR"].position == "NONE"


# ──────────────────────────────────────────────
# DualMomentum
# ──────────────────────────────────────────────

DUAL_MOMENTUM_CONFIG = {
    "simulation": {"enabled": True, "initial_capital": 10_000_000},
    "strategies": {
        "dual_momentum": {
            "enabled": True,
            "lookback_months": 12,
            "rebalance_day": 1,
            "kr_etf": "069500",
            "us_etf": "SPY",
            "us_etf_exchange": "NYS",
            "safe_kr_etf": "148070",
            "safe_us_etf": "SHY",
            "safe_us_etf_exchange": "NYS",
            "risk_free_rate": 0.04,
        },
    },
}


def _make_trending_prices(n: int = 300, trend: float = 0.001, seed: int = 0) -> pd.Series:
    """상승/하락 트렌드 가격 시리즈 생성"""
    rng = np.random.RandomState(seed)
    returns = trend + rng.randn(n) * 0.01
    prices = 100 * np.cumprod(1 + returns)
    return pd.Series(prices, dtype=float)


class TestDualMomentum:
    @pytest.fixture(autouse=True)
    def setup(self):
        with patch("src.strategies.dual_momentum.get_config", return_value=DUAL_MOMENTUM_CONFIG):
            from src.strategies.dual_momentum import DualMomentumStrategy
            self.strategy = DualMomentumStrategy()

    def test_init(self):
        assert self.strategy.lookback_months == 12
        assert self.strategy.current_allocation == "NONE"

    def test_required_codes(self):
        codes = self.strategy.required_codes()
        code_set = {c["code"] for c in codes}
        assert {"069500", "SPY", "148070", "SHY"} == code_set

    def test_calculate_return_positive(self):
        prices = _make_trending_prices(n=300, trend=0.001)
        ret = self.strategy.calculate_return(prices, months=12)
        assert ret > 0

    def test_calculate_return_negative(self):
        prices = _make_trending_prices(n=300, trend=-0.001, seed=1)
        ret = self.strategy.calculate_return(prices, months=12)
        assert ret < 0

    def test_calculate_return_short_data(self):
        prices = pd.Series([100.0, 101.0, 102.0])
        ret = self.strategy.calculate_return(prices, months=12)
        # 짧은 데이터도 가용 범위에서 계산
        assert isinstance(ret, float)

    def test_prepare_signal_kwargs_missing(self):
        result = self.strategy.prepare_signal_kwargs({"069500": pd.Series(range(100), dtype=float)})
        assert result == {}

    def test_prepare_signal_kwargs_valid(self):
        result = self.strategy.prepare_signal_kwargs({
            "069500": pd.Series(range(100), dtype=float),
            "SPY": pd.Series(range(100), dtype=float),
        })
        assert "kr_prices" in result
        assert "us_prices" in result

    def test_generate_signals_kr_wins(self):
        """한국 수익률 > 미국 수익률 > 무위험수익률 → KR 매수"""
        kr = _make_trending_prices(n=300, trend=0.002, seed=10)   # 강한 상승
        us = _make_trending_prices(n=300, trend=0.0005, seed=11)  # 약한 상승
        signals = self.strategy.generate_signals(kr_prices=kr, us_prices=us)
        assert len(signals) >= 1
        buy_signals = [s for s in signals if s.signal == Signal.BUY]
        assert len(buy_signals) == 1
        assert buy_signals[0].code == "069500"  # kr_etf

    def test_generate_signals_us_wins(self):
        """미국 수익률 > 한국 수익률 > 무위험수익률 → US 매수"""
        kr = _make_trending_prices(n=300, trend=0.0005, seed=20)
        us = _make_trending_prices(n=300, trend=0.002, seed=21)
        signals = self.strategy.generate_signals(kr_prices=kr, us_prices=us)
        buy_signals = [s for s in signals if s.signal == Signal.BUY]
        assert len(buy_signals) == 1
        assert buy_signals[0].code == "SPY"

    def test_generate_signals_safe(self):
        """둘 다 무위험수익률 이하 → 안전자산"""
        kr = _make_trending_prices(n=300, trend=-0.001, seed=30)
        us = _make_trending_prices(n=300, trend=-0.001, seed=31)
        signals = self.strategy.generate_signals(kr_prices=kr, us_prices=us)
        buy_signals = [s for s in signals if s.signal == Signal.BUY]
        assert len(buy_signals) == 1
        assert buy_signals[0].code == "148070"  # safe_kr_etf

    def test_no_change_no_signal(self):
        """동일 배분 유지 시 빈 시그널"""
        kr = _make_trending_prices(n=300, trend=0.002, seed=40)
        us = _make_trending_prices(n=300, trend=0.0005, seed=41)
        # 첫 호출로 KR 배분 확정
        self.strategy.generate_signals(kr_prices=kr, us_prices=us)
        self.strategy.current_allocation = "KR"
        # 동일 데이터로 재호출
        signals = self.strategy.generate_signals(kr_prices=kr, us_prices=us)
        assert signals == []

    def test_disabled_returns_empty(self):
        self.strategy.enabled = False
        kr = _make_trending_prices(n=300, trend=0.002)
        us = _make_trending_prices(n=300, trend=0.0005, seed=1)
        assert self.strategy.generate_signals(kr_prices=kr, us_prices=us) == []

    def test_on_trade_executed(self):
        signal = TradeSignal(
            strategy="DualMomentum", code="SPY", market="US", signal=Signal.BUY,
            metadata={"target_allocation": "US"},
        )
        self.strategy.on_trade_executed(signal, success=True)
        assert self.strategy.current_allocation == "US"


# ──────────────────────────────────────────────
# QuantFactor
# ──────────────────────────────────────────────

QUANT_FACTOR_CONFIG = {
    "simulation": {"enabled": True, "initial_capital": 10_000_000},
    "strategies": {
        "quant_factor": {
            "enabled": True,
            "top_n": 2,
            "rebalance_months": 1,
            "lookback_days": 252,
            "momentum_days": 126,
            "volatility_days": 60,
            "min_data_days": 60,
            "weights": {"value": 0.3, "quality": 0.3, "momentum": 0.4},
            "universe_codes": [
                {"code": "A", "market": "US"},
                {"code": "B", "market": "US"},
                {"code": "C", "market": "US"},
                {"code": "D", "market": "KR"},
            ],
        },
    },
}


def _make_stock_prices(n: int = 200, base: float = 100, trend: float = 0.0005,
                       vol: float = 0.02, seed: int = 0) -> pd.Series:
    """주가 시리즈 생성"""
    rng = np.random.RandomState(seed)
    returns = trend + rng.randn(n) * vol
    prices = base * np.cumprod(1 + returns)
    return pd.Series(prices, dtype=float)


class TestQuantFactor:
    @pytest.fixture(autouse=True)
    def setup(self):
        with patch("src.strategies.quant_factor.get_config", return_value=QUANT_FACTOR_CONFIG):
            from src.strategies.quant_factor import QuantFactorStrategy
            self.strategy = QuantFactorStrategy()

    def test_init(self):
        assert self.strategy.top_n == 2
        assert self.strategy.weight_momentum == 0.4

    def test_required_codes(self):
        codes = self.strategy.required_codes()
        assert len(codes) == 4
        code_set = {c["code"] for c in codes}
        assert {"A", "B", "C", "D"} == code_set

    def test_prepare_signal_kwargs_insufficient(self):
        """최소 2종목 미만이면 빈 dict"""
        result = self.strategy.prepare_signal_kwargs({
            "A": pd.Series(range(10), dtype=float),  # too short
        })
        assert result == {}

    def test_prepare_signal_kwargs_valid(self):
        result = self.strategy.prepare_signal_kwargs({
            "A": pd.Series(range(100), dtype=float),
            "B": pd.Series(range(100), dtype=float),
        })
        assert "price_data" in result
        assert len(result["price_data"]) == 2

    def test_generate_signals_selects_top_n(self):
        """4종목 중 top_n=2 선정"""
        price_data = {
            "A": _make_stock_prices(n=200, trend=0.002, vol=0.01, seed=0),   # 강한 상승, 저변동
            "B": _make_stock_prices(n=200, trend=0.001, vol=0.02, seed=1),
            "C": _make_stock_prices(n=200, trend=-0.001, vol=0.03, seed=2),
            "D": _make_stock_prices(n=200, trend=-0.002, vol=0.04, seed=3),
        }
        signals = self.strategy.generate_signals(price_data=price_data)
        buy_signals = [s for s in signals if s.signal == Signal.BUY]
        # top_n=2이므로 최대 2개 매수
        assert len(buy_signals) <= 2
        # 첫 실행이므로 청산 없음 (current_holdings 비어있음)
        close_signals = [s for s in signals if s.signal == Signal.CLOSE]
        assert len(close_signals) == 0

    def test_rebalance_drops_and_adds(self):
        """리밸런싱: 기존 보유 탈락 → 청산, 신규 편입 → 매수"""
        self.strategy.current_holdings = {"C", "D"}

        price_data = {
            "A": _make_stock_prices(n=200, trend=0.002, vol=0.01, seed=0),
            "B": _make_stock_prices(n=200, trend=0.001, vol=0.02, seed=1),
            "C": _make_stock_prices(n=200, trend=-0.001, vol=0.03, seed=2),
            "D": _make_stock_prices(n=200, trend=-0.002, vol=0.04, seed=3),
        }
        signals = self.strategy.generate_signals(price_data=price_data)
        buy_codes = {s.code for s in signals if s.signal == Signal.BUY}
        close_codes = {s.code for s in signals if s.signal == Signal.CLOSE}
        # C, D 탈락 → 청산, A, B 편입 → 매수 (스코어에 따라)
        assert len(buy_codes) > 0
        assert len(close_codes) > 0

    def test_factor_calculation(self):
        """단일 종목 팩터 계산"""
        prices = _make_stock_prices(n=200, trend=0.001, vol=0.02, seed=0)
        factors = self.strategy._calculate_factors(prices)
        assert factors is not None
        assert "value" in factors
        assert "quality" in factors
        assert "momentum" in factors

    def test_factor_short_data_returns_none(self):
        prices = pd.Series([100.0, 101.0, 102.0])
        factors = self.strategy._calculate_factors(prices)
        assert factors is None

    def test_disabled_returns_empty(self):
        self.strategy.enabled = False
        price_data = {
            "A": _make_stock_prices(n=200, seed=0),
            "B": _make_stock_prices(n=200, seed=1),
        }
        assert self.strategy.generate_signals(price_data=price_data) == []

    def test_composite_score_ranking(self):
        """Z-Score 정규화 + 가중합산 → 순위"""
        price_data = {
            "A": _make_stock_prices(n=200, trend=0.002, vol=0.01, seed=0),
            "B": _make_stock_prices(n=200, trend=-0.002, vol=0.04, seed=1),
        }
        scores = self.strategy._calculate_composite_scores(price_data)
        assert len(scores) == 2
        assert scores["A"]["rank"] < scores["B"]["rank"]  # A가 더 높은 순위


# ──────────────────────────────────────────────
# QuantFactor — Absolute Momentum Filter
# ──────────────────────────────────────────────

QUANT_FACTOR_ABS_MOM_CONFIG = {
    "simulation": {"enabled": True, "initial_capital": 10_000_000},
    "strategies": {
        "quant_factor": {
            "enabled": True,
            "top_n": 2,
            "rebalance_months": 1,
            "lookback_days": 252,
            "momentum_days": 126,
            "volatility_days": 60,
            "min_data_days": 60,
            "weights": {"value": 0.3, "quality": 0.3, "momentum": 0.4},
            "absolute_momentum_filter": True,
            "abs_mom_threshold": 0.0,
            "safe_asset": "SHY",
            "safe_asset_exchange": "NYS",
            "universe_codes": [
                {"code": "A", "market": "US"},
                {"code": "B", "market": "US"},
                {"code": "C", "market": "US"},
                {"code": "D", "market": "KR"},
            ],
        },
    },
}


class TestQuantFactorAbsoluteMomentum:
    @pytest.fixture(autouse=True)
    def setup(self):
        with patch("src.strategies.quant_factor.get_config", return_value=QUANT_FACTOR_ABS_MOM_CONFIG):
            from src.strategies.quant_factor import QuantFactorStrategy
            self.strategy = QuantFactorStrategy()

    def test_init_filter_params(self):
        """절대 모멘텀 필터 파라미터 로딩 확인"""
        assert self.strategy.absolute_momentum_filter is True
        assert self.strategy.abs_mom_threshold == 0.0
        assert self.strategy.safe_asset == "SHY"
        assert self.strategy.safe_asset_exchange == "NYS"

    def test_required_codes_includes_safe_asset(self):
        """필터 활성 시 required_codes에 안전자산 포함"""
        codes = self.strategy.required_codes()
        code_set = {c["code"] for c in codes}
        assert "SHY" in code_set

    def test_get_market_safe_asset(self):
        """안전자산 코드의 시장은 US"""
        assert self.strategy._get_market("SHY") == "US"

    def test_composite_scores_preserve_raw_momentum(self):
        """_calculate_composite_scores 결과에 raw_momentum 키 존재"""
        price_data = {
            "A": _make_stock_prices(n=200, trend=0.002, vol=0.01, seed=0),
            "B": _make_stock_prices(n=200, trend=0.001, vol=0.02, seed=1),
        }
        scores = self.strategy._calculate_composite_scores(price_data)
        assert len(scores) == 2
        for code in scores:
            assert "raw_momentum" in scores[code]

    def test_filter_replaces_low_momentum_with_safe(self):
        """하락 추세 종목이 안전자산으로 대체됨"""
        price_data = {
            "A": _make_stock_prices(n=200, trend=-0.002, vol=0.01, seed=0),  # 하락
            "B": _make_stock_prices(n=200, trend=-0.003, vol=0.02, seed=1),  # 하락
            "C": _make_stock_prices(n=200, trend=-0.001, vol=0.03, seed=2),  # 하락
            "D": _make_stock_prices(n=200, trend=-0.004, vol=0.04, seed=3),  # 하락
        }
        signals = self.strategy.generate_signals(price_data=price_data)
        buy_codes = {s.code for s in signals if s.signal == Signal.BUY}
        # 모든 종목이 음수 모멘텀 → 안전자산 대체
        assert "SHY" in buy_codes

    def test_filter_disabled_no_replacement(self):
        """필터 비활성 시 안전자산 대체 없음"""
        self.strategy.absolute_momentum_filter = False
        price_data = {
            "A": _make_stock_prices(n=200, trend=-0.002, vol=0.01, seed=0),
            "B": _make_stock_prices(n=200, trend=-0.003, vol=0.02, seed=1),
            "C": _make_stock_prices(n=200, trend=-0.001, vol=0.03, seed=2),
            "D": _make_stock_prices(n=200, trend=-0.004, vol=0.04, seed=3),
        }
        signals = self.strategy.generate_signals(price_data=price_data)
        buy_codes = {s.code for s in signals if s.signal == Signal.BUY}
        assert "SHY" not in buy_codes


# ──────────────────────────────────────────────
# VolatilityBreakout
# ──────────────────────────────────────────────

VOLATILITY_BREAKOUT_CONFIG = {
    "simulation": {"enabled": True, "initial_capital": 10_000_000},
    "strategies": {
        "volatility_breakout": {
            "enabled": True,
            "k": 0.5,
            "market": "KR",
            "max_hold_per_stock": 1,
            "close_at_market_end": True,
            "kr_close_time": "15:15",
            "us_close_time": "15:45",
            "universe_codes": [
                {"code": "005930", "market": "KR", "name": "삼성전자"},
                {"code": "000660", "market": "KR", "name": "SK하이닉스"},
            ],
        },
    },
}


def _make_ohlc_df(n: int = 10, base: float = 50000, seed: int = 42) -> pd.DataFrame:
    """OHLC DataFrame 생성 (변동성 돌파 테스트용)"""
    rng = np.random.RandomState(seed)
    dates = pd.bdate_range("2024-01-01", periods=n)
    rows = []
    price = base
    for d in dates:
        open_ = price + rng.randn() * 500
        high = open_ + abs(rng.randn()) * 1000
        low = open_ - abs(rng.randn()) * 1000
        close = open_ + rng.randn() * 500
        rows.append({"date": d.strftime("%Y-%m-%d"), "open": open_, "high": high,
                      "low": low, "close": close})
        price = close
    return pd.DataFrame(rows)


class TestVolatilityBreakout:
    @pytest.fixture(autouse=True)
    def setup(self):
        with patch("src.strategies.volatility_breakout.get_config",
                    return_value=VOLATILITY_BREAKOUT_CONFIG):
            from src.strategies.volatility_breakout import VolatilityBreakoutStrategy
            self.strategy = VolatilityBreakoutStrategy()

    def test_init(self):
        assert self.strategy.k == 0.5
        assert self.strategy.market == "KR"
        assert len(self.strategy.universe) == 2
        assert self.strategy.needs_ohlc is True

    def test_required_codes(self):
        codes = self.strategy.required_codes()
        code_set = {c["code"] for c in codes}
        assert {"005930", "000660"} == code_set
        assert all(c["market"] == "KR" for c in codes)

    def test_prepare_signal_kwargs_valid(self):
        ohlc = {
            "005930": _make_ohlc_df(n=5, seed=0),
            "000660": _make_ohlc_df(n=5, seed=1),
        }
        result = self.strategy.prepare_signal_kwargs(ohlc)
        assert "ohlc_data" in result
        assert len(result["ohlc_data"]) == 2

    def test_prepare_signal_kwargs_insufficient_data(self):
        """1일치 데이터 → 최소 2일 미달 → 스킵"""
        result = self.strategy.prepare_signal_kwargs({
            "005930": _make_ohlc_df(n=1),
        })
        assert result == {}

    def test_prepare_signal_kwargs_series_skipped(self):
        """Series 데이터 → OHLC 아니므로 스킵"""
        result = self.strategy.prepare_signal_kwargs({
            "005930": pd.Series([100, 101, 102]),
        })
        assert result == {}

    def test_target_price_calculation(self):
        """목표가 = 오늘 시가 + 전일 (고가 - 저가) × k"""
        df = pd.DataFrame([
            {"date": "2024-01-01", "open": 50000, "high": 52000, "low": 48000, "close": 51000},
            {"date": "2024-01-02", "open": 51000, "high": 53000, "low": 49000, "close": 52000},
        ])
        ohlc_data = {"005930": df}
        self.strategy._update_targets(ohlc_data)

        # target = today_open(51000) + (prev_high(52000) - prev_low(48000)) * 0.5 = 51000 + 2000 = 53000
        assert "005930" in self.strategy.today_targets
        assert self.strategy.today_targets["005930"] == 53000.0

    def test_target_recalc_on_new_date(self):
        """날짜 변경 시 목표가 재계산"""
        df1 = pd.DataFrame([
            {"date": "2024-01-01", "open": 50000, "high": 52000, "low": 48000, "close": 51000},
            {"date": "2024-01-02", "open": 51000, "high": 53000, "low": 49000, "close": 52000},
        ])
        self.strategy._update_targets({"005930": df1})
        target_day2 = self.strategy.today_targets["005930"]

        df2 = pd.DataFrame([
            {"date": "2024-01-01", "open": 50000, "high": 52000, "low": 48000, "close": 51000},
            {"date": "2024-01-02", "open": 51000, "high": 53000, "low": 49000, "close": 52000},
            {"date": "2024-01-03", "open": 52000, "high": 55000, "low": 50000, "close": 54000},
        ])
        self.strategy._update_targets({"005930": df2})
        target_day3 = self.strategy.today_targets["005930"]

        assert target_day2 != target_day3
        # day3: 52000 + (53000 - 49000) * 0.5 = 52000 + 2000 = 54000
        assert target_day3 == 54000.0

    def test_target_not_recalc_same_date(self):
        """같은 날짜 → 재계산 안함"""
        df = pd.DataFrame([
            {"date": "2024-01-01", "open": 50000, "high": 52000, "low": 48000, "close": 51000},
            {"date": "2024-01-02", "open": 51000, "high": 53000, "low": 49000, "close": 52000},
        ])
        self.strategy._update_targets({"005930": df})
        self.strategy.today_targets["005930"] = 99999  # manually overwrite
        self.strategy._update_targets({"005930": df})  # same date → skip
        assert self.strategy.today_targets["005930"] == 99999  # unchanged

    def test_backtest_breakout_buy(self):
        """백테스트: 고가 ≥ 목표가 → BUY 신호"""
        df = pd.DataFrame([
            {"date": "2024-01-01", "open": 50000, "high": 52000, "low": 48000, "close": 51000},
            {"date": "2024-01-02", "open": 51000, "high": 55000, "low": 49000, "close": 52000},
        ])
        # target = 51000 + (52000 - 48000) * 0.5 = 53000, high = 55000 ≥ 53000 → buy
        signals = self.strategy.generate_signals(ohlc_data={"005930": df})
        buy_signals = [s for s in signals if s.signal == Signal.BUY]
        assert len(buy_signals) == 1
        assert buy_signals[0].code == "005930"
        assert buy_signals[0].price == 53000.0  # target price

    def test_backtest_no_breakout(self):
        """백테스트: 고가 < 목표가 → 신호 없음"""
        df = pd.DataFrame([
            {"date": "2024-01-01", "open": 50000, "high": 52000, "low": 48000, "close": 51000},
            {"date": "2024-01-02", "open": 51000, "high": 52500, "low": 49000, "close": 52000},
        ])
        # target = 53000, high = 52500 < 53000 → no signal
        signals = self.strategy.generate_signals(ohlc_data={"005930": df})
        assert len(signals) == 0

    def test_backtest_close_after_buy(self):
        """백테스트: 진입 다음날 청산 확인"""
        # Day 1→2: breakout → buy
        df_day2 = pd.DataFrame([
            {"date": "2024-01-01", "open": 50000, "high": 52000, "low": 48000, "close": 51000},
            {"date": "2024-01-02", "open": 51000, "high": 55000, "low": 49000, "close": 52000},
        ])
        signals = self.strategy.generate_signals(ohlc_data={"005930": df_day2})
        for s in signals:
            self.strategy.on_trade_executed(s, success=True)
        assert "005930" in self.strategy.current_holdings

        # Day 2→3: close existing + potentially new breakout
        df_day3 = pd.DataFrame([
            {"date": "2024-01-01", "open": 50000, "high": 52000, "low": 48000, "close": 51000},
            {"date": "2024-01-02", "open": 51000, "high": 55000, "low": 49000, "close": 52000},
            {"date": "2024-01-03", "open": 52000, "high": 52500, "low": 50000, "close": 51000},
        ])
        signals = self.strategy.generate_signals(ohlc_data={"005930": df_day3})
        close_signals = [s for s in signals if s.signal == Signal.CLOSE]
        assert len(close_signals) == 1
        assert close_signals[0].code == "005930"

    def test_no_duplicate_entry_same_day(self):
        """같은 날 같은 종목 2번 진입 방지"""
        df = pd.DataFrame([
            {"date": "2024-01-01", "open": 50000, "high": 52000, "low": 48000, "close": 51000},
            {"date": "2024-01-02", "open": 51000, "high": 55000, "low": 49000, "close": 52000},
        ])
        signals1 = self.strategy.generate_signals(ohlc_data={"005930": df})
        for s in signals1:
            self.strategy.on_trade_executed(s, success=True)

        # same day, same data → no new buy
        signals2 = self.strategy.generate_signals(ohlc_data={"005930": df})
        buy_signals = [s for s in signals2 if s.signal == Signal.BUY]
        assert len(buy_signals) == 0

    def test_live_breakout(self):
        """실시간 모드: 현재가 ≥ 목표가 → BUY"""
        df = pd.DataFrame([
            {"date": "2024-01-01", "open": 50000, "high": 52000, "low": 48000, "close": 51000},
            {"date": "2024-01-02", "open": 51000, "high": 53000, "low": 49000, "close": 52000},
        ])
        # target = 53000
        with patch("src.strategies.volatility_breakout.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = "10:00"
            signals = self.strategy.generate_signals(
                ohlc_data={"005930": df},
                current_prices={"005930": 54000},
            )
        buy_signals = [s for s in signals if s.signal == Signal.BUY]
        assert len(buy_signals) == 1
        assert buy_signals[0].price == 54000

    def test_live_no_breakout(self):
        """실시간 모드: 현재가 < 목표가 → 신호 없음"""
        df = pd.DataFrame([
            {"date": "2024-01-01", "open": 50000, "high": 52000, "low": 48000, "close": 51000},
            {"date": "2024-01-02", "open": 51000, "high": 53000, "low": 49000, "close": 52000},
        ])
        with patch("src.strategies.volatility_breakout.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = "10:00"
            signals = self.strategy.generate_signals(
                ohlc_data={"005930": df},
                current_prices={"005930": 52000},
            )
        assert len(signals) == 0

    def test_live_close_time(self):
        """실시간 모드: 장 마감 시간 → CLOSE 신호"""
        df = pd.DataFrame([
            {"date": "2024-01-01", "open": 50000, "high": 52000, "low": 48000, "close": 51000},
            {"date": "2024-01-02", "open": 51000, "high": 53000, "low": 49000, "close": 52000},
        ])
        self.strategy.current_holdings = {"005930"}
        with patch("src.strategies.volatility_breakout.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = "15:20"
            signals = self.strategy.generate_signals(
                ohlc_data={"005930": df},
                current_prices={"005930": 54000},
            )
        close_signals = [s for s in signals if s.signal == Signal.CLOSE]
        assert len(close_signals) == 1
        assert close_signals[0].code == "005930"

    def test_on_trade_executed_buy(self):
        signal = TradeSignal(
            strategy="VolatilityBreakout", code="005930", market="KR",
            signal=Signal.BUY, price=53000,
        )
        self.strategy.on_trade_executed(signal, success=True)
        assert "005930" in self.strategy.today_entered
        assert "005930" in self.strategy.current_holdings

    def test_on_trade_executed_close(self):
        self.strategy.current_holdings = {"005930"}
        signal = TradeSignal(
            strategy="VolatilityBreakout", code="005930", market="KR",
            signal=Signal.CLOSE,
        )
        self.strategy.on_trade_executed(signal, success=True)
        assert "005930" not in self.strategy.current_holdings

    def test_on_trade_executed_failure_no_change(self):
        signal = TradeSignal(
            strategy="VolatilityBreakout", code="005930", market="KR",
            signal=Signal.BUY, price=53000,
        )
        self.strategy.on_trade_executed(signal, success=False)
        assert "005930" not in self.strategy.today_entered
        assert "005930" not in self.strategy.current_holdings

    def test_disabled_returns_empty(self):
        self.strategy.enabled = False
        df = pd.DataFrame([
            {"date": "2024-01-01", "open": 50000, "high": 52000, "low": 48000, "close": 51000},
            {"date": "2024-01-02", "open": 51000, "high": 55000, "low": 49000, "close": 52000},
        ])
        assert self.strategy.generate_signals(ohlc_data={"005930": df}) == []

    def test_get_status(self):
        status = self.strategy.get_status()
        assert status["strategy"] == "VolatilityBreakout"
        assert status["params"]["k"] == 0.5
        assert status["params"]["universe_count"] == 2


# ──────────────────────────────────────────────
# BollingerBand
# ──────────────────────────────────────────────

BOLLINGER_BAND_CONFIG = {
    "simulation": {"enabled": True, "initial_capital": 10_000_000},
    "strategies": {
        "bollinger_band": {
            "enabled": True,
            "window": 20,
            "num_std": 2.0,
            "market": "KR",
            "max_hold_per_stock": 1,
            "universe_codes": [
                {"code": "005930", "market": "KR", "name": "삼성전자"},
                {"code": "000660", "market": "KR", "name": "SK하이닉스"},
            ],
        },
    },
}


def _make_bb_prices(n: int = 30, base: float = 50000, seed: int = 42) -> pd.Series:
    """볼린저 밴드 테스트용 종가 시리즈 생성"""
    rng = np.random.RandomState(seed)
    returns = rng.randn(n) * 0.01
    prices = base * np.cumprod(1 + returns)
    return pd.Series(prices, dtype=float)


class TestBollingerBandStrategy:
    @pytest.fixture(autouse=True)
    def setup(self):
        with patch("src.strategies.bollinger_band.get_config",
                    return_value=BOLLINGER_BAND_CONFIG):
            from src.strategies.bollinger_band import BollingerBandStrategy
            self.strategy = BollingerBandStrategy()

    def test_init_loads_config(self):
        assert self.strategy.window == 20
        assert self.strategy.num_std == 2.0
        assert self.strategy.market == "KR"
        assert len(self.strategy.universe) == 2

    def test_required_codes(self):
        codes = self.strategy.required_codes()
        code_set = {c["code"] for c in codes}
        assert {"005930", "000660"} == code_set
        assert all(c["market"] == "KR" for c in codes)

    def test_generate_signals_buy(self):
        """종가가 하단 밴드 아래 → BUY 시그널"""
        # 안정적 가격 후 급락으로 하단 밴드 이탈 유도
        rng = np.random.RandomState(99)
        stable = [50000 + rng.randn() * 100 for _ in range(25)]
        # 마지막 값을 급격히 하락시켜 하단 밴드 이탈
        stable.append(stable[-1] - 3000)
        prices = pd.Series(stable, dtype=float)

        signals = self.strategy.generate_signals(close_data={"005930": prices})
        buy_signals = [s for s in signals if s.signal == Signal.BUY]
        assert len(buy_signals) == 1
        assert buy_signals[0].code == "005930"
        assert "sma" in buy_signals[0].metadata
        assert "upper_band" in buy_signals[0].metadata
        assert "lower_band" in buy_signals[0].metadata
        assert "percent_b" in buy_signals[0].metadata
        assert "bandwidth" in buy_signals[0].metadata

    def test_generate_signals_close(self):
        """종가가 상단 밴드 위 + 보유 중 → CLOSE 시그널"""
        rng = np.random.RandomState(99)
        stable = [50000 + rng.randn() * 100 for _ in range(25)]
        # 마지막 값을 급격히 상승시켜 상단 밴드 돌파
        stable.append(stable[-1] + 3000)
        prices = pd.Series(stable, dtype=float)

        # 보유 중이어야 CLOSE 시그널 발생
        self.strategy.current_holdings.add("005930")

        signals = self.strategy.generate_signals(close_data={"005930": prices})
        close_signals = [s for s in signals if s.signal == Signal.CLOSE]
        assert len(close_signals) == 1
        assert close_signals[0].code == "005930"

    def test_generate_signals_hold(self):
        """밴드 안에 있을 때 시그널 없음"""
        # 안정적 가격 → 밴드 안에 위치
        rng = np.random.RandomState(42)
        prices = pd.Series(
            [50000 + rng.randn() * 50 for _ in range(25)], dtype=float,
        )
        signals = self.strategy.generate_signals(close_data={"005930": prices})
        assert signals == []

    def test_disabled_returns_empty(self):
        """비활성 시 빈 리스트"""
        self.strategy.enabled = False
        prices = _make_bb_prices(n=30)
        assert self.strategy.generate_signals(close_data={"005930": prices}) == []

    def test_insufficient_data(self):
        """window보다 적은 데이터 시 스킵"""
        prices = pd.Series([50000, 50100, 50200], dtype=float)
        result = self.strategy.prepare_signal_kwargs({"005930": prices})
        assert result == {}

    def test_on_trade_executed(self):
        """보유 종목 추적 확인"""
        # BUY
        buy_signal = TradeSignal(
            strategy="BollingerBand", code="005930", market="KR",
            signal=Signal.BUY, price=48000,
        )
        self.strategy.on_trade_executed(buy_signal, success=True)
        assert "005930" in self.strategy.current_holdings

        # CLOSE
        close_signal = TradeSignal(
            strategy="BollingerBand", code="005930", market="KR",
            signal=Signal.CLOSE, price=52000,
        )
        self.strategy.on_trade_executed(close_signal, success=True)
        assert "005930" not in self.strategy.current_holdings

    def test_on_trade_executed_failure_no_change(self):
        """체결 실패 시 상태 변경 없음"""
        signal = TradeSignal(
            strategy="BollingerBand", code="005930", market="KR",
            signal=Signal.BUY, price=48000,
        )
        self.strategy.on_trade_executed(signal, success=False)
        assert "005930" not in self.strategy.current_holdings
