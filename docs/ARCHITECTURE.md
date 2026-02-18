# Architecture

## 시스템 레이어

```
┌─────────────────────────────────────────────────────────────────┐
│ Layer 4: Web (Next.js)                                          │
│   web/app/page.tsx → components/* → hooks/* → lib/api-client.ts │
│                                                    │            │
│   web/app/api/*/route.ts → lib/python-proxy.ts ────┘            │
└────────────────────────────────────────────────────│────────────┘
                                                     │ HTTP (X-Internal-Secret)
┌────────────────────────────────────────────────────│────────────┐
│ Layer 3: API (FastAPI)                             ▼            │
│   pyapi/main.py → pyapi/routers/* → dashboard/services/*       │
└────────────────────────────────────────────────────│────────────┘
                                                     │ Python import
┌────────────────────────────────────────────────────│────────────┐
│ Layer 2: Core Engine (src/)                        ▼            │
│   strategies/* → execution/* → core/broker → core/data_manager │
└────────────────────────────────────────────────────│────────────┘
                                                     │ HTTPS
┌────────────────────────────────────────────────────│────────────┐
│ Layer 1: External                                  ▼            │
│   KIS Open API (한국투자증권) / Yahoo Finance                    │
└─────────────────────────────────────────────────────────────────┘

별도 진입점:
  CLI (main.py) → Layer 2 직접 접근
```

## 데이터 플로우

### 웹 대시보드 요청 흐름

```
Browser (React component)
  → web/lib/api-client.ts : fetchApi("/portfolio")
    → GET /api/portfolio (Next.js API Route)
      → web/lib/python-proxy.ts : pythonGet("/py/portfolio")
        → GET http://localhost:8000/py/portfolio (FastAPI)
          → pyapi/routers/portfolio.py : get_portfolio()
            → dashboard/services/portfolio_service.py
              → src/core/broker.py : KISBroker → KIS API
```

### CLI 실행 흐름

```
python3 main.py run
  → AlgoTrader.__init__()
    → KISBroker, DataManager, RiskManager, strategies 초기화
  → AlgoTrader.run_once()
    → DataCollector.collect_all() → KISBroker → DataManager(SQLite)
    → Strategy.generate_signals() → TradeSignal[]
    → OrderExecutor.execute_signals()
      → RiskManager.validate() → KISBroker.place_order()
      → TelegramNotifier.send()
```

### 예외 라우트

```
Settings:  Browser → /api/settings → config/settings.yaml 직접 읽기/쓰기 (Python API 없음)
Benchmark: Browser → /api/benchmark → yahoo-finance2 패키지 직접 호출 (Python API 없음)
```

## 인증 체계

### KIS API 인증
- OAuth2 토큰 기반
- 토큰 파일 캐시: `data/kis_token_*.json`
- `src/core/broker.py`의 KISBroker가 토큰 발급/갱신 관리
- SHA-256 해시로 토큰 파일명 결정 (키 변경 시 자동 갱신)

### Next.js ↔ Python API 인증
- `X-Internal-Secret` HTTP 헤더
- 환경변수: `PYTHON_API_SECRET`
- 구현: `pyapi/deps.py` → `verify_secret()`
- 개발 모드: `PYTHON_API_SECRET=""` (빈 값) → 검증 건너뜀

### 환경변수

