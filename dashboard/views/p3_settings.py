from __future__ import annotations

"""Page 3: 전략 설정 / 파라미터 조정"""
from copy import deepcopy
from datetime import date

import streamlit as st

from dashboard.services.config_service import load_settings, parse_date as _parse_date, save_settings


def render() -> None:
    st.header("\u2699\ufe0f 전략 설정")

    # ── 설정 로드 ──
    if st.session_state.config_cache is None:
        try:
            st.session_state.config_cache = load_settings()
        except Exception as e:
            st.error(f"설정 파일 로드 실패: {e}")
            return

    config = deepcopy(st.session_state.config_cache)
    strategies = config.get("strategies", {})
    risk = config.get("risk", {})
    bt = config.get("backtest", {})
    kis = config.get("kis", {})
    notifications = config.get("notifications", {})

    # 삭제 확인용 세션 상태 초기화
    for key in ["sa_delete_confirm", "qf_delete_confirm"]:
        if key not in st.session_state:
            st.session_state[key] = None

    # ── 탭 구성 ──
    tab_sa, tab_dm, tab_qf, tab_risk, tab_bt, tab_api = st.tabs([
        "StatArb (차익거래)", "DualMomentum (듀얼 모멘텀)", "QuantFactor (퀀트 팩터)",
        "리스크 관리", "백테스트", "API / 알림",
    ])

    # ────────── StatArb ──────────
    with tab_sa:
        sa = strategies.get("stat_arb", {})
        sa["enabled"] = st.checkbox("활성화", value=sa.get("enabled", True), key="sa_enabled")

        st.subheader("페어 목록")
        pairs = sa.get("pairs", [])
        if pairs:
            for i, pair in enumerate(pairs):
                label = (f"{pair.get('name', '?')} [{pair.get('market', '?')}] "
                         f"— {pair.get('stock_a', '?')} / {pair.get('stock_b', '?')}")
                with st.expander(label, expanded=False):
                    pc1, pc2 = st.columns(2)
                    with pc1:
                        pair["name"] = st.text_input(
                            "페어 이름", value=pair.get("name", ""),
                            key=f"sa_pair_name_{i}",
                        )
                        pair["stock_a"] = st.text_input(
                            "종목 A 코드", value=pair.get("stock_a", ""),
                            key=f"sa_pair_a_{i}",
                        )
                        pair["hedge_etf"] = st.text_input(
                            "헤지 ETF 코드", value=pair.get("hedge_etf", ""),
                            key=f"sa_pair_hedge_{i}",
                        )
                    with pc2:
                        market_opts = ["KR", "US"]
                        pair["market"] = st.selectbox(
                            "시장", options=market_opts,
                            index=market_opts.index(pair.get("market", "KR"))
                            if pair.get("market") in market_opts else 0,
                            key=f"sa_pair_market_{i}",
                        )
                        pair["stock_b"] = st.text_input(
                            "종목 B 코드", value=pair.get("stock_b", ""),
                            key=f"sa_pair_b_{i}",
                        )

                    # 미국 종목 거래소 선택
                    if pair["market"] == "US":
                        exc1, exc2, exc3 = st.columns(3)
                        exchange_opts = ["NAS", "NYS"]
                        with exc1:
                            pair["exchange_a"] = st.selectbox(
                                "종목 A 거래소", options=exchange_opts,
                                index=exchange_opts.index(pair.get("exchange_a", "NAS"))
                                if pair.get("exchange_a") in exchange_opts else 0,
                                key=f"sa_pair_exch_a_{i}",
                            )
                        with exc2:
                            pair["exchange_b"] = st.selectbox(
                                "종목 B 거래소", options=exchange_opts,
                                index=exchange_opts.index(pair.get("exchange_b", "NAS"))
                                if pair.get("exchange_b") in exchange_opts else 0,
                                key=f"sa_pair_exch_b_{i}",
                            )
                        with exc3:
                            pair["exchange_hedge"] = st.selectbox(
                                "헤지 ETF 거래소", options=exchange_opts,
                                index=exchange_opts.index(pair.get("exchange_hedge", "NAS"))
                                if pair.get("exchange_hedge") in exchange_opts else 0,
                                key=f"sa_pair_exch_h_{i}",
                            )

                    # 삭제 (2단계 확인 — 이름 기반)
                    pair_name = pair.get("name", "")
                    if st.session_state.sa_delete_confirm == pair_name:
                        st.warning(f"'{pair_name}' 페어를 삭제하시겠습니까?")
                        dc1, dc2 = st.columns(2)
                        with dc1:
                            if st.button("확인 — 삭제", key=f"sa_del_yes_{i}", type="primary"):
                                sa["pairs"] = [
                                    p for p in pairs if p.get("name") != pair_name
                                ]
                                strategies["stat_arb"] = sa
                                config["strategies"] = strategies
                                save_settings(config)
                                st.session_state.config_cache = config
                                st.session_state.sa_delete_confirm = None
                                st.rerun()
                        with dc2:
                            if st.button("취소", key=f"sa_del_no_{i}"):
                                st.session_state.sa_delete_confirm = None
                                st.rerun()
                    else:
                        if st.button("페어 삭제", key=f"sa_del_{i}"):
                            st.session_state.sa_delete_confirm = pair_name
                            st.rerun()
        else:
            st.info("설정된 페어가 없습니다.")

        # 새 페어 추가
        st.subheader("새 페어 추가")
        nc1, nc2 = st.columns(2)
        with nc1:
            new_name = st.text_input("페어 이름", key="sa_new_name", placeholder="예: AAPL_MSFT")
            new_a = st.text_input("종목 A 코드", key="sa_new_a", placeholder="예: AAPL")
            new_hedge = st.text_input("헤지 ETF", key="sa_new_hedge", placeholder="예: PSQ")
        with nc2:
            new_market = st.selectbox("시장", options=["KR", "US"], key="sa_new_market")
            new_b = st.text_input("종목 B 코드", key="sa_new_b", placeholder="예: MSFT")

        # 미국 종목 거래소 선택
        if new_market == "US":
            exc1, exc2, exc3 = st.columns(3)
            with exc1:
                new_exchange_a = st.selectbox(
                    "종목 A 거래소", options=["NAS", "NYS"], key="sa_new_exch_a",
                )
            with exc2:
                new_exchange_b = st.selectbox(
                    "종목 B 거래소", options=["NAS", "NYS"], key="sa_new_exch_b",
                )
            with exc3:
                new_exchange_hedge = st.selectbox(
                    "헤지 ETF 거래소", options=["NAS", "NYS"], key="sa_new_exch_h",
                )
        else:
            new_exchange_a = new_exchange_b = new_exchange_hedge = ""

        if st.button("페어 추가", key="sa_add_pair"):
            errors = _validate_pair(new_name, new_market, new_a, new_b, new_hedge, pairs)
            if errors:
                for e in errors:
                    st.error(e)
            else:
                new_pair = {
                    "name": new_name.strip(),
                    "market": new_market,
                    "stock_a": new_a.strip(),
                    "stock_b": new_b.strip(),
                    "hedge_etf": new_hedge.strip(),
                }
                if new_market == "US":
                    new_pair["exchange_a"] = new_exchange_a
                    new_pair["exchange_b"] = new_exchange_b
                    new_pair["exchange_hedge"] = new_exchange_hedge
                pairs.append(new_pair)
                sa["pairs"] = pairs
                strategies["stat_arb"] = sa
                config["strategies"] = strategies
                save_settings(config)
                st.session_state.config_cache = config
                st.rerun()

        st.subheader("시그널 파라미터")
        c1, c2 = st.columns(2)
        with c1:
            sa["lookback_window"] = st.number_input(
                "롤링 윈도우 (일)", value=sa.get("lookback_window", 60),
                min_value=10, max_value=252, key="sa_lookback",
                help="공적분 및 Z-Score 계산에 사용되는 롤링 윈도우 (60~120일 권장)",
            )
            sa["entry_z_score"] = st.number_input(
                "진입 Z-Score", value=float(sa.get("entry_z_score", 2.0)),
                min_value=0.5, max_value=5.0, step=0.1, key="sa_entry_z",
                help="스프레드가 이 값을 초과하면 진입 (1.5~2.5 권장)",
            )
        with c2:
            sa["exit_z_score"] = st.number_input(
                "청산 Z-Score", value=float(sa.get("exit_z_score", 0.5)),
                min_value=0.0, max_value=3.0, step=0.1, key="sa_exit_z",
                help="스프레드가 평균 회귀하여 이 값 이하이면 청산 (0.3~1.0 권장)",
            )
            sa["stop_loss_z_score"] = st.number_input(
                "손절 Z-Score", value=float(sa.get("stop_loss_z_score", 3.5)),
                min_value=1.0, max_value=10.0, step=0.1, key="sa_stop_z",
                help="스프레드 발산 시 손절 기준 (3.0~4.0 권장)",
            )

        c3, c4 = st.columns(2)
        with c3:
            sa["recalc_beta_days"] = st.number_input(
                "베타 재계산 주기 (일)", value=sa.get("recalc_beta_days", 30),
                min_value=5, max_value=120, key="sa_beta_days",
                help="헤지 비율(β) 재계산 주기 (20~60일 권장)",
            )
        with c4:
            sa["coint_pvalue"] = st.number_input(
                "공적분 p-value 임계값", value=float(sa.get("coint_pvalue", 0.05)),
                min_value=0.001, max_value=0.20, step=0.005, format="%.3f",
                key="sa_coint_pvalue",
                help="Engle-Granger 공적분 검정의 유의수준 (낮을수록 엄격)",
            )
        strategies["stat_arb"] = sa

    # ────────── DualMomentum ──────────
    with tab_dm:
        dm = strategies.get("dual_momentum", {})
        dm["enabled"] = st.checkbox("활성화", value=dm.get("enabled", True), key="dm_enabled")

        c1, c2 = st.columns(2)
        with c1:
            dm["lookback_months"] = st.number_input(
                "룩백 기간 (개월)", value=dm.get("lookback_months", 12),
                min_value=1, max_value=36, key="dm_lookback",
                help="모멘텀 비교 기간 (6~12개월 권장)",
            )
            dm["rebalance_day"] = st.number_input(
                "리밸런싱 일 (매월 N번째 거래일)",
                value=dm.get("rebalance_day", 1),
                min_value=1, max_value=25, key="dm_rebal",
                help="매월 이 번째 거래일에 리밸런싱 실행",
            )
        with c2:
            dm["risk_free_rate"] = st.number_input(
                "무위험수익률 (연)", value=float(dm.get("risk_free_rate", 0.04)),
                min_value=0.0, max_value=0.2, step=0.005, format="%.3f",
                key="dm_rf",
                help="무위험 수익률 (절대 모멘텀 기준선)",
            )

        st.subheader("ETF 설정")
        ec1, ec2 = st.columns(2)
        with ec1:
            dm["kr_etf"] = st.text_input(
                "KR ETF (예: KODEX 200)",
                value=dm.get("kr_etf", "069500"), key="dm_kr_etf",
            )
            dm["safe_kr_etf"] = st.text_input(
                "Safe KR ETF (채권)",
                value=dm.get("safe_kr_etf", "148070"), key="dm_safe_kr_etf",
            )
        with ec2:
            dm["us_etf"] = st.text_input(
                "US ETF (예: SPY)",
                value=dm.get("us_etf", "SPY"), key="dm_us_etf",
            )
            dm_us_exch_opts = ["NYS", "NAS"]
            dm["us_etf_exchange"] = st.selectbox(
                "US ETF 거래소", options=dm_us_exch_opts,
                index=dm_us_exch_opts.index(dm.get("us_etf_exchange", "NYS"))
                if dm.get("us_etf_exchange") in dm_us_exch_opts else 0,
                key="dm_us_etf_exch",
            )
            dm["safe_us_etf"] = st.text_input(
                "Safe US ETF (채권)",
                value=dm.get("safe_us_etf", "SHY"), key="dm_safe_us_etf",
            )
            dm["safe_us_etf_exchange"] = st.selectbox(
                "Safe US ETF 거래소", options=dm_us_exch_opts,
                index=dm_us_exch_opts.index(dm.get("safe_us_etf_exchange", "NYS"))
                if dm.get("safe_us_etf_exchange") in dm_us_exch_opts else 0,
                key="dm_safe_us_etf_exch",
            )
        strategies["dual_momentum"] = dm

    # ────────── QuantFactor ──────────
    with tab_qf:
        qf = strategies.get("quant_factor", {})
        qf["enabled"] = st.checkbox("활성화", value=qf.get("enabled", False), key="qf_enabled")

        c1, c2 = st.columns(2)
        with c1:
            qf["top_n"] = st.number_input(
                "상위 N종목 보유", value=int(qf.get("top_n", 20)),
                min_value=5, max_value=50, key="qf_topn",
            )
            qf["rebalance_months"] = st.number_input(
                "리밸런싱 주기 (월)", value=int(qf.get("rebalance_months", 1)),
                min_value=1, max_value=12, key="qf_rebal",
            )
            qf["min_data_days"] = st.number_input(
                "최소 필요 데이터 (일)", value=int(qf.get("min_data_days", 60)),
                min_value=20, max_value=252, key="qf_mindata",
            )
        with c2:
            qf["lookback_days"] = st.number_input(
                "Value 룩백 (거래일)", value=int(qf.get("lookback_days", 252)),
                min_value=60, max_value=504, key="qf_lookback",
            )
            qf["momentum_days"] = st.number_input(
                "Momentum 룩백 (거래일)", value=int(qf.get("momentum_days", 126)),
                min_value=20, max_value=252, key="qf_momentum",
            )
            qf["volatility_days"] = st.number_input(
                "Quality 변동성 윈도우 (일)", value=int(qf.get("volatility_days", 60)),
                min_value=10, max_value=120, key="qf_vol",
            )

        st.subheader("팩터 가중치")
        weights = qf.get("weights", {})
        wc1, wc2, wc3 = st.columns(3)
        with wc1:
            weights["value"] = st.number_input(
                "Value (가치)", value=float(weights.get("value", 0.3)),
                min_value=0.0, max_value=1.0, step=0.05, format="%.2f", key="qf_wv",
                help="가치 팩터 비중 (PER, PBR 기반)",
            )
        with wc2:
            weights["quality"] = st.number_input(
                "Quality (퀄리티)", value=float(weights.get("quality", 0.3)),
                min_value=0.0, max_value=1.0, step=0.05, format="%.2f", key="qf_wq",
                help="퀄리티 팩터 비중 (ROE, 변동성 기반)",
            )
        with wc3:
            weights["momentum"] = st.number_input(
                "Momentum (모멘텀)", value=float(weights.get("momentum", 0.4)),
                min_value=0.0, max_value=1.0, step=0.05, format="%.2f", key="qf_wm",
                help="모멘텀 팩터 비중 (과거 수익률 기반)",
            )
        # 가중치 합계 실시간 표시
        weight_total = weights["value"] + weights["quality"] + weights["momentum"]
        if abs(weight_total - 1.0) > 0.05:
            st.warning(f"가중치 합계: {weight_total:.2f} (1.0이 되어야 합니다)")
        else:
            st.caption(f"가중치 합계: {weight_total:.2f}")
        qf["weights"] = weights

        st.subheader("유니버스 종목")
        universe = qf.get("universe_codes", [])
        kr_codes = [u for u in universe if u.get("market") == "KR"]
        us_codes = [u for u in universe if u.get("market") == "US"]
        st.text(f"  KR: {len(kr_codes)}종목 | US: {len(us_codes)}종목 (총 {len(universe)}종목)")

        # 종목 목록 표시
        market_filter = st.selectbox(
            "시장 필터", ["전체", "KR", "US"], key="qf_market_filter",
        )
        with st.expander(f"종목 목록 ({len(universe)}종목)", expanded=False):
            if universe:
                import pandas as pd
                df_uni = pd.DataFrame(universe)
                display_cols = [c for c in ["code", "name", "market", "exchange"] if c in df_uni.columns]
                df_display = df_uni[display_cols].copy()
                col_names = {"code": "종목코드", "name": "종목명", "market": "시장", "exchange": "거래소"}
                df_display.columns = [col_names.get(c, c) for c in display_cols]
                if market_filter != "전체":
                    df_display = df_display[df_display["시장"] == market_filter]
                st.dataframe(df_display, use_container_width=True, hide_index=True)
            else:
                st.info("유니버스에 종목이 없습니다.")

        # 종목 삭제 (2단계 확인)
        st.markdown("**종목 삭제**")
        if universe:
            delete_options = [
                f"{u['code']} - {u.get('name', '')} [{u.get('market', '')}]"
                for u in universe
            ]
            selected_delete = st.selectbox(
                "삭제할 종목 선택", options=delete_options, key="qf_del_select",
            )
            del_idx = delete_options.index(selected_delete)
            del_code = universe[del_idx].get("code", "")

            if st.session_state.qf_delete_confirm == del_code:
                st.warning(f"'{selected_delete}' 종목을 삭제하시겠습니까?")
                qdc1, qdc2 = st.columns(2)
                with qdc1:
                    if st.button("확인 — 삭제", key="qf_del_yes", type="primary"):
                        universe = [
                            u for u in universe if u.get("code") != del_code
                        ]
                        qf["universe_codes"] = universe
                        strategies["quant_factor"] = qf
                        config["strategies"] = strategies
                        save_settings(config)
                        st.session_state.config_cache = config
                        st.session_state.qf_delete_confirm = None
                        st.rerun()
                with qdc2:
                    if st.button("취소", key="qf_del_no"):
                        st.session_state.qf_delete_confirm = None
                        st.rerun()
            else:
                if st.button("선택 종목 삭제", key="qf_del_btn"):
                    st.session_state.qf_delete_confirm = del_code
                    st.rerun()

        # 종목 추가
        st.markdown("**종목 추가**")
        ac1, ac2, ac3 = st.columns(3)
        with ac1:
            new_qf_code = st.text_input(
                "종목코드", key="qf_new_code", placeholder="예: 005930 또는 AAPL",
            )
        with ac2:
            new_qf_name = st.text_input(
                "종목명", key="qf_new_name", placeholder="예: 삼성전자",
            )
        with ac3:
            new_qf_market = st.selectbox("시장", options=["KR", "US"], key="qf_new_market")

        # 미국 종목 거래소 선택
        if new_qf_market == "US":
            new_qf_exchange = st.selectbox(
                "거래소", options=["NAS", "NYS"], key="qf_new_exchange",
            )
        else:
            new_qf_exchange = ""

        if st.button("종목 추가", key="qf_add_btn"):
            errors = _validate_universe_stock(new_qf_code, new_qf_name, new_qf_market, universe)
            if errors:
                for e in errors:
                    st.error(e)
            else:
                new_stock = {
                    "code": new_qf_code.strip(),
                    "market": new_qf_market,
                    "name": new_qf_name.strip(),
                }
                if new_qf_market == "US" and new_qf_exchange:
                    new_stock["exchange"] = new_qf_exchange
                universe.append(new_stock)
                qf["universe_codes"] = universe
                strategies["quant_factor"] = qf
                config["strategies"] = strategies
                save_settings(config)
                st.session_state.config_cache = config
                st.rerun()
        strategies["quant_factor"] = qf

    # ────────── 리스크 ──────────
    with tab_risk:
        c1, c2 = st.columns(2)
        with c1:
            risk["max_position_pct"] = st.number_input(
                "종목당 최대 비중 (%)", value=float(risk.get("max_position_pct", 10.0)),
                min_value=1.0, max_value=50.0, step=1.0, key="risk_max_pos",
            )
            risk["stop_loss_pct"] = st.number_input(
                "손절 (%)", value=float(risk.get("stop_loss_pct", -7.0)),
                min_value=-30.0, max_value=0.0, step=0.5, key="risk_sl",
            )
            risk["daily_loss_limit_pct"] = st.number_input(
                "일일 최대 손실 (%)", value=float(risk.get("daily_loss_limit_pct", -2.0)),
                min_value=-20.0, max_value=0.0, step=0.5, key="risk_daily",
            )
        with c2:
            risk["max_drawdown_pct"] = st.number_input(
                "최대 드로다운 (%)", value=float(risk.get("max_drawdown_pct", -10.0)),
                min_value=-50.0, max_value=0.0, step=1.0, key="risk_mdd",
            )
            risk["max_positions"] = st.number_input(
                "최대 포지션 수", value=int(risk.get("max_positions", 10)),
                min_value=1, max_value=50, key="risk_max_n",
            )
            risk["min_cash_pct"] = st.number_input(
                "최소 현금 비중 (%)", value=float(risk.get("min_cash_pct", 20.0)),
                min_value=0.0, max_value=90.0, step=5.0, key="risk_cash",
            )

    # ────────── 백테스트 설정 ──────────
    with tab_bt:
        c1, c2 = st.columns(2)
        with c1:
            bt["initial_capital"] = st.number_input(
                "초기 자본금 (KRW)", value=int(bt.get("initial_capital", 10_000_000)),
                step=1_000_000, format="%d", key="bt_capital",
            )
            bt["commission_rate"] = st.number_input(
                "기본 수수료율 (DB 백테스트용)", value=float(bt.get("commission_rate", 0.00015)),
                min_value=0.0, max_value=0.01, step=0.00005, format="%.5f",
                key="bt_comm",
            )
        with c2:
            bt["slippage_rate"] = st.number_input(
                "슬리피지율", value=float(bt.get("slippage_rate", 0.001)),
                min_value=0.0, max_value=0.05, step=0.0005, format="%.4f",
                key="bt_slip",
            )
            bt["start_date"] = st.date_input(
                "시작일",
                value=_parse_date(bt.get("start_date"), date(2024, 1, 1)),
                key="bt_start",
            ).strftime("%Y-%m-%d")
            bt["end_date"] = st.date_input(
                "종료일",
                value=_parse_date(bt.get("end_date"), date(2025, 12, 31)),
                key="bt_end",
            ).strftime("%Y-%m-%d")

        st.subheader("시장별 수수료 / 세금")
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            bt["commission_rate_kr"] = st.number_input(
                "KR 매매 수수료율",
                value=float(bt.get("commission_rate_kr", 0.00015)),
                min_value=0.0, max_value=0.01, step=0.00005, format="%.5f",
                key="bt_comm_kr",
                help="한국 주식 편도 수수료율 (기본 0.015%)",
            )
        with fc2:
            bt["commission_rate_us"] = st.number_input(
                "US 매매 수수료율",
                value=float(bt.get("commission_rate_us", 0.0)),
                min_value=0.0, max_value=0.01, step=0.00005, format="%.5f",
                key="bt_comm_us",
                help="미국 주식 편도 수수료율 (기본 0%, 무수수료)",
            )
        with fc3:
            bt["tax_rate_kr"] = st.number_input(
                "KR 매도 거래세",
                value=float(bt.get("tax_rate_kr", 0.0018)),
                min_value=0.0, max_value=0.01, step=0.0001, format="%.4f",
                key="bt_tax_kr",
                help="한국 주식 매도 시 거래세 (기본 0.18%)",
            )

    # ────────── API / 알림 설정 ──────────
    with tab_api:
        # ── KIS API 모드 ──
        st.subheader("KIS API 설정")
        is_live = kis.get("live_trading", False)

        if is_live:
            st.error("현재 모드: **실거래** — 실제 자금으로 거래됩니다.")
        else:
            st.info("현재 모드: **모의투자** — 가상 계좌로 거래됩니다.")

        # 2단계 확인 (실거래 전환은 위험하므로)
        if "kis_mode_confirm" not in st.session_state:
            st.session_state.kis_mode_confirm = False

        if not st.session_state.kis_mode_confirm:
            target_label = "모의투자로 전환" if is_live else "실거래로 전환"
            if st.button(target_label, key="kis_mode_toggle"):
                st.session_state.kis_mode_confirm = True
                st.rerun()
        else:
            if is_live:
                st.warning("모의투자 모드로 전환합니다.")
            else:
                st.warning("**실거래 모드**로 전환합니다. 실제 자금이 사용됩니다!")
            mc1, mc2 = st.columns(2)
            with mc1:
                if st.button("확인 — 전환", key="kis_mode_yes", type="primary"):
                    kis["live_trading"] = not is_live
                    config["kis"] = kis
                    save_settings(config)
                    st.session_state.config_cache = config
                    st.session_state.kis_mode_confirm = False
                    st.rerun()
            with mc2:
                if st.button("취소", key="kis_mode_no"):
                    st.session_state.kis_mode_confirm = False
                    st.rerun()

        st.divider()
        kis["rate_limit"] = st.number_input(
            "API 호출 제한 (초당 최대)",
            value=int(kis.get("rate_limit", 10)),
            min_value=1, max_value=20, key="kis_rate_limit",
            help="KIS API 초당 최대 호출 횟수",
        )

        # ── 알림 설정 ──
        st.subheader("텔레그램 알림")
        tg = notifications.get("telegram", {})
        tg["enabled"] = st.checkbox(
            "텔레그램 알림 활성화",
            value=tg.get("enabled", True), key="tg_enabled",
        )
        notifications["telegram"] = tg

        st.caption("텔레그램 봇 토큰과 채팅 ID는 `.env` 파일에서 관리합니다.")

        st.subheader("알림 이벤트")
        available_events = {
            "trade_executed": "거래 체결",
            "stop_loss_triggered": "손절 발동",
            "strategy_signal": "전략 시그널",
            "daily_summary": "일일 요약",
            "error": "오류 발생",
        }
        current_alerts = notifications.get("alert_on", list(available_events.keys()))
        selected_alerts = []
        event_items = list(available_events.items())
        for row_start in range(0, len(event_items), 3):
            row_items = event_items[row_start:row_start + 3]
            alert_cols = st.columns(3)
            for col, (event_key, event_label) in zip(alert_cols, row_items):
                with col:
                    if st.checkbox(
                        event_label,
                        value=event_key in current_alerts,
                        key=f"alert_{event_key}",
                    ):
                        selected_alerts.append(event_key)
        notifications["alert_on"] = selected_alerts

    # ── 저장 + 적용 ──
    config["strategies"] = strategies
    config["risk"] = risk
    config["backtest"] = bt
    config["kis"] = kis
    config["notifications"] = notifications

    st.divider()
    col_save, col_rerun = st.columns(2)

    with col_save:
        if st.button("\U0001f4be 설정 저장", use_container_width=True):
            validation_errors = _validate_config_before_save(config)
            if validation_errors:
                for err in validation_errors:
                    st.error(err)
            else:
                try:
                    save_settings(config)
                    st.session_state.config_cache = config
                    st.success("설정이 저장되었습니다!")
                except Exception as e:
                    st.error(f"저장 실패: {e}")

    with col_rerun:
        if st.button("\U0001f504 백테스트 다시 실행", use_container_width=True):
            st.session_state.config_cache = None  # 캐시 초기화
            st.session_state.backtest_result = None
            st.session_state.backtest_metrics = None
            st.info("'백테스트' 탭으로 이동해서 실행해주세요.")


