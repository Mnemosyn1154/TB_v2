# src/utils — 유틸리티 모듈

공통 유틸리티로 **다른 모든 계층에서 사용**됩니다. 외부 라이브러리에만 의존합니다.

---

## 모듈 목록

### logger.py — 로깅 설정

**함수**: `setup_logger()`

| 출력 | 형식 | 설정키 |
|------|------|--------|
| 콘솔 (stderr) | 컬러, 시간+레벨+모듈 | `logging.level` |
| 파일 (`logs/trading_bot.log`) | 타임스탬프 포함 전체 | `logging.rotation`, `logging.retention` |

**사용법**: `main.py` 초기화 시 1회 호출. 이후 각 모듈에서 `from loguru import logger` 사용.

---

### notifier.py — 텔레그램 알림

**클래스**: `TelegramNotifier`

| 메서드 | 용도 |
|--------|------|
| `send(message)` | 범용 메시지 전송 |
| `notify_trade(...)` | 매매 체결 알림 (📈/📉) |
| `notify_signal(strategy, signals)` | 전략 신호 발생 알림 (🔔) |
| `notify_risk(message)` | 리스크 경고 (🚨) |
| `notify_daily_summary(summary)` | 일일 리포트 (📊) |
| `notify_error(error)` | 에러 알림 (❌) |

**설정 필요**: `.env`에 `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`  
**미설정 시**: 로그 출력만 수행 (에러 없이 graceful 처리)

**의존**: `python-telegram-bot` (선택적 — 미설치 시 자동 비활성화)

---

## 의존 관계

```
utils/ → 외부 라이브러리만 (loguru, python-telegram-bot)
       ← core/, strategies/, execution/, main.py 에서 사용
```
