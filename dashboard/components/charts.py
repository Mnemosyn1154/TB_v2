from __future__ import annotations

"""Plotly 차트 헬퍼 함수"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go

# ── 색상 상수 ──
COLOR_PRIMARY = "#1f77b4"
COLOR_DANGER = "#dc3545"
COLOR_SUCCESS = "#28a745"

# ── 다크 테마 공통 레이아웃 ──
_DARK_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
)


def equity_curve_chart(equity: pd.Series) -> go.Figure:
    """에퀴티 커브 라인 차트"""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=equity.index,
        y=equity.values,
        mode="lines",
        name="자산",
        line=dict(color=COLOR_PRIMARY, width=2),
        fill="tozeroy",
        fillcolor="rgba(31,119,180,0.08)",
    ))
    fig.update_layout(
        title="에퀴티 커브",
        xaxis_title="날짜",
        yaxis_title="자산 (원)",
        yaxis_tickformat=",",
        **_DARK_LAYOUT,
        height=420,
        margin=dict(l=60, r=20, t=50, b=40),
    )
    return fig


def drawdown_chart(equity: pd.Series) -> go.Figure:
    """드로다운 영역 차트"""
    cummax = equity.cummax()
    drawdown = (equity - cummax) / cummax * 100

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=drawdown.index,
        y=drawdown.values,
        fill="tozeroy",
        fillcolor="rgba(220,53,69,0.25)",
        line=dict(color=COLOR_DANGER, width=1),
        name="드로다운 (%)",
    ))
    fig.update_layout(
        title="드로다운",
        xaxis_title="날짜",
        yaxis_title="드로다운 (%)",
        **_DARK_LAYOUT,
        height=300,
        margin=dict(l=60, r=20, t=50, b=40),
    )
    return fig


def monthly_heatmap(monthly_df: pd.DataFrame) -> go.Figure:
    """월별 수익률 히트맵"""
    # '연합계' 컬럼 제외
    cols = [c for c in monthly_df.columns if c != "연합계"]
    data = monthly_df[cols] * 100  # → %

    text_vals = [
        [f"{v:+.1f}%" if not np.isnan(v) else "" for v in row]
        for row in data.values
    ]

    fig = go.Figure(data=go.Heatmap(
        z=data.values,
        x=data.columns.tolist(),
        y=[str(y) for y in data.index],
        text=text_vals,
        texttemplate="%{text}",
        textfont=dict(color="white"),
        colorscale="RdYlGn",
        zmid=0,
        colorbar=dict(title="%"),
    ))
    fig.update_layout(
        title="월별 수익률 (%)",
        **_DARK_LAYOUT,
        height=250,
        margin=dict(l=60, r=20, t=50, b=40),
    )
    return fig


def multi_equity_curve_chart(
    curves: dict[str, pd.Series],
    normalize: bool = True,
) -> go.Figure:
    """페어별 에퀴티 커브 오버레이 차트.

    Args:
        curves: {페어이름: equity_curve} 딕셔너리
        normalize: True면 시작값=100 기준 정규화 (비교 용이)
    """
    colors = [
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
        "#9467bd", "#8c564b", "#e377c2", "#7f7f7f",
    ]
    fig = go.Figure()

    for idx, (name, eq) in enumerate(curves.items()):
        if eq is None or len(eq) < 2:
            continue
        y = eq / eq.iloc[0] * 100 if normalize else eq
        color = colors[idx % len(colors)]
        fig.add_trace(go.Scatter(
            x=eq.index,
            y=y.values,
            mode="lines",
            name=name,
            line=dict(color=color, width=2),
        ))

    y_label = "수익률 (시작=100)" if normalize else "자산 (원)"
    fig.update_layout(
        title="페어별 에퀴티 커브 비교",
        xaxis_title="날짜",
        yaxis_title=y_label,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        **_DARK_LAYOUT,
        height=420,
        margin=dict(l=60, r=20, t=50, b=40),
    )
    return fig


def pair_comparison_bar_chart(metrics_dict: dict[str, dict]) -> go.Figure:
    """페어별 핵심 지표 비교 바 차트.

    Args:
        metrics_dict: {페어이름: metrics} 딕셔너리
    """
    pair_names = list(metrics_dict.keys())
    total_returns = [metrics_dict[p].get("total_return", 0) * 100 for p in pair_names]
    sharpes = [metrics_dict[p].get("sharpe_ratio", 0) for p in pair_names]
    mdds = [metrics_dict[p].get("mdd", 0) * 100 for p in pair_names]

    from plotly.subplots import make_subplots

    fig = make_subplots(
        rows=1, cols=3,
        subplot_titles=["총수익률 (%)", "샤프 비율", "MDD (%)"],
        horizontal_spacing=0.08,
    )

    colors = ["#28a745" if v > 0 else "#dc3545" for v in total_returns]
    fig.add_trace(go.Bar(x=pair_names, y=total_returns, marker_color=colors, name="수익률"), row=1, col=1)

    colors_s = ["#1f77b4" if v > 0 else "#dc3545" for v in sharpes]
    fig.add_trace(go.Bar(x=pair_names, y=sharpes, marker_color=colors_s, name="샤프"), row=1, col=2)

    fig.add_trace(go.Bar(x=pair_names, y=mdds, marker_color="#dc3545", name="MDD"), row=1, col=3)

    fig.update_layout(
        showlegend=False,
        **_DARK_LAYOUT,
        height=300,
        margin=dict(l=40, r=20, t=50, b=40),
    )
    return fig


def pnl_distribution_chart(pnl_values: list[float]) -> go.Figure:
    """거래 손익 분포 히스토그램"""
    fig = go.Figure()
    gains = [v for v in pnl_values if v > 0]
    losses = [v for v in pnl_values if v <= 0]
    if gains:
        fig.add_trace(go.Histogram(
            x=gains, nbinsx=15, name="수익",
            marker_color=COLOR_SUCCESS, opacity=0.8,
        ))
    if losses:
        fig.add_trace(go.Histogram(
            x=losses, nbinsx=15, name="손실",
            marker_color=COLOR_DANGER, opacity=0.8,
        ))
    fig.update_layout(
        title="거래 손익 분포",
        xaxis_title="손익 (원)",
        yaxis_title="건수",
        xaxis_tickformat=",",
        barmode="overlay",
        **_DARK_LAYOUT,
        height=350,
        margin=dict(l=60, r=20, t=50, b=40),
    )
    return fig
