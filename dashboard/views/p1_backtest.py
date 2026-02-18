from __future__ import annotations

"""Page 1: 백테스트 결과 시각화 (멀티페어 지원)"""
from datetime import date

import streamlit as st

from dashboard.services.backtest_service import (
    run_backtest,
    run_backtest_per_pair,
    get_pair_names,
)
from dashboard.services.config_service import load_settings, parse_date as _parse_date
from dashboard.components.charts import (
    equity_curve_chart,
    drawdown_chart,
    monthly_heatmap,
    pnl_distribution_chart,
    multi_equity_curve_chart,
    pair_comparison_bar_chart,
)
from dashboard.components.metrics import render_backtest_kpis, render_pair_comparison_table
from dashboard.components.trade_table import render_trade_table


# ── 백테스트 모드 ──
_MODE_ALL = "전체 합산"
_MODE_SINGLE_PAIR = "특정 페어"
_MODE_COMPARE = "페어별 비교"


def render() -> None:
    st.header("\U0001f4ca 백테스트 분석")

    # ── 설정 로드 ──
    try:
        config = load_settings()
    except Exception:
        config = {}
    bt_cfg = config.get("backtest", {})

    # ── 컨트롤 바 (Row 1: 전략 + 기간 + 자본금) ──
    col_strat, col_start, col_end, col_capital = st.columns([3, 2, 2, 3])

    with col_strat:
        strategy_options = {
            "통계적 차익거래 (StatArb)": "stat_arb",
            "듀얼 모멘텀": "dual_momentum",
            "퀀트 팩터": "quant_factor",
        }
        strategy_label = st.selectbox("전략 선택", list(strategy_options.keys()))
        strategy_name = strategy_options[strategy_label]

    with col_start:
        default_start = _parse_date(bt_cfg.get("start_date"), date(2024, 1, 1))
        start_date = st.date_input("시작일", value=default_start)

    with col_end:
        default_end = _parse_date(bt_cfg.get("end_date"), date.today())
        end_date = st.date_input("종료일", value=default_end)

    with col_capital:
        initial_capital = st.number_input(
            "초기 자본금 (KRW)",
            value=int(bt_cfg.get("initial_capital", 10_000_000)),
            step=1_000_000,
            format="%d",
        )

    # ── 컨트롤 바 (Row 2: 페어 선택 + 실행 버튼) ──
    pair_names = _get_cached_pair_names(strategy_name)
    has_pairs = len(pair_names) > 0

    if has_pairs:
        col_mode, col_pair, col_run = st.columns([2, 3, 2])

        with col_mode:
            mode = st.radio(
                "백테스트 모드",
                [_MODE_ALL, _MODE_SINGLE_PAIR, _MODE_COMPARE],
                horizontal=True,
            )

        with col_pair:
            selected_pair = None
            if mode == _MODE_SINGLE_PAIR:
                selected_pair = st.selectbox("페어 선택", pair_names)
            elif mode == _MODE_COMPARE:
                st.caption(f"전체 {len(pair_names)}개 페어를 개별 비교합니다")
            else:
                st.caption("모든 페어를 합산하여 백테스트합니다")

        with col_run:
            st.write("")  # spacing
            run_clicked = st.button(
                "\U0001f680 백테스트 실행", use_container_width=True, type="primary",
            )
    else:
        mode = _MODE_ALL
        selected_pair = None
        run_clicked = st.button(
            "\U0001f680 백테스트 실행", use_container_width=True, type="primary",
        )

    # ── 실행 ──
    if run_clicked:
        _execute_backtest(
            strategy_name=strategy_name,
            initial_capital=float(initial_capital),
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            bt_cfg=bt_cfg,
            mode=mode,
            selected_pair=selected_pair,
        )

    # ── 결과 표시 ──
    result_mode = st.session_state.get("backtest_mode", _MODE_ALL)

    if result_mode == _MODE_COMPARE:
        _render_comparison_results()
    else:
        _render_single_results()


# ──────────────────────────────────────────────
# 실행 로직
# ──────────────────────────────────────────────

