from __future__ import annotations

"""RiskManager 전략별 자본 할당 테스트 (PR #16)"""

from unittest.mock import patch

import pytest

from src.core.risk_manager import Position, RiskManager

# 기본 리스크 설정 (할당 없음)
BASE_RISK_CONFIG = {
    "risk": {
        "max_position_pct": 10,
        "stop_loss_pct": -7,
        "daily_loss_limit_pct": -2,
        "max_drawdown_pct": -10,
        "max_positions": 10,
        "min_cash_pct": 20,
    },
}

# 전략별 자본 할당 포함 설정
ALLOC_RISK_CONFIG = {
    "risk": {
        **BASE_RISK_CONFIG["risk"],
        "strategy_allocation": {
            "stat_arb": 0.30,
            "dual_momentum": 0.20,
            "quant_factor": 0.40,
        },
    },
}


def _make_rm(config: dict) -> RiskManager:
    with patch("src.core.risk_manager.get_config", return_value=config), \
         patch("src.core.risk_manager._KILL_SWITCH_FILE") as mock_path:
        mock_path.exists.return_value = False
        return RiskManager()


class TestRiskManagerAllocation:
    def test_init_without_allocation(self):
        """할당 설정 없으면 빈 dict, 에러 없음"""
        rm = _make_rm(BASE_RISK_CONFIG)
        assert rm.strategy_allocation == {}

    def test_init_with_allocation(self):
        """할당 설정 로딩 확인"""
        rm = _make_rm(ALLOC_RISK_CONFIG)
        assert rm.strategy_allocation["stat_arb"] == 0.30
        assert rm.strategy_allocation["quant_factor"] == 0.40

    def test_get_strategy_budget(self):
        """전략 예산 계산: total * pct"""
        rm = _make_rm(ALLOC_RISK_CONFIG)
        rm.update_equity(5_000_000, 5_000_000)  # total = 10M
        budget = rm._get_strategy_budget("stat_arb")
        assert budget == 10_000_000 * 0.30  # 3M

    def test_get_strategy_budget_unknown_strategy(self):
        """미등록 전략은 None 반환"""
        rm = _make_rm(ALLOC_RISK_CONFIG)
        rm.update_equity(5_000_000, 5_000_000)
        assert rm._get_strategy_budget("unknown") is None

    def test_get_strategy_used(self):
        """전략별 사용 금액 = 해당 전략 포지션 평가금 합계"""
        rm = _make_rm(ALLOC_RISK_CONFIG)
        rm.state.positions = [
            Position("A", "KR", "LONG", 10, 100, current_price=110, strategy="stat_arb"),
            Position("B", "KR", "LONG", 5, 200, current_price=200, strategy="dual_momentum"),
            Position("C", "KR", "LONG", 20, 50, current_price=55, strategy="stat_arb"),
        ]
        used = rm._get_strategy_used("stat_arb")
        assert used == (110 * 10) + (55 * 20)  # 1100 + 1100 = 2200

    def test_can_open_position_within_budget(self):
        """예산 내 포지션 오픈 허용"""
        rm = _make_rm(ALLOC_RISK_CONFIG)
        rm.update_equity(5_000_000, 5_000_000)
        rm.state.peak_equity = 5_000_000
        ok, msg = rm.can_open_position("AAA", 500_000, strategy="stat_arb")
        assert ok is True
        assert msg == "OK"

    def test_can_open_position_exceeds_budget(self):
        """예산 초과 시 거부"""
        rm = _make_rm(ALLOC_RISK_CONFIG)
        rm.update_equity(5_000_000, 5_000_000)  # total = 10M, stat_arb budget = 3M
        rm.state.peak_equity = 5_000_000
        # 이미 2.5M 사용 중
        rm.state.positions = [
            Position("X", "KR", "LONG", 100, 25000, current_price=25000, strategy="stat_arb"),
        ]
        # 1M 추가 → 2.5M + 1M = 3.5M > 3M budget
        ok, msg = rm.can_open_position("YYY", 1_000_000, strategy="stat_arb")
        assert ok is False
        assert "전략 자본 한도 초과" in msg

    def test_can_open_position_no_allocation(self):
        """할당 설정 없으면 전략 한도 체크 스킵 (하위 호환)"""
        rm = _make_rm(BASE_RISK_CONFIG)
        rm.update_equity(5_000_000, 5_000_000)
        rm.state.peak_equity = 5_000_000
        ok, msg = rm.can_open_position("AAA", 500_000, strategy="stat_arb")
        assert ok is True

    def test_calculate_position_size_limited_by_budget(self):
        """포지션 사이징이 전략 잔여 예산 이내로 제한"""
        rm = _make_rm(ALLOC_RISK_CONFIG)
        rm.update_equity(5_000_000, 5_000_000)  # total=10M, stat_arb budget=3M
        # 이미 2.9M 사용 → 잔여 100K
        rm.state.positions = [
            Position("X", "KR", "LONG", 100, 29000, current_price=29000, strategy="stat_arb"),
        ]
        # price=50000 → 일반 사이징이면 ~80K (10M * 10% * 80% / 50000 = 16주)
        # but budget remaining = 100K → 100K / 50000 = 2주
        qty = rm.calculate_position_size(50000, "KR", strategy="stat_arb")
        assert qty <= 2

    def test_risk_summary_includes_allocation(self):
        """get_risk_summary에 strategy_allocation 키 존재"""
        rm = _make_rm(ALLOC_RISK_CONFIG)
        rm.update_equity(5_000_000, 5_000_000)
        rm.state.peak_equity = 5_000_000
        summary = rm.get_risk_summary()
        assert "strategy_allocation" in summary
        assert "stat_arb" in summary["strategy_allocation"]
        alloc = summary["strategy_allocation"]["stat_arb"]
        assert alloc["allocated_pct"] == 30.0
        assert "used_pct" in alloc
        assert "remaining" in alloc
