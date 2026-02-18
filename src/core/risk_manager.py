"""
AlgoTrader KR — 리스크 매니저

포지션/포트폴리오 레벨 리스크 관리 엔진.
can_open_position() 체크 순서: Kill Switch → 일일 손실 → MDD → 포지션 수 → 종목 비중 → 현금 비중

Depends on:
    - src.core.config (리스크 한도 설정)

Used by:
    - src.execution.executor (주문 전 리스크 검증, 포지션 관리)
    - main.py (리스크 상태 조회)

Modification Guide:
    - 새 리스크 체크 추가: can_open_position()에 조건 추가 + settings.yaml에 파라미터 추가
    - Kill Switch는 반드시 첫 번째 체크로 유지
    - Position/RiskState는 dataclass — 필드 추가 시 기본값 필수
"""
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from loguru import logger

from src.core.config import get_config, DATA_DIR

_KILL_SWITCH_FILE = DATA_DIR / "kill_switch.json"


@dataclass
class Position:
    """개별 포지션"""
    code: str
    market: str
    side: str               # "LONG" or "SHORT" (인버스 ETF 매수 포함)
    quantity: int
    entry_price: float
    current_price: float = 0.0
    strategy: str = ""
    entry_time: str = ""

    @property
    def pnl_pct(self) -> float:
        """수익률 (%)"""
        if self.entry_price == 0:
            return 0.0
        if self.side == "LONG":
            return ((self.current_price - self.entry_price) / self.entry_price) * 100
        else:  # SHORT (인버스 ETF)
            return ((self.entry_price - self.current_price) / self.entry_price) * 100

    @property
    def market_value(self) -> float:
        """현재 평가 금액"""
        return self.current_price * self.quantity


@dataclass
class RiskState:
    """포트폴리오 리스크 상태"""
    total_equity: float = 0.0
    cash: float = 0.0
    daily_pnl: float = 0.0
    peak_equity: float = 0.0
    positions: list[Position] = field(default_factory=list)

    @property
    def drawdown_pct(self) -> float:
        """현재 드로다운 (%)"""
        if self.peak_equity == 0:
            return 0.0
        return ((self.total_equity - self.peak_equity) / self.peak_equity) * 100

    @property
    def cash_pct(self) -> float:
        """현금 비중 (%)"""
        total = self.total_equity + self.cash
        if total == 0:
            return 100.0
        return (self.cash / total) * 100


