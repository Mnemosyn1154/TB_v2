from __future__ import annotations

"""
모의 거래(Paper Trading) 서비스

KIS API 모의투자 서버를 활용하여 실제 주문 흐름을 그대로 테스트합니다.
live_trading: false 상태에서 KIS 모의투자 URL로 주문이 전송되며,
실거래 전환 시 settings.yaml의 live_trading: true만 변경하면 됩니다.

주요 기능:
    1. 시그널 미리보기 (Dry-Run) — 전략 시그널만 생성, 주문 안 함
    2. 시그널 실행 — KIS API 모의투자 서버로 실제 주문 전송
    3. 포트폴리오 조회 — KIS API로 모의투자 잔고 조회
    4. 거래 이력 — DB에 기록 및 조회

Depends on:
    - dashboard.services.bot_service (_build_strategies, _run_strategy)
    - dashboard.services.backtest_service (_get_db_engine, load_prices_from_db)
    - src.core.broker (KISBroker — 모의투자/실거래 자동 분기)
    - src.execution.executor (OrderExecutor — 주문 실행)
    - src.core.risk_manager (RiskManager — 리스크 관리)
    - src.core.data_manager (DataManager — 거래 기록)
    - src.utils.notifier (TelegramNotifier — 알림)

Used by:
    - dashboard.views.p5_paper_trading
"""
import json
import uuid
from datetime import datetime

import pandas as pd
from loguru import logger
from sqlalchemy import text

from dashboard.services.backtest_service import _get_db_engine, load_prices_from_db
from dashboard.services.bot_service import _build_strategies
from src.core.config import get_config, load_env
from src.strategies.base import TradeSignal, Signal


# ──────────────────────────────────────────────
# DB 초기화 (세션/거래 이력 추적용)
# ──────────────────────────────────────────────

def _init_paper_tables() -> None:
    """모의 거래 추적 테이블 생성 (없으면)"""
    engine = _get_db_engine()
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS paper_sessions (
                session_id TEXT PRIMARY KEY,
                start_date TEXT NOT NULL,
                end_date TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                strategy_names TEXT,
                memo TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS paper_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                strategy TEXT NOT NULL,
                code TEXT NOT NULL,
                market TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                reason TEXT,
                order_result TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES paper_sessions(session_id)
            )
        """))


# ──────────────────────────────────────────────
# 세션 관리
# ──────────────────────────────────────────────

def create_session() -> dict:
    """새 모의 거래 세션 생성"""
    _init_paper_tables()

    # 기존 활성 세션이 있으면 종료
    active = get_active_session()
    if active:
        stop_session(active["session_id"])

    session_id = str(uuid.uuid4())[:8]
    now = datetime.now().isoformat()

    strategies = _build_strategies()
    strategy_names = [s.name for s in strategies]

    engine = _get_db_engine()
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO paper_sessions (session_id, start_date, status, strategy_names)
            VALUES (:sid, :start, 'active', :strategies)
        """), {
            "sid": session_id,
            "start": now,
            "strategies": json.dumps(strategy_names),
        })

    logger.info(f"모의 거래 세션 생성: {session_id}")
    return get_active_session()


def get_active_session() -> dict | None:
    """활성 세션 조회"""
    _init_paper_tables()
    engine = _get_db_engine()
    with engine.connect() as conn:
        row = conn.execute(text(
            "SELECT * FROM paper_sessions WHERE status = 'active' ORDER BY created_at DESC LIMIT 1"
        )).mappings().first()

    if row is None:
        return None

    session = dict(row)
    session["strategy_names"] = json.loads(session.get("strategy_names") or "[]")
    return session


