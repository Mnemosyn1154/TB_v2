from __future__ import annotations

"""D2trader Python API — KIS/전략/백테스트 전용 경량 API"""

import sys
from pathlib import Path

# 프로젝트 루트를 import path에 추가 (기존 src/ 접근용)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from pyapi.routers import portfolio, backtest, bot, signals, paper, benchmark


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    from src.core.config import get_config
    from pyapi.scheduler import start_scheduler

    config = get_config()
    sched_cfg = config.get("scheduler", {})
    if sched_cfg.get("enabled", False):
        start_scheduler()
        logger.info("Scheduler auto-started (settings.yaml scheduler.enabled=true)")

    yield

    # Shutdown
    from pyapi.scheduler import stop_scheduler
    stop_scheduler()


app = FastAPI(title="D2trader Python API", version="0.1.0", lifespan=lifespan)

# CORS — 허용 오리진 설정
# 환경변수 ALLOWED_ORIGINS로 프로덕션 도메인 추가 가능 (콤마 구분)
# 예: ALLOWED_ORIGINS=https://d2trader.your-domain.com,https://www.d2trader.your-domain.com
_default_origins = ["http://localhost:3000"]
_extra_origins = os.environ.get("ALLOWED_ORIGINS", "")
_origins = _default_origins + [o.strip() for o in _extra_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(portfolio.router)
app.include_router(backtest.router)
app.include_router(bot.router)
app.include_router(signals.router)
app.include_router(paper.router)
app.include_router(benchmark.router)


@app.get("/py/health")
def health_check():
    """API 상태 확인용"""
    return {"status": "ok", "message": "D2trader Python API is running"}
