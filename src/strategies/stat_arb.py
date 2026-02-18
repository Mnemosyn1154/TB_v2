from __future__ import annotations

"""
AlgoTrader KR — 통계적 차익거래 전략 (Pairs Trading)

공적분 관계의 두 종목 간 스프레드 Z-Score 기반 매매.
한국/미국 공매도 제약 → 인버스 ETF로 숏 헤지 대체.

페어: MSFT/GOOGL (1순위), 삼성전자/SK하이닉스 (2순위)
숏 대체: 섹터별 인버스 ETF (PSQ, KODEX 인버스)

알고리즘 흐름:
    1. Engle-Granger 공적분 검정 (p < 0.05)
    2. OLS 회귀 → 헤지 비율 β
    3. 스프레드 = A - β × B → 롤링 Z-Score
    4. Z > entry → B 롱 + 인버스 ETF, Z < -entry → A 롱 + 인버스 ETF
    5. |Z| < exit → 청산, |Z| > stop → 손절

Depends on:
    - src.strategies.base (BaseStrategy, TradeSignal)
    - src.core.config (전략 파라미터)
    - scipy, statsmodels, sklearn (통계 분석)

Used by:
    - main.py (AlgoTrader._run_stat_arb)

Modification Guide:
    - 새 페어 추가: settings.yaml의 stat_arb.pairs[]에 추가만 하면 자동 로드
    - Z-Score 커스텀: calculate_z_score()의 롤링 방식 변경 가능
    - 진입/청산 로직 변경: generate_signals() 내부의 z 비교 조건 수정
"""
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.tsa.stattools import coint, adfuller
from sklearn.linear_model import LinearRegression
from loguru import logger

from src.strategies.base import BaseStrategy, TradeSignal, Signal
from src.core.config import get_config


@dataclass
class PairConfig:
    """페어 설정"""
    name: str
    market: str
    stock_a: str            # 종목 A (예: MSFT)
    stock_b: str            # 종목 B (예: GOOGL)
    hedge_etf: str          # 인버스 ETF (예: PSQ)
    exchange_a: str = ""    # 종목 A 거래소 (US: NAS/NYS)
    exchange_b: str = ""    # 종목 B 거래소
    exchange_hedge: str = ""  # 헤지 ETF 거래소


@dataclass
class PairState:
    """페어 현재 상태"""
    beta: float = 0.0           # 헤지 비율
    spread_mean: float = 0.0    # 스프레드 평균
    spread_std: float = 0.0     # 스프레드 표준편차
    current_z: float = 0.0      # 현재 Z-Score
    is_cointegrated: bool = False
    p_value: float = 1.0
    position: str = "NONE"      # "NONE", "LONG_A", "LONG_B"


