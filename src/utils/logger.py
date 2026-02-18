"""
AlgoTrader KR — 로깅 설정

loguru 기반 로거를 콘솔(컬러) + 파일(로테이션)로 출력합니다.

Depends on:
    - src.core.config (로깅 레벨, 로테이션 설정)
    - loguru (로깅 프레임워크)

Used by:
    - main.py (앱 시작 시 setup_logger() 1회 호출)
    - 이후 각 모듈에서 `from loguru import logger` 사용

Modification Guide:
    - 로그 포맷 변경: setup_logger() 내 format 문자열 수정
    - 출력 대상 추가: logger.add()로 핸들러 추가 (예: Sentry, Slack)
"""
import sys
from pathlib import Path

from loguru import logger

from src.core.config import get_config, LOGS_DIR


def setup_logger() -> None:
    """loguru 로거 설정"""
    config = get_config()
    log_config = config.get("logging", {})

    level = log_config.get("level", "INFO")
    rotation = log_config.get("rotation", "10 MB")
    retention = log_config.get("retention", "30 days")

    # 기존 핸들러 제거
    logger.remove()

    # 콘솔 출력
    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> — <level>{message}</level>",
        colorize=True,
    )

    # 파일 출력
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / "trading_bot.log"

    logger.add(
        str(log_file),
        level=level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} — {message}",
        rotation=rotation,
        retention=retention,
        encoding="utf-8",
    )

    logger.info("로깅 시스템 초기화 완료")
