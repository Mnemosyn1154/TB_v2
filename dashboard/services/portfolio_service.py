from __future__ import annotations

"""포트폴리오/계좌 조회 서비스

시뮬레이션 모드: PortfolioTracker(SQLite)에서 포지션/현금 로드 + KIS/yfinance로 현재가 업데이트
실거래 모드: KIS API에서 잔고 직접 조회 (기존 동작)
"""
from loguru import logger

from src.core.config import get_config, load_env
from src.core.risk_manager import RiskManager, Position


def get_portfolio_status() -> dict:
    """포트폴리오 상태 반환 (시뮬레이션/실거래 모드 자동 분기)"""
    load_env()
    config = get_config()
    sim_enabled = config.get("simulation", {}).get("enabled", False)

    if sim_enabled:
        return _get_simulation_portfolio()
    else:
        return _get_kis_portfolio()


def _get_simulation_portfolio() -> dict:
    """시뮬레이션 포트폴리오 (로컬 DB 기반)"""
    try:
        from src.core.portfolio_tracker import PortfolioTracker
        tracker = PortfolioTracker()
        summary = tracker.get_portfolio_summary()
    except Exception as e:
        logger.error(f"PortfolioTracker 조회 실패: {e}")
        return {
            "error": str(e),
            "kr": {"positions": []},
            "us": {"positions": []},
            "risk": _empty_risk(),
            "initial_capital": 0,
        }

    positions = summary["positions"]

    # 현재가 업데이트 (KIS → yfinance 폴백)
    _update_current_prices(tracker, positions)

    # KR/US 분리
    kr_positions = [_to_frontend_position(p) for p in positions if p["market"] == "KR"]
    us_positions = [_to_frontend_position(p) for p in positions if p["market"] == "US"]

    # equity 재계산 (현재가 업데이트 후)
    kr_equity = sum(p["current_price"] * p["quantity"] for p in positions if p["market"] == "KR")
    us_equity = sum(p["current_price"] * p["quantity"] for p in positions if p["market"] == "US")
    total_equity = kr_equity + us_equity
    cash = summary["cash"]
    total_value = cash + total_equity

    # RiskManager 동기화
    risk_mgr = RiskManager()
    risk_mgr.update_equity(total_equity, cash)
    risk_mgr.state.positions = [
        Position(
            code=p["code"], market=p["market"], side=p["side"],
            quantity=p["quantity"], entry_price=p["entry_price"],
            current_price=p["current_price"],
            strategy=p.get("strategy", ""),
            entry_time=p.get("entry_time", ""),
        )
        for p in positions
    ]

    return {
        "kr": {
            "positions": kr_positions,
            "total_equity": kr_equity,
            "cash": cash,
            "total_value": total_value,
        },
        "us": {
            "positions": us_positions,
        },
        "risk": risk_mgr.get_risk_summary(),
        "initial_capital": summary["initial_capital"],
        "error": None,
    }


def _get_kis_portfolio() -> dict:
    """실거래 포트폴리오 (KIS API 기반, 기존 동작)"""
    from src.core.config import get_kis_credentials

    creds = get_kis_credentials()
    if not creds["app_key"] or not creds["app_secret"] or not creds["account_no"]:
        missing = [
            name for key, name in [
                ("app_key", "KIS_APP_KEY"),
                ("app_secret", "KIS_APP_SECRET"),
                ("account_no", "KIS_ACCOUNT_NO"),
            ]
            if not creds[key]
        ]
        return {
            "error": f"KIS API 인증 정보가 설정되지 않았습니다 (누락: {', '.join(missing)})",
            "kr": {},
            "us": {},
            "risk": _empty_risk(),
        }

    try:
        from src.core.broker import KISBroker
        broker = KISBroker()
        kr_balance = broker.get_kr_balance()
        us_balance = broker.get_us_balance()
    except Exception as e:
        return {
            "error": str(e),
            "kr": {},
            "us": {},
            "risk": _empty_risk(),
        }

    risk_mgr = RiskManager()
    total_equity = kr_balance.get("total_equity", 0)
    cash = kr_balance.get("cash", 0)
    if total_equity > 0:
        risk_mgr.update_equity(total_equity, cash)

    return {
        "kr": kr_balance,
        "us": us_balance,
        "risk": risk_mgr.get_risk_summary(),
        "error": None,
    }


# ──────────────────────────────────────────────
# 헬퍼 함수
# ──────────────────────────────────────────────

def _to_frontend_position(p: dict) -> dict:
    """DB 포지션 → 프론트엔드 Position 형식"""
    entry = p["entry_price"]
    current = p["current_price"]
    quantity = p["quantity"]
    profit_amt = (current - entry) * quantity
    profit_pct = ((current - entry) / entry * 100) if entry > 0 else 0
    return {
        "code": p["code"],
        "name": p["code"],
        "quantity": quantity,
        "avg_price": entry,
        "current_price": current,
        "profit_pct": round(profit_pct, 2),
        "profit_amt": round(profit_amt, 2),
        "market": p["market"],
    }


def _update_current_prices(tracker, positions: list[dict]) -> None:
    """각 포지션의 현재가를 업데이트 (KIS → yfinance 폴백)"""
    for p in positions:
        price = _get_current_price(p["code"], p["market"])
        if price > 0:
            p["current_price"] = price
            tracker.update_position_price(p["code"], price)


def _get_current_price(code: str, market: str) -> float:
    """KIS API → yfinance 폴백으로 현재가 조회"""
    # KIS API 시도
    try:
        from src.core.broker import KISBroker
        broker = KISBroker()
        if market == "KR":
            data = broker.get_kr_price(code)
            return float(data["price"])
        else:
            from src.core.exchange import get_us_exchange
            exchange = get_us_exchange(code)
            data = broker.get_us_price(code, exchange=exchange)
            return float(data["price"])
    except Exception as e:
        logger.debug(f"KIS 가격 조회 실패: {code} — {e}")

    # yfinance 폴백
    try:
        from src.core.data_feed import DataFeed
        import yfinance as yf

        symbol = DataFeed._to_yf_symbol(code, market)
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception as e:
        logger.debug(f"yfinance 가격 조회 실패: {code} — {e}")

    return 0.0


def _empty_risk() -> dict:
    return {
        "total_equity": 0,
        "cash": 0,
        "cash_pct": "0.0%",
        "daily_pnl": 0,
        "drawdown": "0.0%",
        "positions_count": 0,
        "max_positions": 0,
        "kill_switch": False,
        "positions": [],
    }
