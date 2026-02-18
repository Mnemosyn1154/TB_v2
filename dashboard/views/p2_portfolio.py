from __future__ import annotations

"""Page 2: 포트폴리오 현황"""
import pandas as pd
import streamlit as st

from dashboard.services.portfolio_service import get_portfolio_status
from dashboard.components.metrics import render_portfolio_kpis


def render() -> None:
    st.header("\U0001f4bc 포트폴리오 현황")

    # ── 새로고침 ──
    col_btn, col_info = st.columns([1, 3])
    with col_btn:
        refresh = st.button("\U0001f504 새로고침", type="primary")
    with col_info:
        if st.session_state.portfolio_data and not st.session_state.portfolio_data.get("error"):
            st.caption("KIS API에서 실시간 데이터를 조회합니다.")

    if refresh or st.session_state.portfolio_data is None:
        with st.spinner("포트폴리오 조회 중..."):
            st.session_state.portfolio_data = get_portfolio_status()

    data = st.session_state.portfolio_data

    # ── 에러 처리 ──
    if data is None:
        st.info("'새로고침' 버튼을 눌러 포트폴리오를 조회하세요.")
        return

    if data.get("error"):
        st.warning(f"API 연결 실패: {data['error']}")
        st.info(
            "KIS API 인증 정보(.env)를 확인하세요. "
            "백테스트 기능은 API 없이 사용 가능합니다."
        )
        return

    # ── KPI 카드 ──
    risk = data.get("risk", {})
    render_portfolio_kpis(risk)

    # ── 리스크 게이지 ──
    st.divider()
    g1, g2, g3 = st.columns(3)

    with g1:
        cash_pct = risk.get("cash_pct", "0.0%")
        st.metric("현금 비중", cash_pct)

    with g2:
        pos_count = risk.get("positions_count", 0)
        max_pos = risk.get("max_positions", 0)
        st.metric("포지션 수", f"{pos_count} / {max_pos}")

    with g3:
        daily_pnl = risk.get("daily_pnl", 0)
        st.metric("일일 손익", f"{daily_pnl:+,.0f}")

    # ── 포지션 테이블 ──
    st.divider()
    positions = risk.get("positions", [])

    if positions:
        st.subheader("보유 포지션")
        df = pd.DataFrame(positions)
        col_rename = {"code": "종목", "side": "방향", "pnl_pct": "수익률", "value": "평가금액"}
        df = df.rename(columns=col_rename)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("현재 보유 포지션이 없습니다.")

    # ── 계좌 잔고 상세 ──
    st.divider()
    tab_kr, tab_us = st.tabs(["국내 잔고", "해외 잔고"])

    with tab_kr:
        kr = data.get("kr", {})
        if kr:
            _render_balance(kr, "KR")
        else:
            st.info("국내 계좌 데이터가 없습니다.")

    with tab_us:
        us = data.get("us", {})
        if us:
            _render_balance(us, "US")
        else:
            st.info("해외 계좌 데이터가 없습니다.")


_BALANCE_LABELS: dict[str, str] = {
    "total_equity": "총 평가금액",
    "cash": "예수금",
    "stock_value": "주식 평가액",
    "total_profit": "총 손익",
    "total_profit_rate": "총 수익률",
    "realized_profit": "실현 손익",
    "unrealized_profit": "평가 손익",
    "deposit": "예치금",
    "positions": "보유 종목",
    "summary": "계좌 요약",
}

# KIS API 내부 키 패턴 (사용자에게 노출하지 않음)
_HIDDEN_KEY_PREFIXES = ("ctx_", "output", "rt_cd", "msg_cd", "msg")


def _render_balance(balance: dict, market: str) -> None:
    """계좌 잔고 dict를 표시"""
    if isinstance(balance, dict):
        for key, val in balance.items():
            # 내부 API 키는 숨김
            if key.startswith(_HIDDEN_KEY_PREFIXES) or key.startswith("_"):
                continue
            label = _BALANCE_LABELS.get(key, key)
            if isinstance(val, (int, float)):
                st.metric(label, f"{val:,.0f}" if market == "KR" else f"${val:,.2f}")
            elif isinstance(val, list):
                if val:
                    st.subheader(label)
                    st.dataframe(pd.DataFrame(val), use_container_width=True)
            else:
                st.text(f"{label}: {val}")


