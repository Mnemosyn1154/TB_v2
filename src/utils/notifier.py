"""
AlgoTrader KR — 텔레그램 알림 봇

매매 체결, 전략 신호, 리스크 경고, 일일 리포트를 텔레그램으로 전송합니다.
python-telegram-bot 미설치 시 자동 비활성화 (에러 없이 로그만 출력).

Depends on:
    - src.core.config (텔레그램 인증 정보)
    - python-telegram-bot (선택적 의존성)

Used by:
    - src.execution.executor (매매/에러 알림)
    - main.py (전략 신호 알림)

Modification Guide:
    - 새 알림 유형 추가: notify_xxx() 메서드 추가, HTML 형식 유지
    - 알림 채널 추가 (Slack 등): TelegramNotifier와 동일 인터페이스로 새 클래스 생성
"""
import asyncio
from typing import Any

from loguru import logger

from src.core.config import get_telegram_credentials

# python-telegram-bot은 선택적 의존성
try:
    from telegram import Bot
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logger.warning("python-telegram-bot 미설치 — 텔레그램 알림 비활성화")


class TelegramNotifier:
    """텔레그램 봇 알림"""

    def __init__(self):
        self.enabled = False
        creds = get_telegram_credentials()
        self.bot_token = creds["bot_token"]
        self.chat_id = creds["chat_id"]

        if TELEGRAM_AVAILABLE and self.bot_token and self.chat_id:
            self.bot = Bot(token=self.bot_token)
            self.enabled = True
            logger.info("텔레그램 알림 활성화")
        else:
            self.bot = None
            logger.info("텔레그램 알림 비활성화 (토큰/채팅ID 미설정)")

    async def _send_async(self, message: str, parse_mode: str = "HTML") -> None:
        """비동기 메시지 전송"""
        if not self.enabled or self.bot is None:
            return

        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=parse_mode,
            )
        except Exception as e:
            logger.error(f"텔레그램 전송 실패: {e}")

    def send(self, message: str) -> None:
        """동기 메시지 전송"""
        if not self.enabled:
            logger.info(f"[알림 비활성] {message}")
            return

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(self._send_async(message))
            else:
                loop.run_until_complete(self._send_async(message))
        except RuntimeError:
            asyncio.run(self._send_async(message))

    # ──────────────────────────────────────────────
    # 편의 메서드
    # ──────────────────────────────────────────────

    def notify_trade(self, strategy: str, code: str, side: str,
                     quantity: int, price: float, reason: str = "") -> None:
        """매매 알림"""
        emoji = "📈" if side == "BUY" else "📉"
        msg = (
            f"{emoji} <b>매매 체결</b>\n"
            f"전략: {strategy}\n"
            f"종목: {code}\n"
            f"방향: {side}\n"
            f"수량: {quantity}\n"
            f"가격: {price:,.0f}\n"
        )
        if reason:
            msg += f"사유: {reason}\n"
        self.send(msg)

    def notify_signal(self, strategy: str, signals: list) -> None:
        """전략 신호 알림"""
        if not signals:
            return

        lines = [f"🔔 <b>{strategy} 신호 발생</b>"]
        for s in signals:
            lines.append(f"  • {s}")
        self.send("\n".join(lines))

    def notify_risk(self, message: str) -> None:
        """리스크 경고 알림"""
        self.send(f"🚨 <b>리스크 경고</b>\n{message}")

    def notify_daily_summary(self, summary: dict[str, Any]) -> None:
        """일일 리포트"""
        msg = (
            f"📊 <b>일일 리포트</b>\n"
            f"총 자산: {summary.get('total_value', 0):,.0f}\n"
            f"현금: {summary.get('cash', 0):,.0f} ({summary.get('cash_pct', '0%')})\n"
            f"일일 P&L: {summary.get('daily_pnl', 0):,.0f}\n"
            f"포지션: {summary.get('positions_count', 0)}개\n"
            f"드로다운: {summary.get('drawdown', '0%')}\n"
        )
        self.send(msg)

    def notify_error(self, error: str) -> None:
        """에러 알림"""
        self.send(f"❌ <b>에러 발생</b>\n{error}")
