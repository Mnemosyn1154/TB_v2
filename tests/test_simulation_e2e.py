from __future__ import annotations

"""시뮬레이션 매수→가격변동→매도→P&L E2E 테스트"""

import pytest


class TestSimulationBuySellPnL:
    """PortfolioTracker 매수→매도 전체 흐름"""

    def test_buy_deducts_cash(self, tracker):
        """매수 시 현금이 차감된다"""
        ok = tracker.execute_buy("MSFT", "US", 10, 400.0, "test")
        assert ok is True
        assert tracker.get_cash() == pytest.approx(10_000_000 - 4_000)

    def test_buy_creates_position(self, tracker):
        """매수 시 포지션이 생성된다"""
        tracker.execute_buy("MSFT", "US", 10, 400.0, "test")
        pos = tracker.get_position("MSFT")
        assert pos is not None
        assert pos["quantity"] == 10
        assert pos["entry_price"] == 400.0
        assert pos["market"] == "US"

    def test_buy_insufficient_cash(self, tracker):
        """현금 부족 시 매수 실패"""
        ok = tracker.execute_buy("AAPL", "US", 100_000, 200.0, "test")
        assert ok is False
        assert tracker.get_cash() == 10_000_000
        assert tracker.get_position("AAPL") is None

    def test_sell_adds_cash(self, tracker):
        """매도 시 현금이 가산된다"""
        tracker.execute_buy("MSFT", "US", 10, 400.0, "test")
        cash_after_buy = tracker.get_cash()
        proceeds = tracker.execute_sell("MSFT", 450.0)
        assert proceeds == pytest.approx(4_500)
        assert tracker.get_cash() == pytest.approx(cash_after_buy + 4_500)

    def test_sell_removes_position(self, tracker):
        """매도 시 포지션이 제거된다"""
        tracker.execute_buy("MSFT", "US", 10, 400.0, "test")
        tracker.execute_sell("MSFT", 450.0)
        assert tracker.get_position("MSFT") is None

    def test_sell_nonexistent_position(self, tracker):
        """미보유 종목 매도 시 0 반환"""
        proceeds = tracker.execute_sell("FAKE", 100.0)
        assert proceeds == 0.0

    def test_buy_sell_profit(self, tracker):
        """매수→매도 수익 계산"""
        initial = tracker.get_cash()
        tracker.execute_buy("MSFT", "US", 10, 400.0, "test")
        tracker.execute_sell("MSFT", 450.0)
        # 수익 = (450-400) * 10 = 500
        assert tracker.get_cash() == pytest.approx(initial + 500)

    def test_buy_sell_loss(self, tracker):
        """매수→매도 손실 계산"""
        initial = tracker.get_cash()
        tracker.execute_buy("MSFT", "US", 10, 400.0, "test")
        tracker.execute_sell("MSFT", 350.0)
        # 손실 = (350-400) * 10 = -500
        assert tracker.get_cash() == pytest.approx(initial - 500)

    def test_price_update(self, tracker):
        """현재가 업데이트 후 포트폴리오 요약 반영"""
        tracker.execute_buy("MSFT", "US", 10, 400.0, "test")
        tracker.update_position_price("MSFT", 450.0)
        pos = tracker.get_position("MSFT")
        assert pos["current_price"] == 450.0

        summary = tracker.get_portfolio_summary()
        assert summary["total_equity"] == pytest.approx(4_500)

    def test_multiple_positions(self, tracker):
        """복수 포지션 관리"""
        tracker.execute_buy("MSFT", "US", 10, 400.0, "test")
        tracker.execute_buy("AAPL", "US", 5, 200.0, "test")
        assert len(tracker.get_all_positions()) == 2
        assert tracker.get_cash() == pytest.approx(10_000_000 - 4_000 - 1_000)

    def test_snapshot(self, tracker):
        """스냅샷 저장 및 조회"""
        tracker.execute_buy("MSFT", "US", 10, 400.0, "test")
        tracker.update_position_price("MSFT", 450.0)
        tracker.save_snapshot()

        snapshots = tracker.get_snapshots()
        assert len(snapshots) == 1
        s = snapshots[0]
        assert s["equity"] == pytest.approx(4_500)
        assert s["total_value"] == pytest.approx(s["cash"] + s["equity"])

    def test_reset(self, tracker):
        """리셋 시 포지션 삭제 + 현금 복원"""
        tracker.execute_buy("MSFT", "US", 10, 400.0, "test")
        tracker.reset()
        assert tracker.get_all_positions() == []
        assert tracker.get_cash() == 10_000_000

    def test_transaction_atomicity(self, tracker):
        """매수 트랜잭션: 성공 시 현금+포지션 모두 반영"""
        tracker.execute_buy("MSFT", "US", 10, 400.0, "test")
        # 둘 다 반영되어야 함
        assert tracker.get_position("MSFT") is not None
        assert tracker.get_cash() < 10_000_000
