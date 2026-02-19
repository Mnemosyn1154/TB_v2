from __future__ import annotations

from fastapi import APIRouter, Depends

from pyapi.deps import verify_secret
from pyapi.schemas import ModeRequest

router = APIRouter(prefix="/py/bot", tags=["bot"])


def _get_current_mode() -> str:
    """설정에서 현재 트레이딩 모드를 판별합니다."""
    from src.core.config import get_config

    config = get_config()
    if config.get("simulation", {}).get("enabled", False):
        return "simulation"
    if config.get("kis", {}).get("live_trading", False):
        return "live"
    return "paper"


@router.get("/mode")
def get_trading_mode(secret: None = Depends(verify_secret)):
    """현재 트레이딩 모드 조회 (simulation / paper / live)"""
    return {"data": {"mode": _get_current_mode()}, "error": None}


@router.post("/mode")
def set_trading_mode(req: ModeRequest, secret: None = Depends(verify_secret)):
    """트레이딩 모드 전환

    - simulation: 항상 허용
    - paper: KIS 자격증명 검증 필수
    - live: KIS 검증 + confirm=true 필수
    """
    from src.core.config import reload_config, load_env
    from dashboard.services.config_service import load_settings, save_settings

    load_env()

    # live 전환 시 명시적 확인 필요
    if req.mode == "live" and not req.confirm:
        return {"data": None,
                "error": "실거래 모드 전환에는 confirm: true가 필요합니다"}

    # paper/live 전환 시 KIS 자격증명 검증
    if req.mode in ("paper", "live"):
        try:
            from src.core.broker import KISBroker
            broker = KISBroker()
            health = broker.verify_connection()
            if not health["connected"]:
                return {"data": None,
                        "error": f"KIS 연결 실패: {health['error']}"}
        except Exception as e:
            return {"data": None, "error": f"KIS 연결 실패: {e}"}

    # settings.yaml 업데이트 (원자적 쓰기, sort_keys=False로 키 순서 보존)
    raw_config = load_settings()

    if req.mode == "simulation":
        raw_config.setdefault("simulation", {})["enabled"] = True
    elif req.mode == "paper":
        raw_config.setdefault("simulation", {})["enabled"] = False
        raw_config.setdefault("kis", {})["live_trading"] = False
    elif req.mode == "live":
        raw_config.setdefault("simulation", {})["enabled"] = False
        raw_config.setdefault("kis", {})["live_trading"] = True

    save_settings(raw_config)
    reload_config()

    return {"data": {"mode": req.mode}, "error": None}


@router.get("/health/kis")
def kis_health_check(secret: None = Depends(verify_secret)):
    """KIS API 연결 상태 검증"""
    from src.core.config import load_env

    load_env()
    try:
        from src.core.broker import KISBroker
        broker = KISBroker()
        result = broker.verify_connection()
        return {"data": result, "error": None}
    except Exception as e:
        return {"data": {"connected": False, "mode": None, "account": None,
                         "error": str(e)}, "error": None}


@router.post("/collect")
def collect_data(secret: None = Depends(verify_secret)):
    """데이터 수집 실행"""
    from dashboard.services.bot_service import collect_data

    try:
        log = collect_data()
        return {"data": {"log": log}, "error": None}
    except Exception as e:
        return {"data": None, "error": str(e)}


@router.post("/run")
def run_once(secret: None = Depends(verify_secret)):
    """전략 1회 실행"""
    from dashboard.services.bot_service import run_once

    try:
        result = run_once()
        return {"data": result, "error": None}
    except Exception as e:
        return {"data": None, "error": str(e)}


@router.get("/kill-switch")
def get_kill_switch(secret: None = Depends(verify_secret)):
    """Kill Switch 상태 조회"""
    from dashboard.services.bot_service import get_kill_switch_status

    return {"data": {"kill_switch": get_kill_switch_status()}, "error": None}


@router.post("/kill-switch/activate")
def activate_kill_switch(secret: None = Depends(verify_secret)):
    """Kill Switch 활성화"""
    from dashboard.services.bot_service import activate_kill_switch

    activate_kill_switch("D2trader 대시보드에서 수동 활성화")
    return {"data": {"kill_switch": True}, "error": None}


@router.post("/kill-switch/deactivate")
def deactivate_kill_switch(secret: None = Depends(verify_secret)):
    """Kill Switch 비활성화"""
    from dashboard.services.bot_service import deactivate_kill_switch

    deactivate_kill_switch()
    return {"data": {"kill_switch": False}, "error": None}


@router.get("/status")
def bot_status(secret: None = Depends(verify_secret)):
    """봇 상태 조회 (kill switch + scheduler + mode)"""
    from dashboard.services.bot_service import get_kill_switch_status
    from pyapi.scheduler import get_status as get_scheduler_status

    return {
        "data": {
            "kill_switch": get_kill_switch_status(),
            "scheduler": get_scheduler_status(),
            "mode": _get_current_mode(),
        },
        "error": None,
    }


@router.post("/scheduler/start")
def scheduler_start(secret: None = Depends(verify_secret)):
    """스케줄러 시작"""
    from pyapi.scheduler import start_scheduler, get_status

    try:
        start_scheduler()
        return {"data": get_status(), "error": None}
    except Exception as e:
        return {"data": None, "error": str(e)}


@router.post("/scheduler/stop")
def scheduler_stop(secret: None = Depends(verify_secret)):
    """스케줄러 중지"""
    from pyapi.scheduler import stop_scheduler, get_status

    try:
        stop_scheduler()
        return {"data": get_status(), "error": None}
    except Exception as e:
        return {"data": None, "error": str(e)}


@router.get("/orders")
def get_orders(limit: int = 50, secret: None = Depends(verify_secret)):
    """최근 주문 내역 조회"""
    from src.core.config import load_env
    load_env()
    try:
        from src.core.broker import KISBroker
        from src.core.data_manager import DataManager
        broker = KISBroker()
        dm = DataManager(broker)
        orders = dm.get_orders(limit=limit)
        return {"data": orders, "error": None}
    except Exception as e:
        return {"data": [], "error": str(e)}
