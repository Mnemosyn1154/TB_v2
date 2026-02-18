from __future__ import annotations

from fastapi import APIRouter, Depends

from pyapi.deps import verify_secret

router = APIRouter(prefix="/py/bot", tags=["bot"])


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