def _validate_pair(
    name: str, market: str, stock_a: str, stock_b: str,
    hedge_etf: str, existing_pairs: list[dict],
) -> list[str]:
    """StatArb 페어 입력 검증. 에러 메시지 리스트 반환 (비어있으면 통과)."""
    errors: list[str] = []

    if not name.strip():
        errors.append("페어 이름을 입력하세요.")
    if not stock_a.strip():
        errors.append("종목 A 코드를 입력하세요.")
    if not stock_b.strip():
        errors.append("종목 B 코드를 입력하세요.")
    if not hedge_etf.strip():
        errors.append("헤지 ETF 코드를 입력하세요.")

    if stock_a.strip() and stock_b.strip() and stock_a.strip() == stock_b.strip():
        errors.append("종목 A와 종목 B가 동일합니다.")

    if name.strip():
        for p in existing_pairs:
            if p["name"] == name.strip():
                errors.append(f"이미 존재하는 페어 이름입니다: {name}")
                break

    if market == "KR":
        for label, code in [("종목 A", stock_a), ("종목 B", stock_b), ("헤지 ETF", hedge_etf)]:
            code = code.strip()
            if code and (not code.isdigit() or len(code) != 6):
                errors.append(f"{label}: KR 종목코드는 6자리 숫자여야 합니다 (입력: {code})")
    elif market == "US":
        for label, code in [("종목 A", stock_a), ("종목 B", stock_b)]:
            code = code.strip()
            if code and (not code.replace(".", "").isalpha() or len(code) > 5):
                errors.append(f"{label}: US 종목코드 형식이 올바르지 않습니다 (입력: {code})")

    return errors


