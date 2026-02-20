from __future__ import annotations

"""
AlgoTrader KR — 퀀트 팩터 전략 (Quant Factor)

멀티팩터 모델로 종목을 스코어링 → 상위 N개 매수, 하위 종목 청산.

알고리즘 흐름:
    1. 유니버스 전 종목의 일봉 데이터 수집
    2. 팩터 계산 (Value + Quality + Momentum)
    3. 종목별 복합 스코어 산출 (가중 합산)
    4. 상위 top_n 종목 선정 → 매수 신호
    5. 보유 중 탈락 종목 → 청산 신호
    6. 리밸런싱 주기마다 반복

팩터 정의:
    - Value (가치): 12개월 수익률 대비 가격 위치 (저PBR 대용)
      저점 대비 현재 위치가 낮을수록 높은 점수
    - Quality (퀄리티): 변동성 역수 (저변동성 = 고퀄리티 대용)
      변동성이 낮을수록 안정적 → 높은 점수
    - Momentum (모멘텀): 최근 N개월 수익률
      수익률이 높을수록 높은 점수

Depends on:
    - src.strategies.base (BaseStrategy, TradeSignal)
    - src.core.config (전략 파라미터)

Used by:
    - main.py (AlgoTrader._run_quant_factor)

Modification Guide:
    - 팩터 추가: _calculate_factors()에 새 팩터 계산 추가 + settings.yaml weights에 가중치 추가
    - 유니버스 변경: settings.yaml의 quant_factor.universe 블록 수정
      source: sp500 → S&P 500 자동 갱신, manual → manual_codes 사용
      legacy universe_codes도 하위 호환 지원
    - 리밸런싱 주기: rebalance_months 조정
"""
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger

from src.strategies.base import BaseStrategy, TradeSignal, Signal
from src.core.config import get_config


