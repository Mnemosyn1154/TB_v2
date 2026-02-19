from __future__ import annotations

"""APScheduler wrapper — 15분 주기 자동 전략 실행

Depends on: dashboard/services/bot_service.py, src/core/config.py, src/core/risk_manager.py
Used by: pyapi/main.py (lifespan), pyapi/routers/bot.py (status/control endpoints)
"""

from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from src.core.config import get_config

_scheduler: BackgroundScheduler | None = None
_last_run: dict | None = None


def _is_market_hours() -> bool:
    """Check if current time is within any market's trading hours (KST)."""
    config = get_config()
    sched_cfg = config.get("scheduler", {})
    now = datetime.now()
    current_time = now.strftime("%H:%M")

    kr_open = sched_cfg.get("kr_market_open", "09:00")
    kr_close = sched_cfg.get("kr_market_close", "15:30")
    us_open = sched_cfg.get("us_market_open", "09:30")
    us_close = sched_cfg.get("us_market_close", "16:00")

    # KR market hours (KST direct)
    if kr_open <= current_time <= kr_close:
        return True

    # US market hours in KST (23:30 ~ 06:00 next day)
    # Convert US ET times to approximate KST (+14h)
    # US 09:30 ET = 23:30 KST, US 16:00 ET = 06:00 KST
    us_open_kst = "23:30"
    us_close_kst = "06:00"
    if current_time >= us_open_kst or current_time <= us_close_kst:
        return True

    return False


def _run_job() -> None:
    """Scheduled job: run all enabled strategies once."""
    global _last_run

    # Check kill switch
    from src.core.risk_manager import RiskManager
    rm = RiskManager()
    if rm.is_killed:
        logger.info("[Scheduler] Kill switch active, skipping run")
        _last_run = {
            "time": datetime.now().isoformat(),
            "status": "skipped",
            "reason": "kill_switch",
        }
        return

    # Check market hours
    if not _is_market_hours():
        logger.info("[Scheduler] Outside market hours, skipping run")
        _last_run = {
            "time": datetime.now().isoformat(),
            "status": "skipped",
            "reason": "outside_market_hours",
        }
        return

    logger.info("[Scheduler] Running scheduled strategy cycle")
    try:
        from dashboard.services.bot_service import run_once
        result = run_once()
        _last_run = {
            "time": datetime.now().isoformat(),
            "status": "success",
            "total_signals": result.get("total_signals", 0),
        }
        logger.info(f"[Scheduler] Completed — {result.get('total_signals', 0)} signals")
    except Exception as e:
        logger.error(f"[Scheduler] Error: {e}")
        _last_run = {
            "time": datetime.now().isoformat(),
            "status": "error",
            "error": str(e),
        }


def start_scheduler() -> None:
    """Start the background scheduler."""
    global _scheduler
    if _scheduler and _scheduler.running:
        logger.warning("[Scheduler] Already running")
        return

    config = get_config()
    sched_cfg = config.get("scheduler", {})
    interval = sched_cfg.get("interval_minutes", 15)

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        _run_job,
        trigger=IntervalTrigger(minutes=interval),
        id="strategy_run",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info(f"[Scheduler] Started with {interval}min interval")


def stop_scheduler() -> None:
    """Stop the background scheduler."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("[Scheduler] Stopped")
    _scheduler = None


def get_status() -> dict:
    """Return scheduler status for API."""
    running = _scheduler is not None and _scheduler.running

    next_run = None
    interval_minutes = None
    if running and _scheduler:
        job = _scheduler.get_job("strategy_run")
        if job and job.next_run_time:
            next_run = job.next_run_time.isoformat()
        if job and job.trigger:
            interval_minutes = int(job.trigger.interval.total_seconds() / 60)

    return {
        "running": running,
        "interval_minutes": interval_minutes,
        "next_run": next_run,
        "last_run": _last_run,
    }
