from __future__ import annotations

"""거래 내역 테이블 포맷팅"""
import pandas as pd
import streamlit as st

from src.backtest.engine import Trade


def render_trade_table(trades: list[Trade]) -> None:
    """거래 리스트를 데이터프레임 테이블로 표시"""
    if not trades:
        st.info("거래 내역이 없습니다.")
        return

    rows = []
    for t in trades:
        is_sell = t.side == "SELL"
        rows.append({
            "날짜": t.date,
            "전략": t.strategy,
            "종목": t.code,
            "시장": t.market,
            "방향": t.side,
            "수량": t.quantity,
            "가격": f"{t.price:,.2f}",
            "수수료": f"{t.commission:,.0f}",
            "손익": f"{t.pnl:+,.0f}" if is_sell else "",
            "수익률 (%)": f"{t.pnl_pct:+.2f}" if is_sell else "",
            "보유일": str(t.holding_days) if is_sell else "",
        })

    df = pd.DataFrame(rows)
    st.dataframe(
        df,
        use_container_width=True,
        height=min(400, 40 + 35 * len(rows)),
    )
