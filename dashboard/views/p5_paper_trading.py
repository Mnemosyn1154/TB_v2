from __future__ import annotations

"""Page 5: 모의 거래 (Paper Trading)

KIS API 모의투자 서버를 활용한 포워드 테스트 페이지.
전략 시그널을 미리보고, 수동으로 실행/스킵할 수 있습니다.
live_trading: false 상태에서 동작하며, true로 변경하면 실거래로 전환됩니다.
"""
import pandas as pd
import streamlit as st

from dashboard.services.paper_trading_service import (
    create_session,
    get_active_session,
    stop_session,
    generate_signals_dry_run,
    execute_signal,
    execute_all_signals,
    get_portfolio,
    get_paper_trades,
    get_session_history,
    get_session_trade_summary,
)


def render() -> None:
    st.header("📝 모의 거래")

    # 거래 모드 표시
    try:
        from src.core.config import get_config
        cfg = get_config()
        is_live = cfg.get("kis", {}).get("live_trading", False)
        if is_live:
            st.error("⚠️ 현재 **실거래** 모드입니다. 주문이 실제로 체결됩니다!")
        else:
            st.info(
                "모드: **모의투자** (KIS API 모의투자 서버 사용) | "
                "실거래 전환: `settings.yaml` → `live_trading: true`"
            )
    except Exception:
        st.warning("설정 로드 실패")

    session = get_active_session()

    if session:
        _render_active_session(session)
    else:
        _render_no_session()


# ──────────────────────────────────────────────
# 세션 없을 때
# ──────────────────────────────────────────────

def _render_no_session() -> None:
    """새 세션 시작 UI"""
    st.info("활성 모의 거래 세션이 없습니다. 새 세션을 시작하세요.")

    if st.button("새 세션 시작", type="primary", use_container_width=False):
        with st.spinner("세션 생성 중..."):
            create_session()
        st.rerun()

    # 과거 세션 이력
    history = get_session_history()
    if history:
        st.divider()
        st.subheader("과거 세션 이력")
        df = pd.DataFrame(history)
        col_rename = {
            "session_id": "세션 ID",
            "start_date": "시작일",
            "end_date": "종료일",
            "status": "상태",
            "strategy_names": "전략",
        }
        df = df.rename(columns=col_rename)
        st.dataframe(df, use_container_width=True)


# ──────────────────────────────────────────────
# 활성 세션
# ──────────────────────────────────────────────

def _render_active_session(session: dict) -> None:
    """활성 세션 대시보드"""

    # ── 세션 정보 ──
    _render_session_info(session)

    # ── 시그널 미리보기 ──
    st.divider()
    _render_signal_preview(session)

    # ── KIS API 포트폴리오 (모의투자 잔고) ──
    st.divider()
    _render_portfolio()

    # ── 거래 이력 ──
    st.divider()
    _render_trade_history(session["session_id"])

    # ── 세션 종료 ──
    st.divider()
    if st.button("세션 종료", type="secondary"):
        stop_session(session["session_id"])
        st.session_state.paper_signals = []
        st.rerun()


def _render_session_info(session: dict) -> None:
    """세션 정보 표시"""
    strategies = session.get("strategy_names", [])
    summary = get_session_trade_summary(session["session_id"])

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("세션 ID", session["session_id"])
    with c2:
        st.metric("활성 전략", f"{len(strategies)}개")
    with c3:
        st.metric("총 거래", f"{summary['total_trades']}건")
    with c4:
        st.metric("매수/매도", f"{summary['buy_count']} / {summary['sell_count']}")

    st.caption(
        f"시작: {session['start_date'][:19]} | "
        f"전략: {', '.join(strategies)}"
    )