class RiskManager:
    """리스크 관리 엔진"""

    def __init__(self):
        config = get_config()
        risk_config = config["risk"]

        self.max_position_pct = risk_config["max_position_pct"]
        self.stop_loss_pct = risk_config["stop_loss_pct"]
        self.daily_loss_limit_pct = risk_config["daily_loss_limit_pct"]
        self.max_drawdown_pct = risk_config["max_drawdown_pct"]
        self.max_positions = risk_config["max_positions"]
        self.min_cash_pct = risk_config["min_cash_pct"]

        self.state = RiskState()
        self._kill_switch = self._load_kill_switch()

        logger.info(f"RiskManager 초기화: 손절={self.stop_loss_pct}%, "
                    f"일일한도={self.daily_loss_limit_pct}%, "
                    f"MDD={self.max_drawdown_pct}%")

    # ──────────────────────────────────────────────
    # 주문 전 검증
    # ──────────────────────────────────────────────

    def can_open_position(self, code: str, market_value: float) -> tuple[bool, str]:
        """새 포지션 오픈 가능 여부 검증"""
        # Kill switch 체크
        if self._kill_switch:
            return False, "🚨 Kill switch 활성화됨 — 모든 거래 중단"

        # 일일 손실 한도
        total = self.state.total_equity + self.state.cash
        if total > 0:
            daily_pnl_pct = (self.state.daily_pnl / total) * 100
            if daily_pnl_pct <= self.daily_loss_limit_pct:
                return False, f"일일 손실 한도 도달: {daily_pnl_pct:.1f}% <= {self.daily_loss_limit_pct}%"

        # 최대 드로다운
        if self.state.drawdown_pct <= self.max_drawdown_pct:
            return False, f"최대 드로다운 도달: {self.state.drawdown_pct:.1f}% <= {self.max_drawdown_pct}%"

        # 최대 포지션 수
        if len(self.state.positions) >= self.max_positions:
            return False, f"최대 포지션 수 도달: {len(self.state.positions)} >= {self.max_positions}"

        # 개별 종목 최대 비중
        if total > 0:
            position_pct = (market_value / total) * 100
            if position_pct > self.max_position_pct:
                return False, f"종목 비중 초과: {position_pct:.1f}% > {self.max_position_pct}%"

        # 최소 현금 비중
        remaining_cash = self.state.cash - market_value
        if total > 0:
            new_cash_pct = (remaining_cash / total) * 100
            if new_cash_pct < self.min_cash_pct:
                return False, f"최소 현금 비중 미달: {new_cash_pct:.1f}% < {self.min_cash_pct}%"

        return True, "OK"

    def check_stop_loss(self, position: Position) -> bool:
        """개별 포지션 손절 체크"""
        if position.pnl_pct <= self.stop_loss_pct:
            logger.warning(
                f"🛑 손절 트리거: {position.code} — "
                f"PnL {position.pnl_pct:.1f}% <= {self.stop_loss_pct}%"
            )
            return True
        return False

    # ──────────────────────────────────────────────
    # 포지션 관리
    # ──────────────────────────────────────────────

    def add_position(self, position: Position) -> None:
        """포지션 추가"""
        self.state.positions.append(position)
        logger.info(f"포지션 추가: {position.code} {position.side} x{position.quantity}")

    def remove_position(self, code: str) -> None:
        """포지션 제거"""
        self.state.positions = [p for p in self.state.positions if p.code != code]
        logger.info(f"포지션 제거: {code}")

    def update_prices(self, prices: dict[str, float]) -> None:
        """현재가 업데이트"""
        for pos in self.state.positions:
            if pos.code in prices:
                pos.current_price = prices[pos.code]

    def update_equity(self, total_equity: float, cash: float) -> None:
        """자산 업데이트"""
        self.state.total_equity = total_equity
        self.state.cash = cash
        if total_equity > self.state.peak_equity:
            self.state.peak_equity = total_equity

    # ──────────────────────────────────────────────
    # Kill Switch
    # ──────────────────────────────────────────────

    def activate_kill_switch(self, reason: str = "") -> None:
        """긴급 거래 중단"""
        self._kill_switch = True
        self._save_kill_switch(reason)
        logger.critical(f"🚨 KILL SWITCH 활성화: {reason}")

    def deactivate_kill_switch(self) -> None:
        """거래 재개"""
        self._kill_switch = False
        self._save_kill_switch("")
        logger.info("Kill switch 해제")

    @property
    def is_killed(self) -> bool:
        return self._kill_switch

    # ── Kill Switch 파일 영속화 ──

    @staticmethod
    def _load_kill_switch() -> bool:
        """파일에서 Kill Switch 상태 복원"""
        try:
            if _KILL_SWITCH_FILE.exists():
                data = json.loads(_KILL_SWITCH_FILE.read_text(encoding="utf-8"))
                return data.get("active", False)
        except Exception:
            pass
        return False

    def _save_kill_switch(self, reason: str) -> None:
        """Kill Switch 상태를 파일에 저장"""
        try:
            _KILL_SWITCH_FILE.parent.mkdir(parents=True, exist_ok=True)
            _KILL_SWITCH_FILE.write_text(
                json.dumps({
                    "active": self._kill_switch,
                    "reason": reason,
                    "updated_at": datetime.now().isoformat(),
                }, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning(f"Kill Switch 상태 저장 실패: {e}")

    # ──────────────────────────────────────────────
    # 포지션 사이징
    # ──────────────────────────────────────────────

    def calculate_position_size(self, price: float, market: str = "KR") -> int:
        """적정 포지션 사이즈 계산 (동일 비중 기반)"""
        total = self.state.total_equity + self.state.cash
        if total == 0:
            # fallback: settings의 initial_capital 사용
            config = get_config()
            sim_config = config.get("simulation", {})
            total = float(sim_config.get(
                "initial_capital",
                config.get("backtest", {}).get("initial_capital", 10_000_000),
            ))
            logger.warning(f"equity=0, initial_capital fallback: {total:,.0f}")
        if price == 0:
            return 0

        # 최대 비중의 80%로 보수적 사이징
        target_value = total * (self.max_position_pct / 100) * 0.8
        quantity = int(target_value / price)

        return max(quantity, 0)

    def get_risk_summary(self) -> dict[str, Any]:
        """리스크 요약 리포트"""
        return {
            "total_equity": self.state.total_equity,
            "cash": self.state.cash,
            "cash_pct": f"{self.state.cash_pct:.1f}%",
            "daily_pnl": self.state.daily_pnl,
            "drawdown": f"{self.state.drawdown_pct:.1f}%",
            "positions_count": len(self.state.positions),
            "max_positions": self.max_positions,
            "kill_switch": self._kill_switch,
            "positions": [
                {
                    "code": p.code,
                    "side": p.side,
                    "pnl_pct": f"{p.pnl_pct:.1f}%",
                    "value": p.market_value,
                }
                for p in self.state.positions
            ],
        }