class StatArbStrategy(BaseStrategy):
    """
    통계적 차익거래 (Pairs Trading) 전략

    핵심 로직:
    1. 공적분 검정으로 페어 유효성 확인
    2. OLS 회귀로 헤지 비율(β) 계산
    3. 스프레드 Z-Score 기반 매매 신호 생성
    4. 숏 대신 인버스 ETF 활용
    """

    def __init__(self):
        super().__init__("StatArb")
        config = get_config()
        sa_config = config["strategies"]["stat_arb"]

        # 파라미터
        self.lookback = sa_config["lookback_window"]
        self.entry_z = sa_config["entry_z_score"]
        self.exit_z = sa_config["exit_z_score"]
        self.stop_z = sa_config["stop_loss_z_score"]
        self.recalc_days = sa_config["recalc_beta_days"]
        self.coint_pvalue = sa_config.get("coint_pvalue", 0.05)

        # 페어 설정 로드
        self.pairs: list[PairConfig] = []
        self.pair_states: dict[str, PairState] = {}
        # 공적분 재검정 추적: {pair_name: 마지막 검정 시 데이터 길이}
        self._last_coint_len: dict[str, int] = {}

        for p in sa_config["pairs"]:
            pair = PairConfig(
                name=p["name"],
                market=p["market"],
                stock_a=p["stock_a"],
                stock_b=p["stock_b"],
                hedge_etf=p["hedge_etf"],
                exchange_a=p.get("exchange_a", ""),
                exchange_b=p.get("exchange_b", ""),
                exchange_hedge=p.get("exchange_hedge", ""),
            )
            self.pairs.append(pair)
            self.pair_states[pair.name] = PairState()

        logger.info(f"StatArb 전략: {len(self.pairs)}개 페어 로드 — "
                    f"진입 Z={self.entry_z}, 청산 Z={self.exit_z}, 손절 Z={self.stop_z}")

    # ──────────────────────────────────────────────
    # 플러그인 인터페이스
    # ──────────────────────────────────────────────

    def get_config_key(self) -> str:
        return "stat_arb"

    def get_pair_names(self) -> list[str]:
        """사용 가능한 페어 이름 목록 반환"""
        return [p.name for p in self.pairs]

    def filter_pairs(self, pair_names: list[str]) -> None:
        """특정 페어만 사용하도록 필터링"""
        pair_set = set(pair_names)
        self.pairs = [p for p in self.pairs if p.name in pair_set]
        self.pair_states = {k: v for k, v in self.pair_states.items() if k in pair_set}
        self._last_coint_len = {k: v for k, v in self._last_coint_len.items() if k in pair_set}
        logger.info(f"StatArb 페어 필터링: {[p.name for p in self.pairs]}")

    def required_codes(self) -> list[dict[str, str]]:
        """페어 종목 + 헤지 ETF 코드 목록 (exchange 포함)"""
        codes = []
        for pair in self.pairs:
            entry_a = {"code": pair.stock_a, "market": pair.market}
            if pair.exchange_a:
                entry_a["exchange"] = pair.exchange_a
            codes.append(entry_a)

            entry_b = {"code": pair.stock_b, "market": pair.market}
            if pair.exchange_b:
                entry_b["exchange"] = pair.exchange_b
            codes.append(entry_b)

            if pair.hedge_etf:
                entry_h = {"code": pair.hedge_etf, "market": pair.market}
                if pair.exchange_hedge:
                    entry_h["exchange"] = pair.exchange_hedge
                codes.append(entry_h)
        return codes

    def prepare_signal_kwargs(self, price_data: dict[str, pd.Series]) -> dict:
        """원시 가격 데이터 → pair_data 형식으로 변환"""
        pair_data = {}
        for pair in self.pairs:
            prices_a = price_data.get(pair.stock_a)
            prices_b = price_data.get(pair.stock_b)

            if prices_a is None or prices_b is None:
                continue
            if len(prices_a) < 60 or len(prices_b) < 60:
                continue

            pair_data[pair.name] = {
                "prices_a": prices_a,
                "prices_b": prices_b,
            }

        if not pair_data:
            return {}
        return {"pair_data": pair_data}

    # ──────────────────────────────────────────────
    # 공적분 분석
    # ──────────────────────────────────────────────

    def test_cointegration(self, prices_a: pd.Series, prices_b: pd.Series) -> tuple[bool, float]:
        """
        Engle-Granger 공적분 검정 (로그 변환 적용)

        Returns:
            (is_cointegrated, p_value)
        """
        if len(prices_a) < 30 or len(prices_b) < 30:
            logger.warning("데이터 부족: 공적분 검정에 최소 30개 데이터 필요")
            return False, 1.0

        # 로그 변환: 가격 수준 차이에 따른 통계 불안정성 해소
        log_a = np.log(prices_a.clip(lower=1e-8))
        log_b = np.log(prices_b.clip(lower=1e-8))

        score, p_value, _ = coint(log_a, log_b)
        is_coint = p_value < self.coint_pvalue

        logger.info(f"공적분 검정: p-value={p_value:.4f} → {'✅ 공적분 존재' if is_coint else '❌ 공적분 없음'}")
        return is_coint, p_value

    def calculate_hedge_ratio(self, prices_a: pd.Series, prices_b: pd.Series) -> float:
        """
        OLS 회귀로 헤지 비율 β 계산
        prices_a = α + β × prices_b + ε
        """
        model = LinearRegression()
        model.fit(prices_b.values.reshape(-1, 1), prices_a.values)
        beta = model.coef_[0]

        logger.info(f"헤지 비율 β = {beta:.4f}")
        return beta

    def calculate_spread(self, prices_a: pd.Series, prices_b: pd.Series,
                         beta: float) -> pd.Series:
        """스프레드 계산: Spread = A - β × B"""
        return prices_a - beta * prices_b

    def calculate_z_score(self, spread: pd.Series, window: int | None = None) -> pd.Series:
        """롤링 Z-Score 계산"""
        if window is None:
            window = self.lookback

        mean = spread.rolling(window=window).mean()
        std = spread.rolling(window=window).std()

        # 0으로 나누기 방지
        std = std.replace(0, np.nan)
        z_score = (spread - mean) / std

        return z_score

    # ──────────────────────────────────────────────
    # 페어 분석 & 업데이트
    # ──────────────────────────────────────────────

    def _should_recalc_coint(self, pair_name: str, data_len: int) -> bool:
        """공적분 재검정이 필요한지 판단 (recalc_days 간격)"""
        last_len = self._last_coint_len.get(pair_name, 0)
        return (data_len - last_len) >= self.recalc_days or last_len == 0

    def analyze_pair(self, pair: PairConfig,
                     prices_a: pd.Series, prices_b: pd.Series) -> PairState:
        """
        페어 전체 분석 수행
        1. 공적분 검정 (recalc_days 간격으로만)
        2. 헤지 비율 계산 (공적분 재검정 시)
        3. 스프레드 & Z-Score (매일 갱신)
        """
        state = self.pair_states[pair.name]
        data_len = min(len(prices_a), len(prices_b))

        # 1. 공적분 검정 — recalc_days 간격으로만 수행
        if self._should_recalc_coint(pair.name, data_len):
            is_coint, p_value = self.test_cointegration(prices_a, prices_b)
            state.is_cointegrated = is_coint
            state.p_value = p_value
            self._last_coint_len[pair.name] = data_len

            if is_coint:
                # 공적분 확인 시 헤지 비율도 재계산
                state.beta = self.calculate_hedge_ratio(prices_a, prices_b)

        if not state.is_cointegrated:
            logger.warning(f"⚠️ {pair.name}: 공적분 관계 없음 — 신호 생성 중단")
            return state

        # 2. 스프레드 & Z-Score — 매일 갱신
        spread = self.calculate_spread(prices_a, prices_b, state.beta)
        z_scores = self.calculate_z_score(spread)

        if not z_scores.empty and not z_scores.isna().all():
            state.current_z = float(z_scores.iloc[-1])
            state.spread_mean = float(spread.rolling(self.lookback).mean().iloc[-1])
            state.spread_std = float(spread.rolling(self.lookback).std().iloc[-1])

        logger.info(
            f"📊 {pair.name} 분석 완료: β={state.beta:.4f}, "
            f"Z-Score={state.current_z:.2f}, 공적분 p={state.p_value:.4f}"
        )

        return state

    # ──────────────────────────────────────────────
    # 신호 생성
    # ──────────────────────────────────────────────

    def generate_signals(self, pair_data: dict[str, dict[str, pd.Series]] | None = None,
                         **kwargs) -> list[TradeSignal]:
        """
        모든 페어에 대해 매매 신호 생성

        Args:
            pair_data: {pair_name: {"prices_a": Series, "prices_b": Series}}

        Returns:
            list of TradeSignal
        """
        if not self.enabled:
            return []

        if pair_data is None:
            pair_data = kwargs.get("pair_data", {})

        signals: list[TradeSignal] = []

        for pair in self.pairs:
            data = pair_data.get(pair.name, {})
            prices_a = data.get("prices_a")
            prices_b = data.get("prices_b")

            if prices_a is None or prices_b is None:
                continue

            # 페어 분석
            state = self.analyze_pair(pair, prices_a, prices_b)

            if not state.is_cointegrated:
                continue

            z = state.current_z
            current_pos = state.position

            # ── 손절 ──
            if current_pos != "NONE" and abs(z) > self.stop_z:
                signals.extend(self._close_signals(pair, state, reason=f"손절 (Z={z:.2f})"))
                # state.position은 on_trade_executed()에서 업데이트
                continue

            # ── 청산 (평균 회귀 완료) ──
            if current_pos != "NONE" and abs(z) < self.exit_z:
                signals.extend(self._close_signals(pair, state, reason=f"청산 (Z={z:.2f}, 평균 회귀)"))
                # state.position은 on_trade_executed()에서 업데이트
                continue

            # ── 신규 진입 ──
            if current_pos == "NONE":
                if z > self.entry_z:
                    # A가 상대적으로 과대평가 → B 롱 + 인버스 ETF 롱(헤지)
                    signals.append(TradeSignal(
                        strategy=self.name,
                        code=pair.stock_b,
                        market=pair.market,
                        signal=Signal.BUY,
                        reason=f"{pair.name}: B 롱 (Z={z:.2f} > {self.entry_z}, A 과대평가)",
                        metadata={"pair": pair.name, "z_score": z, "beta": state.beta,
                                  "target_position": "LONG_B"},
                    ))
                    signals.append(TradeSignal(
                        strategy=self.name,
                        code=pair.hedge_etf,
                        market=pair.market,
                        signal=Signal.BUY,
                        reason=f"{pair.name}: 인버스 ETF 헤지 (섹터 하락 보호)",
                        metadata={"pair": pair.name, "role": "hedge"},
                    ))
                    # 주의: state.position은 on_trade_executed()에서 업데이트
                    logger.info(f"🔵 {pair.name}: LONG_B 진입 신호 (Z={z:.2f})")

                elif z < -self.entry_z:
                    # A가 상대적으로 과소평가 → A 롱 + 인버스 ETF 롱(헤지)
                    signals.append(TradeSignal(
                        strategy=self.name,
                        code=pair.stock_a,
                        market=pair.market,
                        signal=Signal.BUY,
                        reason=f"{pair.name}: A 롱 (Z={z:.2f} < -{self.entry_z}, A 과소평가)",
                        metadata={"pair": pair.name, "z_score": z, "beta": state.beta,
                                  "target_position": "LONG_A"},
                    ))
                    signals.append(TradeSignal(
                        strategy=self.name,
                        code=pair.hedge_etf,
                        market=pair.market,
                        signal=Signal.BUY,
                        reason=f"{pair.name}: 인버스 ETF 헤지 (섹터 하락 보호)",
                        metadata={"pair": pair.name, "role": "hedge"},
                    ))
                    # 주의: state.position은 on_trade_executed()에서 업데이트
                    logger.info(f"🔵 {pair.name}: LONG_A 진입 신호 (Z={z:.2f})")

        return signals

    def on_trade_executed(self, signal: TradeSignal, success: bool) -> None:
        """엔진 체결 콜백 — 페어 포지션 상태를 실제 체결에 맞춰 동기화"""
        pair_name = signal.metadata.get("pair") if signal.metadata else None
        if not pair_name or pair_name not in self.pair_states:
            return

        state = self.pair_states[pair_name]

        if signal.signal == Signal.BUY and success:
            target = signal.metadata.get("target_position")
            if target in ("LONG_A", "LONG_B"):
                state.position = target
                logger.info(f"[StatArb] {pair_name} 포지션 확정: {target}")
        elif signal.signal == Signal.CLOSE and success:
            # hedge 해제가 아닌 메인 포지션 청산일 때만 NONE으로
            if signal.metadata.get("role") != "hedge":
                state.position = "NONE"
                logger.info(f"[StatArb] {pair_name} 포지션 청산 확정")

    def _close_signals(self, pair: PairConfig, state: PairState,
                       reason: str) -> list[TradeSignal]:
        """포지션 청산 신호 생성"""
        signals = []

        # 롱 포지션 청산
        if state.position == "LONG_A":
            signals.append(TradeSignal(
                strategy=self.name, code=pair.stock_a, market=pair.market,
                signal=Signal.CLOSE, reason=reason,
                metadata={"pair": pair.name},
            ))
        elif state.position == "LONG_B":
            signals.append(TradeSignal(
                strategy=self.name, code=pair.stock_b, market=pair.market,
                signal=Signal.CLOSE, reason=reason,
                metadata={"pair": pair.name},
            ))

        # 인버스 ETF 헤지 청산
        signals.append(TradeSignal(
            strategy=self.name, code=pair.hedge_etf, market=pair.market,
            signal=Signal.CLOSE, reason=f"{reason} — 헤지 해제",
            metadata={"pair": pair.name, "role": "hedge"},
        ))

        logger.info(f"🔴 {pair.name}: 포지션 청산 — {reason}")
        return signals

    # ──────────────────────────────────────────────
    # 상태 조회
    # ──────────────────────────────────────────────

    def get_status(self) -> dict[str, Any]:
        """현재 전략 상태"""
        return {
            "strategy": self.name,
            "enabled": self.enabled,
            "pairs": {
                pair.name: {
                    "stock_a": pair.stock_a,
                    "stock_b": pair.stock_b,
                    "hedge_etf": pair.hedge_etf,
                    "beta": self.pair_states[pair.name].beta,
                    "z_score": self.pair_states[pair.name].current_z,
                    "cointegrated": self.pair_states[pair.name].is_cointegrated,
                    "p_value": self.pair_states[pair.name].p_value,
                    "position": self.pair_states[pair.name].position,
                }
                for pair in self.pairs
            },
            "params": {
                "lookback": self.lookback,
                "entry_z": self.entry_z,
                "exit_z": self.exit_z,
                "stop_z": self.stop_z,
            },
        }
