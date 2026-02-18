from __future__ import annotations

"""포트폴리오/계좌 조회 서비스"""
from src.core.config import get_kis_credentials, load_env
from src.core.risk_manager import RiskManager


def get_portfolio_status() -> dict:
    """KIS API를 통해 잔고 + 리스크 상태 반환"""
    load_env()

    # 자격증명 사전 검증
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
