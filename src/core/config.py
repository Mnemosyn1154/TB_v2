from __future__ import annotations

"""
AlgoTrader KR — 설정 로더

settings.yaml과 .env 파일로부터 설정과 인증 정보를 로드합니다.
싱글톤 패턴으로 앱 전체에서 동일한 설정 인스턴스를 공유합니다.

Depends on:
    - pyyaml (YAML 파싱)
    - python-dotenv (.env 파일 로드)

Used by:
    - 모든 모듈에서 get_config()으로 설정 접근
    - broker.py, notifier.py에서 get_kis_credentials(), get_telegram_credentials() 사용

Modification Guide:
    - 새 환경 변수 추가: get_xxx_credentials() 함수 추가 + .env.example 업데이트
    - 새 설정 섹션 추가: settings.yaml에 키 추가 (get_config()은 자동 반영)
    - 경로 상수 추가: ROOT_DIR 기반으로 Path 상수 정의
"""
import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from loguru import logger


# 프로젝트 루트 디렉토리
ROOT_DIR = Path(__file__).parent.parent.parent
CONFIG_DIR = ROOT_DIR / "config"
DATA_DIR = ROOT_DIR / "data"
LOGS_DIR = ROOT_DIR / "logs"


def load_config(config_path: str | None = None) -> dict[str, Any]:
    """settings.yaml 로드"""
    if config_path is None:
        config_path = CONFIG_DIR / "settings.yaml"

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    return config


_env_loaded = False


def load_env() -> None:
    """환경 변수 로드 (.env)

    워크트리에서 실행 시 메인 레포의 .env도 탐색합니다.
    최초 1회만 실행되며, 이후 호출은 무시됩니다.
    """
    global _env_loaded
    if _env_loaded:
        return
    _env_loaded = True

    env_path = ROOT_DIR / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        return

    # 워크트리에서 실행 시 메인 레포의 .env 탐색
    git_dir = ROOT_DIR / ".git"
    if git_dir.is_file():
        # .git 파일인 경우 워크트리 — 메인 레포 경로 추출
        try:
            content = git_dir.read_text().strip()
            # "gitdir: /path/to/main/.git/worktrees/name" 형식
            if content.startswith("gitdir:"):
                main_git = Path(content.split(":", 1)[1].strip())
                # .git/worktrees/name → .git → 메인 레포 루트
                main_root = main_git.parent.parent.parent
                main_env = main_root / ".env"
                if main_env.exists():
                    load_dotenv(main_env)
                    return
        except Exception:
            pass

    # Streamlit Cloud 환경에서는 st.secrets로 대체 가능하므로 경고 생략
    try:
        import streamlit as st
        if st.secrets:
            return
    except Exception:
        pass
    logger.warning(".env 파일이 없습니다. .env.example을 복사하여 .env를 생성해주세요.")


def _get_env(key: str, default: str = "") -> str:
    """os.environ → st.secrets 순서로 환경변수 조회"""
    value = os.getenv(key, "")
    source = "os.environ"
    if not value:
        try:
            import streamlit as st
            value = st.secrets.get(key, default)
            source = f"st.secrets (type={type(value).__name__})"
        except Exception:
            value = default
            source = "default"
    # st.secrets는 TOML 파싱 결과이므로 int/float 등이 올 수 있음
    result = str(value).strip() if value else default
    if key.startswith("KIS_"):
        # 디버그: 값의 앞 4자리만 표시 (보안)
        masked = result[:4] + "****" if len(result) > 4 else result
        from loguru import logger as _env_logger
        _env_logger.info(f"_get_env('{key}') → '{masked}' (len={len(result)}, type_raw={type(value).__name__}) from {source}")
    return result


def get_kis_credentials() -> dict[str, str]:
    """KIS API 인증 정보 반환"""
    load_env()
    return {
        "app_key": _get_env("KIS_APP_KEY"),
        "app_secret": _get_env("KIS_APP_SECRET"),
        "account_no": _get_env("KIS_ACCOUNT_NO"),
        "account_product": _get_env("KIS_ACCOUNT_PRODUCT", "01"),
    }


def get_telegram_credentials() -> dict[str, str]:
    """텔레그램 봇 인증 정보 반환"""
    load_env()
    return {
        "bot_token": _get_env("TELEGRAM_BOT_TOKEN"),
        "chat_id": _get_env("TELEGRAM_CHAT_ID"),
    }


# 싱글톤 설정 인스턴스
_config: dict[str, Any] | None = None


def get_config() -> dict[str, Any]:
    """글로벌 설정 싱글톤"""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reload_config() -> dict[str, Any]:
    """설정 캐시를 무효화하고 settings.yaml을 다시 읽음"""
    global _config
    _config = load_config()
    return _config