def _render_signal_preview(session: dict) -> None:
    """시그널 생성 및 미리보기 (포워드 테스트 핵심)"""
    st.subheader("시그널 미리보기")

    col_gen, col_exec_all = st.columns([1, 1])
    with col_gen:
        if st.button("시그널 생성", type="primary", use_container_width=True):
            with st.spinner("전략 시그널 생성 중... (DB 데이터 기반)"):
                signals = generate_signals_dry_run()
                st.session_state.paper_signals = signals
                if not signals:
                    st.info("현재 생성된 시그널이 없습니다.")

    signals = st.session_state.get("paper_signals", [])

    with col_exec_all:
        if signals and st.button("전체 실행", use_container_width=True):
            with st.spinner("전체 시그널 실행 중... (KIS API 주문)"):
                results = execute_all_signals(session["session_id"], signals)
                errors = [r for r in results if "error" in r]
                success = [r for r in results if r.get("success")]
                if success:
                    st.success(f"{len(success)}건 주문 전송 완료")
                if errors:
                    for e in errors:
                        st.error(e["error"])
                st.session_state.paper_signals = []
                st.rerun()

    if not signals:
        st.caption("'시그널 생성' 버튼을 눌러 현재 전략 시그널을 확인하세요.")
        return

    st.success(f"{len(signals)}건의 시그널이 생성되었습니다.")

    for i, sig in enumerate(signals):
        signal_type = sig["signal"]
        emoji = "🟢" if signal_type == "BUY" else "🔴"

        with st.container():
            col_info, col_action = st.columns([3, 1])

            with col_info:
                st.markdown(
                    f"{emoji} **{sig['code']}** ({sig['market']}) — "
                    f"**{signal_type}** | 전략: {sig['strategy']}"
                )
                st.caption(f"사유: {sig['reason']}")

            with col_action:
                c_exec, c_skip = st.columns(2)
                with c_exec:
                    if st.button("실행", key=f"exec_{i}", type="primary"):
                        with st.spinner("KIS API 주문 전송 중..."):
                            result = execute_signal(session["session_id"], sig)
                        if "error" in result:
                            st.error(result["error"])
                        else:
                            st.success(
                                f"{result['side']}: {result['code']} "
                                f"[{result['mode']}]"
                            )
                            st.session_state.paper_signals = [
                                s for j, s in enumerate(signals) if j != i
                            ]
                            st.rerun()
                with c_skip:
                    if st.button("스킵", key=f"skip_{i}"):
                        st.session_state.paper_signals = [
                            s for j, s in enumerate(signals) if j != i
                        ]
                        st.rerun()

            st.divider()


def _render_portfolio() -> None:
    """KIS API 모의투자 잔고 표시"""
    st.subheader("모의투자 포트폴리오 (KIS API)")

    if st.button("잔고 조회", use_container_width=False):
        with st.spinner("KIS API에서 잔고 조회 중..."):
            st.session_state.paper_portfolio = get_portfolio()

    data = st.session_state.get("paper_portfolio")
    if data is None:
        st.caption("'잔고 조회' 버튼을 눌러 모의투자 잔고를 확인하세요.")
        return

    if data.get("error"):
        st.warning(f"API 연결 실패: {data['error']}")
        st.info("KIS API 인증 정보(.env)를 확인하세요.")
        return

    # KPI
    risk = data.get("risk", {})
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        eq = risk.get("total_equity", 0)
        st.metric("총 자산", f"{eq:,.0f}")
    with c2:
        cash = risk.get("cash", 0)
        st.metric("현금", f"{cash:,.0f}")
    with c3:
        pos_count = risk.get("positions_count", 0)
        st.metric("포지션 수", f"{pos_count}")
    with c4:
        st.metric("드로다운", risk.get("drawdown", "0.0%"))

    # 포지션 테이블
    kr_positions = data.get("kr", {}).get("positions", [])
    us_positions = data.get("us", {}).get("positions", [])
    all_positions = kr_positions + us_positions

    if all_positions:
        df = pd.DataFrame(all_positions)
        col_rename = {
            "code": "종목코드", "name": "종목명", "quantity": "수량",
            "avg_price": "평균단가", "current_price": "현재가",
            "profit_pct": "수익률(%)", "profit_amt": "평가손익",
            "market": "시장",
        }
        df = df.rename(columns=col_rename)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("보유 포지션이 없습니다.")


def _render_trade_history(session_id: str) -> None:
    """거래 이력 테이블"""
    st.subheader("세션 거래 이력")

    trades_df = get_paper_trades(session_id)
    if trades_df.empty:
        st.info("아직 거래 기록이 없습니다.")
        return

    col_rename = {
        "strategy": "전략",
        "code": "종목",
        "market": "시장",
        "side": "방향",
        "quantity": "수량",
        "price": "가격",
        "reason": "사유",
        "timestamp": "시간",
    }
    display_df = trades_df.rename(columns=col_rename)
    st.dataframe(display_df, use_container_width=True)
