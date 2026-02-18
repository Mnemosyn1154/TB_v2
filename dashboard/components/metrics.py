from __future__ import annotations

"""KPI 메트릭 카드 헬퍼"""
import streamlit as st


def render_backtest_kpis(m: dict) -> None:
    """백테스트 핵심 KPI를 6열 메트릭 카드로 표시"""
    c1, c2, c3, c4, c5, c6 = st.columns(6)

    with c1:
        v = m["total_return"]
        st.metric("총수익률", f"{v:+.1%}", delta=f"{v:+.1%}")
    with c2:
        v = m["cagr"]
        st.metric("CAGR", f"{v:+.1%}", delta=f"{v:+.1%}")
    with c3:
        v = m["sharpe_ratio"]
        st.metric("샤프 비율", f"{v:.2f}", delta=f"{v:.2f}")
    with c4:
        v = m["mdd"]
        st.metric("MDD", f"{v:+.1%}", delta=f"{v:+.1%}")
    with c5:
        v = m["win_rate"]
        st.metric("승률", f"{v:.1%}", delta=f"{v:.0%}")
    with c6:
        pf = m["profit_factor"]
        if pf == 0:
            pf_str = "0.00 (수익 없음)"
        elif pf > 100:
            pf_str = "∞ (손실 없음)"
        else:
            pf_str = f"{pf:.2f}"
        st.metric("손익비", pf_str, delta=f"{pf:.2f}" if pf <= 100 else "∞")


def render_pair_comparison_table(metrics_dict: dict[str, dict]) -> None:
    """페어별 백테스트 결과 비교 테이블 표시.

    Args:
        metrics_dict: {페어이름: metrics} 딕셔너리
    """
    import pandas as pd

    rows = []
    for pair_name, m in metrics_dict.items():
        rows.append({
            "페어": pair_name,
            "수익률": f"{m.get('total_return', 0):+.1%}",
            "CAGR": f"{m.get('cagr', 0):+.1%}",
            "샤프": f"{m.get('sharpe_ratio', 0):.2f}",
            "MDD": f"{m.get('mdd', 0):+.1%}",
            "거래수": m.get("total_trades", 0),
            "승률": f"{m.get('win_rate', 0):.1%}",
            "손익비": f"{m.get('profit_factor', 0):.2f}" if m.get("profit_factor", 0) < 100 else "INF",
            "소르티노": f"{m.get('sortino_ratio', 0):.2f}",
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_portfolio_kpis(risk: dict) -> None:
    """포트폴리오 KPI를 4열 메트릭 카드로 표시"""
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        eq = risk.get("total_equity", 0)
        st.metric("총 자산", f"{eq:,.0f}")
    with c2:
        cash = risk.get("cash", 0)
        st.metric("현금", f"{cash:,.0f}")
    with c3:
        st.metric("드로다운", risk.get("drawdown", "0.0%"))
    with c4:
        ks = risk.get("kill_switch", False)
        st.metric("Kill Switch", "ON" if ks else "OFF")
