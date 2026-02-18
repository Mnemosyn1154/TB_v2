from __future__ import annotations

"""D2trader Python API — KIS/전략/백테스트 전용 경량 API"""

import sys
from pathlib import Path

# 프로젝트 루트를 import path에 추가 (기존 src/ 접근용)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pyapi.routers import portfolio, backtest, bot, signals, paper

app = FastAPI(title="D2trader Python API", version="0.1.0")

# CORS — 개발 시 Next.js에서의 직접 호출 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(portfolio.router)
app.include_router(backtest.router)
app.include_router(bot.router)
app.include_router(signals.router)
app.include_router(paper.router)


@app.get("/py/health")
def health_check():
    """API 상태 확인용"""
    return {"status": "ok", "message": "D2trader Python API is running"}