| 변수 | 위치 | 용도 |
|------|------|------|
| `KIS_APP_KEY` | `.env` | KIS API 앱 키 |
| `KIS_APP_SECRET` | `.env` | KIS API 시크릿 |
| `KIS_ACCOUNT_NO` | `.env` | KIS 계좌번호 |
| `TELEGRAM_BOT_TOKEN` | `.env` | 텔레그램 봇 토큰 |
| `TELEGRAM_CHAT_ID` | `.env` | 텔레그램 채팅 ID |
| `PYTHON_API_SECRET` | `.env`, `web/.env.local` | 내부 API 인증 |
| `PYTHON_API_URL` | `web/.env.local` | Python API URL (기본: http://localhost:8000) |
| `ALLOWED_ORIGINS` | `.env` | CORS 허용 오리진 (콤마 구분) |

## DB 스키마

SQLite: `data/trading_bot.db`

```sql
-- 일일 가격 데이터
CREATE TABLE IF NOT EXISTS daily_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL,
    market TEXT NOT NULL,        -- "KR" | "US"
    date TEXT NOT NULL,          -- "YYYY-MM-DD" or "YYYYMMDD"
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(code, market, date)
);

-- 매매 기록
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy TEXT NOT NULL,       -- "stat_arb", "dual_momentum", etc.
    code TEXT NOT NULL,           -- 종목코드
    market TEXT NOT NULL,         -- "KR" | "US"
    side TEXT NOT NULL,           -- "BUY" | "SELL"
    quantity INTEGER NOT NULL,
    price REAL NOT NULL,
    timestamp TEXT NOT NULL,
    reason TEXT                   -- 매매 사유
);
```

Paper trading 테이블은 `dashboard/services/paper_trading_service.py`에서 별도 관리.

## 전략 플러그인 시스템

```python
# src/strategies/__init__.py
STRATEGY_REGISTRY = {
    "stat_arb": StatArbStrategy,
    "dual_momentum": DualMomentumStrategy,
    "quant_factor": QuantFactorStrategy,
}

def resolve_strategy(config_key: str, strat_config: dict) -> BaseStrategy:
    type_name = strat_config.get("type", config_key)  # type 필드 or config_key
    cls = STRATEGY_REGISTRY[type_name]
    return cls(config_key=config_key)
```

새 전략 추가 절차:
1. `src/strategies/new_strategy.py` — `BaseStrategy` 상속, 추상 메서드 5개 구현
2. `src/strategies/__init__.py` — `STRATEGY_REGISTRY`에 등록
3. `config/settings.yaml` — `strategies:` 아래에 파라미터 추가

## 설정 관리

### config/settings.yaml 구조

```yaml
kis:                          # KIS API 브로커 설정
  base_url, paper_url, live_trading, rate_limit

strategies:                   # 전략별 파라미터
  stat_arb:                   # 페어, z-score, lookback 등
  dual_momentum:              # ETF, 리밸런싱, 모멘텀 기간
  quant_factor:               # 팩터 가중치, 유니버스, top_n

risk:                         # 리스크 관리
  max_position_pct, stop_loss_pct, daily_loss_limit_pct,
  max_drawdown_pct, max_positions, min_cash_pct

notifications:                # 텔레그램 알림
database:                     # SQLite 경로
logging:                      # loguru 설정
scheduler:                    # 한국/미국 장 시간
backtest:                     # 초기 자본, 수수료율, 세율, 슬리피지
```

## 배포 아키텍처

```
┌──────────────────┐     ┌──────────────────┐
│ Cloudflare Pages │     │ Cloudflare Tunnel │
│ (Next.js static) │     │ (reverse proxy)   │
└────────┬─────────┘     └────────┬──────────┘
         │                        │
         ▼                        ▼
┌──────────────────┐     ┌──────────────────┐
│ GitHub Actions   │     │ 서버 (systemd)    │
│ (CI/CD)          │     │ pyapi + tunnel    │
└──────────────────┘     └──────────────────┘
```

- **Cloudflare Pages**: Next.js 빌드 호스팅 (`.github/workflows/deploy.yml`)
- **Cloudflare Tunnel**: Python API를 인터넷에 안전하게 노출 (`deploy/cloudflared/`)
- **systemd 서비스**: `deploy/systemd/`
  - `d2trader-pyapi.service` — FastAPI 프로세스
  - `d2trader-tunnel.service` — Cloudflare Tunnel 프로세스
- **배포 스크립트**: `deploy/deploy.sh` — 자동화된 배포 절차
