from __future__ import annotations

# AlgoTrader KR — 웹 대시보드 진입점
#
# Streamlit 기반 웹 UI. 사이드바 네비게이션으로 4개 페이지를 라우팅합니다.
#
# 실행:
#     streamlit run dashboard/app.py
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가 (src.* import 허용)
ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

# ── 페이지 설정 (반드시 첫 번째 Streamlit 호출) ──
st.set_page_config(
    page_title="AlgoTrader KR",
    page_icon="\U0001f916",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── session_state 초기값 ──
_defaults = {
    "backtest_result": None,
    "backtest_metrics": None,
    "backtest_per_pair": None,
    "backtest_mode": "전체 합산",
    "selected_strategy": "stat_arb",
    "portfolio_data": None,
    "config_cache": None,
    "bot_log": [],
    "kill_switch_active": False,
    "paper_signals": [],
}
for key, default in _defaults.items():
    if key not in st.session_state:
        st.session_state[key] = default

# Kill Switch 파일 상태 복원 (세션 시작 시 1회)
if st.session_state.kill_switch_active is False:
    try:
        from dashboard.services.bot_service import get_kill_switch_status
        st.session_state.kill_switch_active = get_kill_switch_status()
    except Exception as e:
        from loguru import logger
        logger.warning(f"Kill Switch 상태 로드 실패 (기본값 False 사용): {e}")

# ── 사이드바 ──
with st.sidebar:
    st.title("\U0001f916 AlgoTrader KR")
    st.caption("자동 트레이딩 대시보드")
    st.divider()

    # 사이드바 라디오 버튼 항목 간격 확대
    st.markdown(
        """<style>
        div[role="radiogroup"] > label {
            margin-bottom: 10px;
            padding: 4px 0;
        }
        </style>""",
        unsafe_allow_html=True,
    )

    page = st.radio(
        "메뉴",
        [
            "\U0001f4ca 백테스트",
            "\U0001f4bc 포트폴리오",
            "\u2699\ufe0f 전략 설정",
            "\U0001f3ae 봇 제어",
            "\U0001f4dd 모의 거래",
        ],
        label_visibility="collapsed",
    )
    st.divider()

    # 모드 표시
    try:
        from src.core.config import get_config
        cfg = get_config()
        is_live = cfg.get("kis", {}).get("live_trading", False)
        if is_live:
            st.error("모드: **실거래**")
        else:
            st.info("모드: **모의투자**")
    except Exception:
        st.warning("설정 로드 실패")

    st.caption("v1.0 | Streamlit Dashboard")

# ── 페이지 라우팅 ──
if "백테스트" in page:
    from dashboard.views.p1_backtest import render
    render()
elif "포트폴리오" in page:
    from dashboard.views.p2_portfolio import render
    render()
elif "전략 설정" in page:
    from dashboard.views.p3_settings import render
    render()
elif "봇 제어" in page:
    from dashboard.views.p4_control import render
    render()
elif "모의 거래" in page:
    from dashboard.views.p5_paper_trading import render
    render()