def stop_session(session_id: str) -> None:
    """세션 종료"""
    now = datetime.now().isoformat()
    engine = _get_db_engine()
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE paper_sessions SET status = 'stopped', end_date = :end
            WHERE session_id = :sid
        """), {"sid": session_id, "end": now})
    logger.info(f"모의 거래 세션 종료: {session_id}")


# ──────────────────────────────────────────────
# 시그널 생성 (Dry-Run)
# ──────────────────────────────────────────────

def generate_signals_dry_run() -> list[dict]:
    """
    현재 DB 데이터로 전략 시그널만 생성 (주문 안 함).

    Returns:
        시그널 dict 리스트: strategy, code, market, signal, price, reason, _raw
    """
    load_env()
    strategies = _build_strategies()

    all_signals: list[dict] = []
    for strategy in strategies:
        try:
            price_data = {}
            for item in strategy.required_codes():
                code = item["code"]
                market = item["market"]
                df = load_prices_from_db(code, market)
                if not df.empty:
                    price_data[code] = df["close"]

            if not price_data:
                continue

            kwargs = strategy.prepare_signal_kwargs(price_data)
            if not kwargs:
                continue

            signals = strategy.generate_signals(**kwargs)
            for sig in signals:
                if sig.signal == Signal.HOLD:
                    continue
                all_signals.append({
                    "strategy": sig.strategy,
                    "code": sig.code,
                    "market": sig.market,
                    "signal": sig.signal.value,
                    "quantity": sig.quantity,
                    "price": sig.price,
                    "reason": sig.reason,
                    "_raw": sig,
                })
        except Exception as e:
            logger.error(f"시그널 생성 실패 ({strategy.name}): {e}")

    return all_signals


# ──────────────────────────────────────────────
# 시그널 실행 (KIS API 모의투자 주문)
# ──────────────────────────────────────────────

def execute_signal(session_id: str, signal_dict: dict) -> dict:
    """
    시그널을 KIS API 모의투자 서버로 실제 주문 전송합니다.

    기존 OrderExecutor 파이프라인을 그대로 사용:
        1. KISBroker → 현재가 조회
        2. RiskManager → 리스크 검증 + 포지션 사이즈 계산
        3. KISBroker → 주문 전송 (모의투자/실거래 자동 분기)
        4. DB 기록 + 텔레그램 알림

    Returns:
        체결 결과 dict
    """
    load_env()

    signal: TradeSignal | None = signal_dict.get("_raw")
    if signal is None:
        return {"error": "시그널 데이터가 없습니다."}

    try:
        from src.core.broker import KISBroker
        from src.core.data_manager import DataManager
        from src.core.risk_manager import RiskManager
        from src.execution.executor import OrderExecutor
        from src.utils.notifier import TelegramNotifier

        broker = KISBroker()
        rm = RiskManager()
        dm = DataManager(broker)
        notifier = TelegramNotifier()
        executor = OrderExecutor(broker, rm, dm, notifier)

        # 단일 시그널 실행 (OrderExecutor가 리스크 검증 + 주문 + 기록 처리)
        executor.execute_signals([signal])

        # 모의 거래 이력 DB 기록
        _save_paper_trade(session_id, signal)

        mode = "모의투자" if not broker.live_trading else "실거래"
        return {
            "success": True,
            "side": signal.signal.value,
            "code": signal.code,
            "market": signal.market,
            "reason": signal.reason,
            "mode": mode,
        }
    except Exception as e:
        logger.error(f"시그널 실행 실패: {signal.code} — {e}")
        return {"error": str(e)}


def execute_all_signals(session_id: str, signal_dicts: list[dict]) -> list[dict]:
    """모든 시그널을 일괄 실행"""
    results = []
    for sig_dict in signal_dicts:
        result = execute_signal(session_id, sig_dict)
        results.append(result)
    return results


def _save_paper_trade(session_id: str, signal: TradeSignal) -> None:
    """모의 거래 이력 DB 저장"""
    engine = _get_db_engine()
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO paper_trades
                (session_id, strategy, code, market, side, quantity, price, reason, timestamp)
            VALUES (:sid, :strategy, :code, :market, :side, :qty, :price, :reason, :ts)
        """), {
            "sid": session_id,
            "strategy": signal.strategy,
            "code": signal.code,
            "market": signal.market,
            "side": signal.signal.value,
            "qty": signal.quantity,
            "price": signal.price,
            "reason": signal.reason,
            "ts": datetime.now().isoformat(),
        })


# ──────────────────────────────────────────────
# 포트폴리오 조회 (KIS API)
# ──────────────────────────────────────────────

def get_portfolio() -> dict:
    """
    KIS API로 현재 (모의투자) 잔고를 조회합니다.

    portfolio_service.get_portfolio_status()와 동일한 로직이지만,
    여기서는 모의 거래 세션 컨텍스트에서 사용됩니다.
    """
    from dashboard.services.portfolio_service import get_portfolio_status
    return get_portfolio_status()


# ──────────────────────────────────────────────
# 거래 이력 조회
# ──────────────────────────────────────────────

def get_paper_trades(session_id: str) -> pd.DataFrame:
    """세션의 거래 이력 조회"""
    engine = _get_db_engine()
    query = text("""
        SELECT strategy, code, market, side, quantity, price,
               reason, timestamp
        FROM paper_trades
        WHERE session_id = :sid
        ORDER BY timestamp DESC
    """)
    return pd.read_sql(query, engine, params={"sid": session_id})


def get_session_history() -> list[dict]:
    """모든 세션 목록 조회"""
    _init_paper_tables()
    engine = _get_db_engine()
    query = text("""
        SELECT session_id, start_date, end_date, status, strategy_names
        FROM paper_sessions
        ORDER BY created_at DESC
    """)
    df = pd.read_sql(query, engine)
    return df.to_dict("records") if not df.empty else []


def get_session_trade_summary(session_id: str) -> dict:
    """세션의 거래 요약 통계"""
    trades_df = get_paper_trades(session_id)
    if trades_df.empty:
        return {"total_trades": 0, "buy_count": 0, "sell_count": 0}

    buy_count = len(trades_df[trades_df["side"] == "BUY"])
    sell_count = len(trades_df[trades_df["side"].isin(["SELL", "CLOSE"])])

    return {
        "total_trades": len(trades_df),
        "buy_count": buy_count,
        "sell_count": sell_count,
    }