def _execute_backtest(
    strategy_name: str,
    initial_capital: float,
    start_date: str,
    end_date: str,
    bt_cfg: dict,
    mode: str,
    selected_pair: str | None,
) -> None:
    """모드에 따라 백테스트를 실행하고 session_state에 저장"""
    commission = bt_cfg.get("commission_rate", 0.00015)
    slippage = bt_cfg.get("slippage_rate", 0.001)

    if mode == _MODE_COMPARE:
        with st.spinner("페어별 백테스트 실행 중..."):
            try:
                per_pair = run_backtest_per_pair(
                    strategy_name=strategy_name,
                    initial_capital=initial_capital,
                    start_date=start_date,
                    end_date=end_date,
                    commission_rate=commission,
                    slippage_rate=slippage,
                )
                st.session_state.backtest_per_pair = per_pair
                st.session_state.backtest_mode = _MODE_COMPARE
                st.session_state.selected_strategy = strategy_name
                # 단일 결과도 초기화
                st.session_state.backtest_result = None
                st.session_state.backtest_metrics = None
            except Exception as e:
                st.error(f"페어별 백테스트 오류: {e}")
    else:
        pair_name = selected_pair if mode == _MODE_SINGLE_PAIR else None
        with st.spinner("백테스트 실행 중..."):
            try:
                result, metrics = run_backtest(
                    strategy_name=strategy_name,
                    initial_capital=initial_capital,
                    start_date=start_date,
                    end_date=end_date,
                    commission_rate=commission,
                    slippage_rate=slippage,
                    pair_name=pair_name,
                )
                st.session_state.backtest_result = result
                st.session_state.backtest_metrics = metrics
                st.session_state.backtest_mode = mode
                st.session_state.selected_strategy = strategy_name
                # 비교 결과 초기화
                st.session_state.backtest_per_pair = None
                # 데이터 소스 알림
                data_source = metrics.get("data_source", "")
                if "yfinance" in data_source:
                    st.info("DB 데이터가 부족하여 yfinance 데이터로 백테스트를 실행했습니다.")
                elif "룩백 부족" in data_source:
                    st.warning("DB 데이터의 룩백 기간이 부족합니다. 거래가 적을 수 있습니다.")
            except Exception as e:
                st.error(f"백테스트 오류: {e}")


# ──────────────────────────────────────────────
# 단일 결과 렌더링 (전체 합산 / 특정 페어)
# ──────────────────────────────────────────────

def _render_single_results() -> None:
    """단일 백테스트 결과 표시 (기존 로직)"""
    result = st.session_state.get("backtest_result")
    metrics = st.session_state.get("backtest_metrics")

    if result is None or metrics is None:
        st.info("백테스트를 실행하면 여기에 결과가 표시됩니다.")
        return

    if result.equity_curve is None or len(result.equity_curve) < 2:
        st.warning("백테스트 결과 데이터가 부족합니다. 데이터를 먼저 수집해주세요.")
        return

    # ── KPI 카드 ──
    st.divider()
    render_backtest_kpis(metrics)

    # 기본 정보
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("초기 자본 (KRW)", f"\u20a9{metrics['initial_capital']:,.0f}")
    c2.metric("최종 자산 (KRW)", f"\u20a9{metrics['final_equity']:,.0f}")
    c3.metric("거래일수", f"{metrics['trading_days']}")
    c4.metric("총 수수료", f"{metrics['total_commission']:,.0f}")

    # ── 차트 ──
    st.divider()
    tab_equity, tab_dd = st.tabs(["에퀴티 커브", "드로다운"])

    with tab_equity:
        st.plotly_chart(
            equity_curve_chart(result.equity_curve),
            use_container_width=True,
        )

    with tab_dd:
        st.plotly_chart(
            drawdown_chart(result.equity_curve),
            use_container_width=True,
        )

    # ── 월별 수익률 히트맵 ──
    monthly = metrics.get("monthly_returns")
    if monthly is not None and not monthly.empty:
        st.plotly_chart(
            monthly_heatmap(monthly),
            use_container_width=True,
        )

    # ── 거래 분석 ──
    st.divider()
    st.subheader("거래 분석")

    tab_list, tab_dist, tab_detail = st.tabs(["거래 목록", "손익 분포", "상세 지표"])

    with tab_list:
        render_trade_table(result.trades)

    with tab_dist:
        sell_trades = [t for t in result.trades if t.side == "SELL"]
        if sell_trades:
            pnl_values = [t.pnl for t in sell_trades]
            st.plotly_chart(
                pnl_distribution_chart(pnl_values),
                use_container_width=True,
            )
        else:
            st.info("매도 거래가 없습니다.")

    with tab_detail:
        d1, d2, d3, d4 = st.columns(4)
        d1.metric("평균 수익 거래", f"{metrics['avg_win']:+,.0f}")
        d2.metric("평균 손실 거래", f"{metrics['avg_loss']:,.0f}")
        d3.metric("최대 수익", f"{metrics['max_win']:+,.0f}")
        d4.metric("최대 손실", f"{metrics['max_loss']:+,.0f}")

        d5, d6, d7, d8 = st.columns(4)
        d5.metric("소르티노", f"{metrics['sortino_ratio']:.2f}")
        d6.metric("연 변동성", f"{metrics['annual_volatility']:.1%}")
        d7.metric("평균 보유일", f"{metrics['avg_holding_days']:.1f}일")
        d8.metric("MDD 복구일", metrics.get("mdd_recovery", "-"))


