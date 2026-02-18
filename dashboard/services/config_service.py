from __future__ import annotations

"""settings.yaml 읽기/쓰기 서비스"""
import tempfile
from datetime import date, datetime
from pathlib import Path

import yaml

from src.core.config import CONFIG_DIR

SETTINGS_PATH = CONFIG_DIR / "settings.yaml"


def load_settings() -> dict:
    """settings.yaml을 dict로 반환"""
    with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_settings(config: dict) -> None:
    """dict를 settings.yaml에 저장 (원자적 쓰기)"""
    # 임시 파일에 먼저 쓴 뒤 rename (corruption 방지)
    tmp = SETTINGS_PATH.with_suffix(".yaml.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    tmp.replace(SETTINGS_PATH)

    # 싱글톤 캐시 무효화
    import src.core.config as cfg_module
    cfg_module._config = None


def parse_date(s: str | None, default: date) -> date:
    """YYYY-MM-DD 문자열을 date로 변환. 실패 시 default."""
    if not s:
        return default
    try:
        return datetime.strptime(str(s), "%Y-%m-%d").date()
    except Exception:
        return default
