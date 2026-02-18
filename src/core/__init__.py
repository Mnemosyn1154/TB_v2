"""
AlgoTrader KR — Core 패키지

시스템 핵심 인프라: API 연동, 데이터 관리, 리스크 관리, 설정 로더.

공개 API:
    - KISBroker: KIS Open API 래퍼
    - DataManager: 시세 수집 + SQLite CRUD
    - RiskManager: 리스크 관리 엔진
    - Position: 개별 포지션 데이터 클래스
    - get_config: settings.yaml 싱글톤 로더
"""
from src.core.config import get_config, get_kis_credentials, load_env
from src.core.broker import KISBroker
from src.core.data_manager import DataManager
from src.core.risk_manager import RiskManager, Position, RiskState

__all__ = [
    "get_config",
    "get_kis_credentials",
    "load_env",
    "KISBroker",
    "DataManager",
    "RiskManager",
    "Position",
    "RiskState",
]
