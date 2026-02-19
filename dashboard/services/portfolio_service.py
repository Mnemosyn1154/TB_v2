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
        "exchange_rate": get_usd_krw(),
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
        err_msg = str(e)
        if "403" in err_msg or "Forbidden" in err_msg:
            err_msg = ("KIS API 인증 실패 (403 Forbidden). "
                       "API 키/시크릿이 만료되었거나 유효하지 않습니다. "
                       "시뮬레이션 모드를 사용하려면 settings.yaml에서 "
                       "simulation.enabled: true로 설정하세요.")
        elif "401" in err_msg or "Unauthorized" in err_msg:
            err_msg = ("KIS API 인증 실패 (401). "
                       "토큰이 만료되었습니다. data/kis_token_*.json 삭제 후 재시도하세요.")
        logger.error(f"KIS 포트폴리오 조회 실패: {e}")
        return {
            "error": err_msg,
            "kr": {},
            "us": {},
            "risk": _empty_risk(),
        }

    # RiskManager에 KIS 포지션 동기화
    risk_mgr = RiskManager()
    total_equity = kr_balance.get("total_equity", 0)
    cash = kr_balance.get("cash", 0)
    if total_equity > 0:
        risk_mgr.update_equity(total_equity, cash)

    all_positions = kr_balance.get("positions", []) + us_balance.get("positions", [])
    risk_mgr.state.positions = [
        Position(
            code=p["code"], market=p["market"], side="LONG",
            quantity=p["quantity"], entry_price=p["avg_price"],
            current_price=p["current_price"],
        )
        for p in all_positions
    ]

    return {
        "kr": kr_balance,
        "us": us_balance,
        "risk": risk_mgr.get_risk_summary(),
        "exchange_rate": get_usd_krw(),
        "error": None,
    }


# ──────────────────────────────────────────────
# 환율
# ──────────────────────────────────────────────

_fx_cache: dict[str, tuple[float, float]] = {}  # pair → (rate, timestamp)
_FX_TTL = 3600  # 1시간 캐시


def get_usd_krw() -> float:
    """USD/KRW 환율 조회 (yfinance, 1시간 캐시)"""
    import time
    cached = _fx_cache.get("USDKRW")
    if cached and (time.time() - cached[1]) < _FX_TTL:
        return cached[0]
    try:
        import yfinance as yf
        ticker = yf.Ticker("USDKRW=X")
        rate = ticker.fast_info.get("lastPrice", 0) or 0
        if rate > 0:
            _fx_cache["USDKRW"] = (rate, time.time())
            logger.debug(f"USD/KRW 환율: {rate:,.1f}")
            return rate
    except Exception as e:
        logger.warning(f"USD/KRW 환율 조회 실패: {e}")
    # 캐시 남아있으면 만료돼도 사용
    if cached:
        return cached[0]
    return 1350.0  # 최후 폴백


# ──────────────────────────────────────────────
# 헬퍼 함수
# ──────────────────────────────────────────────

def _build_name_lookup() -> dict[str, str]:
    """settings.yaml에서 종목코드 → 이름 매핑 빌드"""
    config = get_config()
    lookup: dict[str, str] = {}
    strategies = config.get("strategies", {})
    for _key, strat in strategies.items():
        # universe_codes, sectors (have explicit name field)
        for item in strat.get("universe_codes", []):
            if item.get("code") and item.get("name"):
                lookup[str(item["code"])] = item["name"]
        for item in strat.get("sectors", []):
            if item.get("code") and item.get("name"):
                lookup[str(item["code"])] = f"{item['name']} 섹터"
        # pairs
        for pair in strat.get("pairs", []):
            if pair.get("name"):
                for field in ("stock_a", "stock_b", "hedge_etf"):
                    code = pair.get(field)
                    if code:
                        lookup[str(code)] = f"{pair['name']}_{field}"
    return lookup


_name_cache: dict[str, str] = {}


def _resolve_name_yf(code: str) -> str | None:
    """yfinance에서 종목명 조회 (1회 호출 후 캐시)"""
    try:
        import yfinance as yf
        # 한국 종목 (숫자 코드)
        ticker_str = f"{code}.KS" if code.isdigit() else code
        ticker = yf.Ticker(ticker_str)
        info = ticker.info or {}
        name = info.get("shortName") or info.get("longName")
        if name:
            return name
        # .KS 실패 시 .KQ (코스닥) 시도
        if code.isdigit():
            ticker = yf.Ticker(f"{code}.KQ")
            info = ticker.info or {}
            return info.get("shortName") or info.get("longName")
    except Exception:
        pass
    return None


def _get_name(code: str, fallback: str = "") -> str:
    """종목코드로 이름 조회 (settings → yfinance 폴백, 캐시)"""
    if code in _name_cache:
        return _name_cache[code]

    # 1. settings.yaml 매핑
    if not _name_cache:
        _name_cache.update(_build_name_lookup())
        if code in _name_cache:
            return _name_cache[code]

    # 2. yfinance 폴백
    name = _resolve_name_yf(code)
    if name:
        _name_cache[code] = name
        return name

    # 3. 최종 폴백
    _name_cache[code] = fallback or code
    return _name_cache[code]


def _to_frontend_position(p: dict) -> dict:
    """DB 포지션 → 프론트엔드 Position 형식"""
    entry = p["entry_price"]
    current = p["current_price"]
    quantity = p["quantity"]
    code = p["code"]
    profit_amt = (current - entry) * quantity
    profit_pct = ((current - entry) / entry * 100) if entry > 0 else 0
    return {
        "code": code,
        "name": p.get("name") or _get_name(code),
        "quantity": quantity,
        "avg_price": entry,
        "current_price": current,
        "profit_pct": round(profit_pct, 2),
        "profit_amt": round(profit_amt, 2),
        "market": p["market"],
        "strategy": p.get("strategy", ""),
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