# ──────────────────────────────────────────────
# 페어별 비교 결과 렌더링
# ──────────────────────────────────────────────

def _render_comparison_results() -> None:
    """페어별 비교 결과 표시"""
    per_pair = st.session_state.get("backtest_per_pair")

    if not per_pair:
        st.info("백테스트를 실행하면 여기에 결과가 표시됩니다.")
        return

    # 유효한 결과만 필터링
    valid = {
        name: (result, metrics)
        for name, (result, metrics) in per_pair.items()
        if result.equity_curve is not None and len(result.equity_curve) >= 2
    }

    if not valid:
        st.warning("유효한 백테스트 결과가 없습니다.")
        return

    st.divider()
    st.subheader(f"페어별 비교 ({len(valid)}개 페어)")

    # ── 비교 테이블 ──
    metrics_dict = {name: m for name, (_, m) in valid.items()}
    render_pair_comparison_table(metrics_dict)

    # ── 지표 비교 바 차트 ──
    if len(valid) >= 2:
        st.plotly_chart(
            pair_comparison_bar_chart(metrics_dict),
            use_container_width=True,
        )

    # ── 에퀴티 커브 비교 ──
    st.divider()
    curves = {name: result.equity_curve for name, (result, _) in valid.items()}

    tab_norm, tab_abs = st.tabs(["정규화 비교 (시작=100)", "절대 금액 비교"])

    with tab_norm:
        st.plotly_chart(
            multi_equity_curve_chart(curves, normalize=True),
            use_container_width=True,
        )

    with tab_abs:
        st.plotly_chart(
            multi_equity_curve_chart(curves, normalize=False),
            use_container_width=True,
        )

    # ── 개별 페어 상세 (확장 가능) ──
    st.divider()
    st.subheader("개별 페어 상세")

    pair_tabs = st.tabs(list(valid.keys()))
    for tab, (pair_name, (result, metrics)) in zip(pair_tabs, valid.items()):
        with tab:
            _render_pair_detail(pair_name, result, metrics)


def _render_pair_detail(pair_name: str, result, metrics: dict) -> None:
    """개별 페어 상세 결과 표시"""
    # KPI
    render_backtest_kpis(metrics)

    # 기본 정보
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("초기 자본", f"\u20a9{metrics['initial_capital']:,.0f}")
    c2.metric("최종 자산", f"\u20a9{metrics['final_equity']:,.0f}")
    c3.metric("거래수", f"{metrics['total_trades']}")
    c4.metric("총 수수료", f"{metrics['total_commission']:,.0f}")

    # 에퀴티 커브 + 드로다운
    col_eq, col_dd = st.columns(2)
    with col_eq:
        st.plotly_chart(
            equity_curve_chart(result.equity_curve),
            use_container_width=True,
        )
    with col_dd:
        st.plotly_chart(
            drawdown_chart(result.equity_curve),
            use_container_width=True,
        )

    # 거래 목록
    if result.trades:
        with st.expander(f"거래 내역 ({len(result.trades)}건)", expanded=False):
            render_trade_table(result.trades)


# ──────────────────────────────────────────────
# 유틸리티
# ──────────────────────────────────────────────

@st.cache_data(ttl=60)
def _get_cached_pair_names(strategy_name: str) -> list[str]:
    """전략의 페어 목록을 캐시하여 반환"""
    try:
        return get_pair_names(strategy_name)
    except Exception:
        return []