def _validate_universe_stock(
    code: str, name: str, market: str, existing: list[dict],
) -> list[str]:
    """QuantFactor 유니버스 종목 입력 검증."""
    errors: list[str] = []

    if not code.strip():
        errors.append("종목코드를 입력하세요.")
    if not name.strip():
        errors.append("종목명을 입력하세요.")

    if code.strip():
        for item in existing:
            if item["code"] == code.strip() and item.get("market") == market:
                errors.append(f"이미 존재하는 종목입니다: {code} [{market}]")
                break

    if market == "KR" and code.strip():
        if not code.strip().isdigit() or len(code.strip()) != 6:
            errors.append("KR 종목코드는 6자리 숫자여야 합니다.")
    elif market == "US" and code.strip():
        if not code.strip().replace(".", "").isalpha() or len(code.strip()) > 5:
            errors.append("US 종목코드 형식이 올바르지 않습니다.")

    return errors


def _validate_config_before_save(config: dict) -> list[str]:
    """저장 전 전체 설정 검증."""
    errors: list[str] = []

    # DualMomentum ETF 빈값 검사
    dm_cfg = config.get("strategies", {}).get("dual_momentum", {})
    etf_labels = {
        "kr_etf": "KR ETF",
        "us_etf": "US ETF",
        "safe_kr_etf": "Safe KR ETF",
        "safe_us_etf": "Safe US ETF",
    }
    for field, label in etf_labels.items():
        val = dm_cfg.get(field, "")
        if isinstance(val, str):
            val = val.strip()
        if not val:
            errors.append(f"DualMomentum: {label}이(가) 비어 있습니다.")
        else:
            dm_cfg[field] = val  # 공백 제거된 값 저장

    # QuantFactor 가중치 합계 검증
    qf_cfg = config.get("strategies", {}).get("quant_factor", {})
    qf_weights = qf_cfg.get("weights", {})
    weight_sum = (
        float(qf_weights.get("value", 0))
        + float(qf_weights.get("quality", 0))
        + float(qf_weights.get("momentum", 0))
    )
    if abs(weight_sum - 1.0) > 0.05:
        errors.append(
            f"QuantFactor: 팩터 가중치 합계가 {weight_sum:.2f}입니다 (0.95~1.05 범위여야 합니다)"
        )

    # StatArb 기존 페어 필드 빈값 검사
    sa_cfg = config.get("strategies", {}).get("stat_arb", {})
    for i, pair in enumerate(sa_cfg.get("pairs", [])):
        for field in ["name", "stock_a", "stock_b", "hedge_etf"]:
            val = pair.get(field, "")
            if isinstance(val, str):
                val = val.strip()
            if not val:
                errors.append(f"StatArb 페어 #{i + 1}: {field}이(가) 비어 있습니다.")
            else:
                pair[field] = val  # 공백 제거

    return errors


