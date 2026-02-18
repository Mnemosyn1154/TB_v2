from __future__ import annotations

"""Page 4: 봇 제어 패널"""
from datetime import datetime

import streamlit as st


def render() -> None:
    st.header("\U0001f3ae 봇 제어 패널")

    # ── 상태 배너 ──
    ks = st.session_state.kill_switch_active
    if ks:
        st.error("Kill Switch **활성화** 상태 — 모든 거래가 중단됩니다.")
    else:
        st.success("봇 상태: **대기 중** (정상)")

    # ── 주요 액션 버튼 ──
    st.divider()
    c1, c2, c3 = st.columns(3)

    with c1:
        if st.button("\u25b6\ufe0f 전략 1회 실행", use_container_width=True, type="primary"):
            _run_strategy_once()

    with c2:
        if st.button("\U0001f4e5 데이터 수집", use_container_width=True):
            _collect_data()

    with c3:
        if st.button("\U0001f4cb 상태 조회", use_container_width=True):
            _show_status()

    # ── Kill Switch ──
    st.divider()
    st.subheader("Kill Switch (긴급 거래 중단)")

    # 2단계 확인용 session state
    if "ks_confirm_activate" not in st.session_state:
        st.session_state.ks_confirm_activate = False
    if "ks_confirm_deactivate" not in st.session_state:
        st.session_state.ks_confirm_deactivate = False

    if not ks:
        # ── 활성화 플로우 ──
        if not st.session_state.ks_confirm_activate:
            if st.button("\u26a0\ufe0f Kill Switch 활성화", use_container_width=True, type="primary", key="ks_act"):
                st.session_state.ks_confirm_activate = True
                st.rerun()
        else:
            st.warning("\u26a0\ufe0f Kill Switch를 활성화하면 **모든 거래가 즉시 중단**됩니다.")
            cc1, cc2 = st.columns(2)
            with cc1:
                if st.button("\u2705 확인 — 활성화", use_container_width=True, type="primary", key="ks_act_confirm"):
                    try:
                        from dashboard.services.bot_service import activate_kill_switch
                        activate_kill_switch()
                        st.session_state.kill_switch_active = True
                        st.session_state.ks_confirm_activate = False
                        _append_log("Kill Switch 활성화됨")
                        st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")
            with cc2:
                if st.button("\u274c 취소", use_container_width=True, key="ks_act_cancel"):
                    st.session_state.ks_confirm_activate = False
                    st.rerun()
    else:
        # ── 해제 플로우 ──
        if not st.session_state.ks_confirm_deactivate:
            if st.button("Kill Switch 해제", use_container_width=True, key="ks_deact"):
                st.session_state.ks_confirm_deactivate = True
                st.rerun()
        else:
            st.info("Kill Switch를 해제하면 거래가 다시 시작됩니다. 계속하시겠습니까?")
            cc1, cc2 = st.columns(2)
            with cc1:
                if st.button("\u2705 확인 — 해제", use_container_width=True, key="ks_deact_confirm"):
                    try:
                        from dashboard.services.bot_service import deactivate_kill_switch
                        deactivate_kill_switch()
                        st.session_state.kill_switch_active = False
                        st.session_state.ks_confirm_deactivate = False
                        _append_log("Kill Switch 해제됨")
                        st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")
            with cc2:
                if st.button("\u274c 취소", use_container_width=True, key="ks_deact_cancel"):
                    st.session_state.ks_confirm_deactivate = False
                    st.rerun()

    # ── 실행 로그 ──
    st.divider()
    with st.expander("실행 로그", expanded=bool(st.session_state.bot_log)):
        if st.session_state.bot_log:
            show_all = st.checkbox("전체 로그 보기", value=False, key="log_show_all")
            if show_all:
                log_text = "\n".join(st.session_state.bot_log)
            else:
                log_text = "\n".join(st.session_state.bot_log[-100:])
            st.code(log_text, language="text")
        else:
            st.info("아직 실행 로그가 없습니다.")

        if st.button("로그 지우기"):
            st.session_state.bot_log = []
            st.rerun()


def _run_strategy_once() -> None:
    """전략 1회 실행"""
    with st.spinner("전략 실행 중..."):
        try:
            from dashboard.services.bot_service import run_once
            log = run_once()
            _append_log(f"[전략 실행]\n{log}")
            st.success("전략 실행 완료!")
        except Exception as e:
            msg = f"전략 실행 오류: {e}"
            _append_log(msg)
            st.error(msg)


def _collect_data() -> None:
    """데이터 수집"""
    with st.spinner("데이터 수집 중..."):
        try:
            from dashboard.services.bot_service import collect_data
            log = collect_data()
            _append_log(f"[데이터 수집]\n{log}")
            st.success("데이터 수집 완료!")
        except Exception as e:
            msg = f"데이터 수집 오류: {e}"
            _append_log(msg)
            st.error(msg)


def _show_status() -> None:
    """전략 상태 조회"""
    try:
        from dashboard.services.bot_service import get_kill_switch_status
        from dashboard.services.config_service import load_settings

        config = load_settings()
        strategies = config.get("strategies", {})

        status_lines = []
        for name, cfg in strategies.items():
            enabled = cfg.get("enabled", False)
            status_lines.append(f"  {name}: {'활성' if enabled else '비활성'}")

        ks = get_kill_switch_status()
        status_lines.append(f"  Kill Switch: {'ON' if ks else 'OFF'}")

        status_text = "\n".join(status_lines)
        _append_log(f"[상태 조회]\n{status_text}")
        st.info(f"전략 상태:\n{status_text}")
    except Exception as e:
        st.error(f"상태 조회 오류: {e}")


def _append_log(msg: str) -> None:
    """세션 로그에 타임스탬프 + 메시지 추가"""
    ts = datetime.now().strftime("%H:%M:%S")
    st.session_state.bot_log.append(f"[{ts}] {msg}")