class QuantFactorStrategy(BaseStrategy):
    """
    퀀트 팩터 전략

    멀티팩터 복합 스코어 기반 종목 선정.
    1. Value: 12개월 고점 대비 할인율 (깊이 빠진 종목 선호)
    2. Quality: 일별 수익률 변동성 역수 (안정적 종목 선호)
    3. Momentum: 최근 N개월 수익률 (상승 추세 종목 선호)
    """

    def __init__(self, config_key: str | None = None):
        super().__init__("QuantFactor", config_key=config_key)
        config = get_config()
        qf_config = config["strategies"][self.config_key]

        self.top_n: int = qf_config["top_n"]
        self.rebalance_months: int = qf_config["rebalance_months"]
        self.lookback_days: int = qf_config.get("lookback_days", 252)
        self.momentum_days: int = qf_config.get("momentum_days", 126)
        self.volatility_days: int = qf_config.get("volatility_days", 60)
        self.min_data_days: int = qf_config.get("min_data_days", 60)

        # 팩터 가중치
        weights = qf_config["weights"]
        self.weight_value: float = weights["value"]
        self.weight_quality: float = weights["quality"]
        self.weight_momentum: float = weights["momentum"]

        # 절대 모멘텀 필터
        self.absolute_momentum_filter: bool = qf_config.get("absolute_momentum_filter", False)
        self.abs_mom_threshold: float = qf_config.get("abs_mom_threshold", 0.0)
        self.safe_asset: str = qf_config.get("safe_asset", "SHY")
        self.safe_asset_exchange: str = qf_config.get("safe_asset_exchange", "")

        # 유니버스 종목 코드
        universe_cfg = qf_config.get("universe", {})
        legacy_codes = qf_config.get("universe_codes", [])

        if not universe_cfg and legacy_codes:
            # 하위 호환: 테스트 등에서 기존 universe_codes 사용
            self._universe_source = "manual"
            self.universe_codes: list[dict] = legacy_codes
        elif universe_cfg.get("source") == "sp500":
            self._universe_source = "sp500"
            self.universe_codes = self._load_sp500_universe(universe_cfg)
        else:
            self._universe_source = "manual"
            self.universe_codes = universe_cfg.get("manual_codes", legacy_codes)

        # 현재 상태
        self.current_holdings: set[str] = set()
        self.last_scores: dict[str, dict] = {}
        self._last_rebalance_month: tuple[int, int] | None = None  # (year, month)

        logger.info(
            f"퀀트 팩터 전략: top_n={self.top_n}, "
            f"가중치=(V={self.weight_value}, Q={self.weight_quality}, M={self.weight_momentum})"
        )

    # ──────────────────────────────────────────────
    # 플러그인 인터페이스
    # ──────────────────────────────────────────────

    def get_config_key(self) -> str:
        return getattr(self, "config_key", "quant_factor")

    def required_codes(self) -> list[dict[str, str]]:
        """필요 종목 코드 목록 (exchange 포함)"""
        result = []
        for item in self.universe_codes:
            entry = {"code": item["code"], "market": item["market"]}
            if item.get("exchange"):
                entry["exchange"] = item["exchange"]
            result.append(entry)

        # 절대 모멘텀 필터 활성 시 안전자산도 포함
        if self.absolute_momentum_filter:
            safe_entry: dict[str, str] = {"code": self.safe_asset, "market": "US"}
            if self.safe_asset_exchange:
                safe_entry["exchange"] = self.safe_asset_exchange
            result.append(safe_entry)

        return result

    def prepare_signal_kwargs(self, price_data: dict[str, pd.Series]) -> dict:
        filtered = {code: prices for code, prices in price_data.items()
                    if prices is not None and len(prices) >= self.min_data_days}
        if len(filtered) < 2:
            logger.warning(
                f"[{self.name}] 시그널 스킵: 유효 종목 {len(filtered)}개 "
                f"(최소 2개 필요, min_data_days={self.min_data_days})"
            )
            return {}
        return {"price_data": filtered}

    def should_skip_date(self, date: str, equity_history: list[dict]) -> bool:
        """월별 리밸런싱: 마지막 리밸런싱 월 기준으로 rebalance_months 이상 경과해야 실행"""
        try:
            from datetime import datetime
            current = datetime.strptime(date, "%Y-%m-%d")
            current_ym = (current.year, current.month)

            if self._last_rebalance_month is None:
                # 첫 실행 — 스킵하지 않고 실행
                self._last_rebalance_month = current_ym
                return False

            last_y, last_m = self._last_rebalance_month
            months_diff = (current.year - last_y) * 12 + (current.month - last_m)
            if months_diff >= self.rebalance_months:
                self._last_rebalance_month = current_ym
                return False

            return True
        except Exception:
            return False

    # ──────────────────────────────────────────────
    # 신호 생성
    # ──────────────────────────────────────────────

    def generate_signals(self, price_data: dict[str, pd.Series] | None = None,
                         **kwargs) -> list[TradeSignal]:
        """
        팩터 스코어 기반 매매 신호 생성.

        Args:
            price_data: {종목코드: 종가 시리즈} 딕셔너리
        """
        if not self.enabled:
            return []

        if price_data is None:
            price_data = kwargs.get("price_data")

        if not price_data:
            logger.warning("퀀트 팩터: 가격 데이터 없음")
            return []

        # 1. 팩터 계산
        scores = self._calculate_composite_scores(price_data)

        if not scores:
            logger.warning("퀀트 팩터: 스코어 계산 실패 (데이터 부족)")
            return []

        self.last_scores = scores

        # 2. 상위 top_n 선정
        ranked = sorted(scores.items(), key=lambda x: x[1]["composite"], reverse=True)
        new_holdings = {code for code, _ in ranked[:self.top_n]}

        logger.info(
            f"📊 퀀트 팩터: {len(scores)}종목 스코어링 완료, "
            f"상위 {self.top_n}종목 선정"
        )

        # 상위 5종목 로깅
        for i, (code, s) in enumerate(ranked[:5], 1):
            logger.info(
                f"  #{i} {code}: 복합={s['composite']:.3f} "
                f"(V={s['value']:.3f}, Q={s['quality']:.3f}, M={s['momentum']:.3f})"
            )

        # 2-1. 절대 모멘텀 필터: raw_momentum < threshold → safe_asset 대체
        if self.absolute_momentum_filter:
            filtered_out: list[str] = []
            for code in list(new_holdings):
                raw_mom = scores[code].get("raw_momentum", 0.0)
                if raw_mom < self.abs_mom_threshold:
                    filtered_out.append(code)
                    new_holdings.discard(code)

            if filtered_out:
                new_holdings.add(self.safe_asset)
                for code in filtered_out:
                    logger.info(
                        f"  ⚠️ {code} 원본 모멘텀 {scores[code]['raw_momentum']*100:+.1f}% "
                        f"< 기준 {self.abs_mom_threshold*100:.1f}% → 안전자산({self.safe_asset}) 대체"
                    )

        # 3. 매매 신호 생성
        signals: list[TradeSignal] = []

        # 청산: 기존 보유 중 탈락 종목
        codes_to_close = self.current_holdings - new_holdings
        for code in codes_to_close:
            market = self._get_market(code)
            signals.append(TradeSignal(
                strategy=self.name,
                code=code,
                market=market,
                signal=Signal.CLOSE,
                reason=f"팩터 탈락 (리밸런싱)",
                metadata=scores.get(code, {}),
            ))

        # 매수: 신규 편입 종목
        codes_to_buy = new_holdings - self.current_holdings
        for code in codes_to_buy:
            market = self._get_market(code)
            score_info = scores.get(code, {})
            signals.append(TradeSignal(
                strategy=self.name,
                code=code,
                market=market,
                signal=Signal.BUY,
                reason=(
                    f"팩터 편입 (복합={score_info.get('composite', 0):.3f}, "
                    f"순위={score_info.get('rank', '?')}/{len(scores)})"
                ),
                metadata=score_info,
            ))

        # 상태 업데이트
        self.current_holdings = new_holdings

        if signals:
            logger.info(
                f"🔄 퀀트 팩터 리밸런싱: "
                f"매수={len(codes_to_buy)}, 청산={len(codes_to_close)}"
            )

        return signals

    def _calculate_composite_scores(self, price_data: dict[str, pd.Series]) -> dict[str, dict]:
        """
        전 종목 복합 팩터 스코어 계산.

        Returns:
            {종목코드: {"value": float, "quality": float, "momentum": float,
                        "composite": float, "rank": int, "raw_momentum": float}}
        """
        raw_factors: dict[str, dict] = {}

        for code, prices in price_data.items():
            if prices is None or len(prices) < self.min_data_days:
                continue

            factors = self._calculate_factors(prices)
            if factors is not None:
                raw_factors[code] = factors

        if len(raw_factors) < 2:
            return {}

        # Z-Score 정규화 (팩터별 상대 순위 기반)
        result = self._normalize_and_rank(raw_factors)

        # 정규화 전 원본 momentum 값 보존 (절대 모멘텀 필터용)
        for code in result:
            result[code]["raw_momentum"] = raw_factors[code]["momentum"]

        return result

    def _calculate_factors(self, prices: pd.Series) -> dict[str, float] | None:
        """
        단일 종목 팩터 값 계산.

        Returns:
            {"value": float, "quality": float, "momentum": float} 또는 None
        """
        try:
            prices = prices.dropna()
            if len(prices) < self.min_data_days:
                return None

            # Value 팩터: 12개월 고점 대비 할인율
            # 고점 대비 많이 빠진 종목 = 높은 가치 점수
            lookback = min(self.lookback_days, len(prices))
            recent_prices = prices.iloc[-lookback:]
            high_price = recent_prices.max()
            current_price = prices.iloc[-1]

            if high_price <= 0 or current_price <= 0:
                return None

            # 할인율: 1 - (현재가/고가). 많이 빠질수록 큰 값
            value_factor = 1.0 - (current_price / high_price)

            # Quality 팩터: 변동성 역수
            # 일별 수익률 표준편차가 낮을수록 고퀄리티
            vol_window = min(self.volatility_days, len(prices) - 1)
            daily_returns = prices.iloc[-vol_window:].pct_change().dropna()

            if len(daily_returns) < 20:
                return None

            volatility = daily_returns.std()
            if volatility <= 0:
                return None

            # 변동성 역수 (안정적일수록 높은 점수)
            quality_factor = 1.0 / volatility

            # Momentum 팩터: N개월 수익률
            mom_window = min(self.momentum_days, len(prices) - 1)
            if mom_window <= 0:
                return None

            momentum_factor = (prices.iloc[-1] / prices.iloc[-mom_window]) - 1.0

            return {
                "value": value_factor,
                "quality": quality_factor,
                "momentum": momentum_factor,
            }

        except Exception as e:
            logger.debug(f"팩터 계산 실패: {e}")
            return None

    def _normalize_and_rank(self, raw_factors: dict[str, dict]) -> dict[str, dict]:
        """
        팩터 값을 Z-Score 정규화 후 가중 합산 → 순위 부여.

        Z-Score = (값 - 평균) / 표준편차
        복합 = w_value * z_value + w_quality * z_quality + w_momentum * z_momentum
        """
        codes = list(raw_factors.keys())
        df = pd.DataFrame(raw_factors).T  # 종목 x 팩터

        # Z-Score 정규화
        z_scores = pd.DataFrame(index=codes)
        for col in ["value", "quality", "momentum"]:
            mean = df[col].mean()
            std = df[col].std()
            if std > 0:
                z_scores[col] = (df[col] - mean) / std
            else:
                z_scores[col] = 0.0

        # 가중 합산
        z_scores["composite"] = (
            self.weight_value * z_scores["value"]
            + self.weight_quality * z_scores["quality"]
            + self.weight_momentum * z_scores["momentum"]
        )

        # 순위 (높을수록 좋음, 1이 최고)
        z_scores["rank"] = z_scores["composite"].rank(ascending=False).astype(int)

        # dict로 변환
        result = {}
        for code in codes:
            row = z_scores.loc[code]
            result[code] = {
                "value": float(row["value"]),
                "quality": float(row["quality"]),
                "momentum": float(row["momentum"]),
                "composite": float(row["composite"]),
                "rank": int(row["rank"]),
            }

        return result

    def _load_sp500_universe(self, universe_cfg: dict) -> list[dict]:
        """S&P 500 유니버스 로딩, 실패 시 manual_codes fallback"""
        try:
            from src.core.universe import UniverseManager

            mgr = UniverseManager()
            stocks = mgr.get_stocks(universe_cfg)
            if stocks:
                logger.info(f"S&P 500 유니버스 로딩: {len(stocks)}개 종목")
                return stocks
        except Exception as e:
            logger.warning(f"S&P 500 유니버스 로딩 실패: {e}")

        fallback = universe_cfg.get("manual_codes", [])
        logger.info(f"manual_codes fallback: {len(fallback)}개 종목")
        return fallback

    def _get_market(self, code: str) -> str:
        """종목 코드로 시장 판별"""
        if self.absolute_momentum_filter and code == self.safe_asset:
            return "US"
        for item in self.universe_codes:
            if item["code"] == code:
                return item.get("market", "KR")
        # 코드가 숫자면 KR, 알파벳이면 US
        return "KR" if code.isdigit() else "US"

    def get_status(self) -> dict[str, Any]:
        """현재 전략 상태"""
        top_5 = sorted(
            self.last_scores.items(),
            key=lambda x: x[1].get("composite", 0),
            reverse=True,
        )[:5]

        return {
            "strategy": self.name,
            "enabled": self.enabled,
            "top_n": self.top_n,
            "rebalance_months": self.rebalance_months,
            "weights": {
                "value": self.weight_value,
                "quality": self.weight_quality,
                "momentum": self.weight_momentum,
            },
            "current_holdings": sorted(self.current_holdings),
            "holdings_count": len(self.current_holdings),
            "universe_size": len(self.universe_codes),
            "top_5_scores": {
                code: {k: round(v, 3) for k, v in s.items()}
                for code, s in top_5
            },
        }
