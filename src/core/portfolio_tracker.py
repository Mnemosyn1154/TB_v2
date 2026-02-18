"""
AlgoTrader KR — 시뮬레이션 포트폴리오 트래커

시뮬레이션 모드에서 포지션과 현금을 SQLite에 영속화합니다.
DataManager의 DB 엔진을 공유하여 trading_bot.db에 저장합니다.

Depends on:
    - src.core.config (DATA_DIR, 설정)
    - sqlalchemy (DB 접근)

Used by:
    - src.execution.executor (시뮬레이션 매매 시 포지션/현금 업데이트)
    - dashboard.services.portfolio_service (포트폴리오 조회)
    - src.core.risk_manager (스타트업 시 상태 동기화)

Modification Guide:
    - sim_positions 필드 추가: _init_tables()의 CREATE TABLE + add_position() 파라미터 수정
    - 새 설정 키 추가: get_setting()/set_setting()으로 접근
"""
from datetime import datetime

from loguru import logger
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.core.config import get_config, DATA_DIR


class PortfolioTracker:
    """시뮬레이션 포트폴리오 영속 관리"""

    def __init__(self, engine: Engine | None = None):
        if engine is not None:
            self.engine = engine
        else:
            db_path = DATA_DIR / "trading_bot.db"
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            self.engine = create_engine(f"sqlite:///{db_path}")

        self._init_tables()

    def _init_tables(self) -> None:
        """sim_positions, sim_portfolio 테이블 생성 (멱등)"""
        with self.engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS sim_positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL UNIQUE,
                    market TEXT NOT NULL,
                    side TEXT NOT NULL DEFAULT 'LONG',
                    quantity INTEGER NOT NULL,
                    entry_price REAL NOT NULL,
                    current_price REAL NOT NULL DEFAULT 0,
                    strategy TEXT NOT NULL DEFAULT '',
                    entry_time TEXT NOT NULL,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS sim_portfolio (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()

    # ──────────────────────────────────────────────
    # 설정 관리 (키-값)
    # ──────────────────────────────────────────────

    def get_setting(self, key: str, default: str = "") -> str:
        """sim_portfolio 키-값 조회"""
        with self.engine.connect() as conn:
            row = conn.execute(
                text("SELECT value FROM sim_portfolio WHERE key = :key"),
                {"key": key},
            ).fetchone()
        return row[0] if row else default

    def set_setting(self, key: str, value: str) -> None:
        """sim_portfolio 키-값 저장 (UPSERT)"""
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO sim_portfolio (key, value, updated_at)
                VALUES (:key, :value, :now)
                ON CONFLICT(key) DO UPDATE SET value = :value, updated_at = :now
            """), {"key": key, "value": value, "now": datetime.now().isoformat()})
            conn.commit()

    def get_initial_capital(self) -> float:
        """초기 자본금 조회"""
        stored = self.get_setting("initial_capital")
        if stored:
            return float(stored)
        config = get_config()
        return float(config.get("simulation", {}).get(
            "initial_capital",
            config.get("backtest", {}).get("initial_capital", 10_000_000),
        ))

    def set_initial_capital(self, amount: float) -> None:
        """초기 자본금 설정 — 현금 리셋 + 포지션 전체 삭제"""
        with self.engine.connect() as conn:
            now = datetime.now().isoformat()
            conn.execute(text("""
                INSERT INTO sim_portfolio (key, value, updated_at)
                VALUES ('initial_capital', :val, :now)
                ON CONFLICT(key) DO UPDATE SET value = :val, updated_at = :now
            """), {"val": str(amount), "now": now})
            conn.execute(text("""
                INSERT INTO sim_portfolio (key, value, updated_at)
                VALUES ('cash', :val, :now)
                ON CONFLICT(key) DO UPDATE SET value = :val, updated_at = :now
            """), {"val": str(amount), "now": now})
            conn.execute(text("DELETE FROM sim_positions"))
            conn.commit()
        logger.info(f"초기 자본금 설정: {amount:,.0f} (포지션 초기화)")

    def get_cash(self) -> float:
        """현재 현금 잔고"""
        stored = self.get_setting("cash")
        if stored:
            return float(stored)
        return self.get_initial_capital()

    def set_cash(self, amount: float) -> None:
        """현금 잔고 업데이트"""
        self.set_setting("cash", str(amount))

    # ──────────────────────────────────────────────
    # 포지션 CRUD
    # ──────────────────────────────────────────────

    def add_position(self, code: str, market: str, side: str,
                     quantity: int, entry_price: float,
                     strategy: str = "", entry_time: str = "") -> None:
        """포지션 추가 (동일 code 존재 시 교체)"""
        if not entry_time:
            entry_time = datetime.now().isoformat()
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO sim_positions
                    (code, market, side, quantity, entry_price, current_price, strategy, entry_time, updated_at)
                VALUES (:code, :market, :side, :qty, :ep, :ep, :strat, :et, :now)
                ON CONFLICT(code) DO UPDATE SET
                    market = :market, side = :side, quantity = :qty,
                    entry_price = :ep, current_price = :ep,
                    strategy = :strat, entry_time = :et, updated_at = :now
            """), {
                "code": code, "market": market, "side": side,
                "qty": quantity, "ep": entry_price,
                "strat": strategy, "et": entry_time,
                "now": datetime.now().isoformat(),
            })
            conn.commit()

    def remove_position(self, code: str) -> None:
        """포지션 삭제"""
        with self.engine.connect() as conn:
            conn.execute(
                text("DELETE FROM sim_positions WHERE code = :code"),
                {"code": code},
            )
            conn.commit()

    def get_position(self, code: str) -> dict | None:
        """단일 포지션 조회"""
        with self.engine.connect() as conn:
            row = conn.execute(
                text("SELECT code, market, side, quantity, entry_price, "
                     "current_price, strategy, entry_time FROM sim_positions "
                     "WHERE code = :code"),
                {"code": code},
            ).fetchone()
        if not row:
            return None
        return dict(zip(
            ["code", "market", "side", "quantity", "entry_price",
             "current_price", "strategy", "entry_time"],
            row,
        ))

    def get_all_positions(self) -> list[dict]:
        """모든 포지션 조회"""
        with self.engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT code, market, side, quantity, entry_price, "
                "current_price, strategy, entry_time FROM sim_positions"
            )).fetchall()
        cols = ["code", "market", "side", "quantity", "entry_price",
                "current_price", "strategy", "entry_time"]
        return [dict(zip(cols, row)) for row in rows]

    def update_position_price(self, code: str, current_price: float) -> None:
        """포지션 현재가 업데이트"""
        with self.engine.connect() as conn:
            conn.execute(text("""
                UPDATE sim_positions
                SET current_price = :price, updated_at = :now
                WHERE code = :code
            """), {
                "code": code,
                "price": current_price,
                "now": datetime.now().isoformat(),
            })
            conn.commit()

    # ──────────────────────────────────────────────
    # 매매 시뮬레이션
    # ──────────────────────────────────────────────

    def execute_buy(self, code: str, market: str, quantity: int,
                    price: float, strategy: str = "") -> bool:
        """
        매수 실행: 현금 차감 + 포지션 추가.
        현금 부족이면 False.
        """
        cost = price * quantity
        cash = self.get_cash()
        if cash < cost:
            logger.warning(f"시뮬레이션 매수 실패 — 현금 부족: "
                           f"필요 {cost:,.0f}, 보유 {cash:,.0f}")
            return False

        self.set_cash(cash - cost)
        self.add_position(code, market, "LONG", quantity, price, strategy)
        logger.info(f"시뮬레이션 매수: {code} x{quantity} @ {price:,.2f} "
                    f"(비용 {cost:,.0f}, 잔여 현금 {cash - cost:,.0f})")
        return True

    def execute_sell(self, code: str, price: float) -> float:
        """
        매도 실행: 포지션 제거 + 현금 가산.
        반환: 매도 수입 금액. 포지션 미보유 시 0.0.
        """
        pos = self.get_position(code)
        if not pos:
            logger.warning(f"시뮬레이션 매도 실패 — 포지션 없음: {code}")
            return 0.0

        proceeds = price * pos["quantity"]
        cash = self.get_cash()
        self.set_cash(cash + proceeds)
        self.remove_position(code)
        logger.info(f"시뮬레이션 매도: {code} x{pos['quantity']} @ {price:,.2f} "
                    f"(수입 {proceeds:,.0f}, 잔여 현금 {cash + proceeds:,.0f})")
        return proceeds

    # ──────────────────────────────────────────────
    # 조회
    # ──────────────────────────────────────────────

    def get_portfolio_summary(self) -> dict:
        """포트폴리오 요약"""
        positions = self.get_all_positions()
        cash = self.get_cash()
        total_equity = sum(p["current_price"] * p["quantity"] for p in positions)
        return {
            "initial_capital": self.get_initial_capital(),
            "cash": cash,
            "positions": positions,
            "total_equity": total_equity,
            "total_value": cash + total_equity,
        }

    # ──────────────────────────────────────────────
    # 리셋
    # ──────────────────────────────────────────────

    def reset(self) -> None:
        """포트폴리오 리셋: 포지션 삭제 + 현금을 초기 자본금으로 복원"""
        capital = self.get_initial_capital()
        with self.engine.connect() as conn:
            conn.execute(text("DELETE FROM sim_positions"))
            conn.execute(text("""
                INSERT INTO sim_portfolio (key, value, updated_at)
                VALUES ('cash', :val, :now)
                ON CONFLICT(key) DO UPDATE SET value = :val, updated_at = :now
            """), {"val": str(capital), "now": datetime.now().isoformat()})
            conn.commit()
        logger.info(f"포트폴리오 리셋: 현금 {capital:,.0f}")


def sync_risk_manager(risk_manager, tracker: PortfolioTracker) -> None:
    """PortfolioTracker의 영속 상태를 RiskManager 인메모리 상태에 동기화"""
    from src.core.risk_manager import Position

    positions = tracker.get_all_positions()
    cash = tracker.get_cash()

    risk_manager.state.positions = [
        Position(
            code=p["code"],
            market=p["market"],
            side=p["side"],
            quantity=p["quantity"],
            entry_price=p["entry_price"],
            current_price=p["current_price"],
            strategy=p.get("strategy", ""),
            entry_time=p.get("entry_time", ""),
        )
        for p in positions
    ]

    total_equity = sum(p["current_price"] * p["quantity"] for p in positions)
    risk_manager.update_equity(total_equity, cash)
    logger.info(f"RiskManager 동기화: 포지션 {len(positions)}개, "
                f"현금 {cash:,.0f}, 주식평가 {total_equity:,.0f}")
