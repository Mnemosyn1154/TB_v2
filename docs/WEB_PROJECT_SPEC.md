# WEB_PROJECT_SPEC.md — D2trader 개발 스펙

> 새 프로젝트 **D2trader**의 기술 스택, 아키텍처, API 설계, 구현 체크리스트를 정의합니다.
> 디자인 토큰과 페이지 와이어프레임은 [`DESIGN_SYSTEM.md`](./DESIGN_SYSTEM.md)를 참조합니다.

---

## 1. 프로젝트 개요

| 항목 | 내용 |
|------|------|
| 프로젝트명 | **D2trader** |
| 목적 | AlgoTrader KR의 차세대 웹 대시보드 |
| 프론트엔드 | Next.js 14+ (App Router) + TypeScript |
| 백엔드 | **하이브리드** — Next.js API Routes + 경량 Python API |
| 배포 | Cloudflare Pages (Next.js) + Cloudflare Tunnel (Python) |
| 기존 코드 | `src/`, `config/`, `main.py` — Python 필수 부분만 API로 노출 |

---

## 2. 아키텍처

### 2.1 설계 원칙: Python은 필수인 곳에만

prism-insight의 대시보드는 Python이 생성한 JSON 파일을 프론트가 읽는 구조이다.
D2trader도 이 원칙을 따른다: **Next.js가 할 수 있는 것은 Next.js에서 처리**하고,
Python이 반드시 필요한 기능만 경량 Python API로 분리한다.

#### Python이 필수인 기능 (대체 불가)

| 기능 | 이유 |
|------|------|
| KIS API 잔고/주문 | 기존 `KISBroker` (OAuth2 토큰, rate limiting) |
| 전략 시그널 생성 | numpy, pandas, scipy, statsmodels 의존 |
| 백테스트 엔진 실행 | pandas 기반 이벤트 드리븐 시뮬레이터 |
| 모의거래 주문 실행 | `OrderExecutor` + `RiskManager` |
| Kill Switch 제어 | `RiskManager` → JSON 영속화 |
| 데이터 수집 | `DataCollector` → KIS API → SQLite |

#### Next.js에서 직접 처리하는 기능

| 기능 | 방법 |
|------|------|
| 벤치마크 조회 (KOSPI, S&P500) | Next.js API Route → Yahoo Finance API 직접 호출 |
| 설정 읽기/쓰기 (settings.yaml) | Next.js API Route → `js-yaml` 라이브러리 |
| 차트 렌더링 | Recharts (프론트에서 직접 — Plotly 불필요) |
| 통화/날짜 포맷 | TypeScript 유틸리티 함수 |
| 다크/라이트 모드 | next-themes (클라이언트) |
| 정적 데이터 표시 | React 컴포넌트 (서버 불필요) |

### 2.2 전체 구조

```
┌─ 사용자 브라우저 ──────────────────────────────────────────┐
│  D2trader (Next.js)                                        │
│  https://d2trader.your-domain.com                          │
└───────────────────┬────────────────────────────────────────┘
                    │ HTTPS
┌───────────────────▼────────────────────────────────────────┐
│  Cloudflare                                                 │
│  ┌─ Pages ───────────────┐  ┌─ Tunnel ──────────────────┐ │
│  │ Next.js 풀스택 배포    │  │ Python API ↔ 외부 접속    │ │
│  │ (SSR + API Routes)    │  │ (KIS/전략/백테스트 전용)   │ │
│  └───────────────────────┘  └──────────┬────────────────┘ │
└─────────────────────────────────────────┼──────────────────┘
                                          │
┌─ 로컬 서버 / VPS ──────────────────────▼──────────────────┐
│                                                             │
│  ┌─ Python API (FastAPI, 경량) ─────────────────────────┐  │
│  │  /py/portfolio     → KIS API 잔고 조회                │  │
│  │  /py/backtest      → 백테스트 엔진 실행               │  │
│  │  /py/bot/run       → 전략 실행 + 주문                 │  │
│  │  /py/bot/collect   → 데이터 수집                      │  │
│  │  /py/bot/kill      → Kill Switch 제어                 │  │
│  │  /py/signals       → 시그널 dry-run                   │  │
│  │  /py/paper/*       → 모의거래 세션/실행               │  │
│  └──────────┬────────────────────────────────────────────┘  │
│             │                                               │
│  ┌──────────▼────────────────────────────────────────────┐  │
│  │  기존 src/ (수정 없음)                                 │  │
│  │  strategies/ · core/ · execution/ · backtest/          │  │
│  │  config/settings.yaml · data/trading_bot.db            │  │
│  └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 통신 흐름

```
Next.js 프론트 (브라우저)
    │
    │  ── Next.js API Routes (서버사이드, Python 불필요) ──
    ├─ /api/benchmark    → Yahoo Finance API 직접 호출
    ├─ /api/settings     → settings.yaml 읽기/쓰기 (js-yaml)
    │
    │  ── Python API 프록시 (Next.js → Python) ──
    ├─ /api/portfolio    → Next.js API Route → Python /py/portfolio
    ├─ /api/backtest     → Next.js API Route → Python /py/backtest
    ├─ /api/bot/*        → Next.js API Route → Python /py/bot/*
    ├─ /api/signals      → Next.js API Route → Python /py/signals
    └─ /api/paper/*      → Next.js API Route → Python /py/paper/*
```

> **프론트는 항상 `/api/*`만 호출한다.**
> Python이 필요한 요청은 Next.js API Route가 Python으로 프록시한다.
> 이렇게 하면 프론트 코드에서 Python 서버 URL을 직접 알 필요가 없고,
> API Key도 서버사이드에서만 처리할 수 있다.

### 2.4 인증

```
브라우저 → Next.js API Route:  세션/쿠키 기반 (또는 단순 API Key 헤더)
Next.js  → Python API:        내부 통신용 시크릿 (PYTHON_API_SECRET)
```

프론트에서 API Key를 `NEXT_PUBLIC_`으로 노출하지 않는다.
Next.js 서버사이드에서만 Python API 시크릿을 사용한다.

---

## 3. 기술 스택

### 3.1 프론트엔드 + Next.js API

| 패키지 | 용도 |
|--------|------|
| next 14+ | React 프레임워크 (App Router + API Routes) |
| react 18+ | UI 라이브러리 |
| typescript 5+ | 타입 안전성 |
| tailwindcss 3.4+ | 유틸리티 CSS |
| shadcn/ui | 기본 UI 컴포넌트 (Card, Table, Button, Tabs, Badge, ...) |
| recharts 2+ | 차트 (LineChart, BarChart, AreaChart) |
| lucide-react | 아이콘 |
| next-themes | 다크/라이트 모드 |
| geist | 폰트 (Sans + Mono) |
| js-yaml | settings.yaml 읽기/쓰기 (Next.js API Route) |
| yahoo-finance2 | 벤치마크 시세 조회 (Next.js API Route) |

### 3.2 Python API (경량)

| 패키지 | 용도 |
|--------|------|
| fastapi | REST API |
| uvicorn | ASGI 서버 |
| pydantic 2+ | 요청/응답 검증 |

> 기존 `requirements.txt`에 fastapi + uvicorn만 추가.

### 3.3 인프라 (Cloudflare)

| 서비스 | 용도 | 비용 |
|--------|------|------|
| Cloudflare Pages | Next.js 풀스택 배포 (SSR + API Routes) | 무료 |
| Cloudflare Tunnel | 로컬 Python API를 HTTPS로 노출 | 무료 |
| Cloudflare Workers | (선택) 인증 프록시, Rate Limiting | 이미 보유 |

---

## 4. 디렉토리 구조

### 4.1 Next.js 프로젝트 (`web/`)

```
web/
├── app/
│   ├── layout.tsx                 # 루트 레이아웃 (ThemeProvider, 폰트, 메타)
│   ├── page.tsx                   # 메인 페이지 (탭 라우팅 허브)
│   ├── globals.css                # 디자인 토큰 (DESIGN_SYSTEM.md 참조)
│   ├── favicon.ico
│   └── api/                       # ── Next.js API Routes ──
│       ├── benchmark/
│       │   └── route.ts           # Yahoo Finance 직접 호출
│       ├── settings/
│       │   └── route.ts           # settings.yaml 읽기/쓰기
│       ├── portfolio/
│       │   └── route.ts           # → Python /py/portfolio 프록시
│       ├── backtest/
│       │   └── route.ts           # → Python /py/backtest 프록시
│       ├── bot/
│       │   ├── run/route.ts       # → Python /py/bot/run 프록시
│       │   ├── collect/route.ts   # → Python /py/bot/collect 프록시
│       │   ├── kill-switch/route.ts
│       │   └── status/route.ts
│       ├── signals/
│       │   └── route.ts           # → Python /py/signals 프록시
│       └── paper/
│           ├── sessions/route.ts
│           ├── execute/route.ts
│           └── trades/route.ts
├── components/
│   ├── ui/                        # shadcn/ui (자동 생성)
│   │   ├── card.tsx
│   │   ├── button.tsx
│   │   ├── table.tsx
│   │   ├── tabs.tsx
│   │   ├── badge.tsx
│   │   ├── dialog.tsx
│   │   └── ...
│   ├── layout/
│   │   ├── dashboard-header.tsx   # 탭 네비 + 마켓 선택 + 모드 표시
│   │   └── project-footer.tsx
│   ├── common/
│   │   ├── metrics-card.tsx       # KPI 카드 (그라데이션 + 아이콘)
│   │   ├── market-selector.tsx    # KR/US 토글
│   │   ├── loading-spinner.tsx
│   │   └── error-boundary.tsx
│   ├── portfolio/                 # ① 자산 현황
│   │   ├── portfolio-kpis.tsx
│   │   ├── strategy-cards.tsx
│   │   ├── holdings-table.tsx
│   │   └── risk-indicators.tsx
│   ├── benchmark/                 # ② 벤치마크 비교
│   │   ├── benchmark-chart.tsx
│   │   ├── alpha-beta-cards.tsx
│   │   └── strategy-vs-market.tsx
│   ├── strategy/                  # ③ 전략 설정
│   │   ├── strategy-list.tsx
│   │   ├── strategy-editor.tsx
│   │   └── universe-viewer.tsx
│   ├── backtest/                  # ④ 백테스트
│   │   ├── backtest-form.tsx
│   │   ├── backtest-kpis.tsx
│   │   ├── equity-curve.tsx
│   │   ├── drawdown-chart.tsx
│   │   ├── monthly-heatmap.tsx
│   │   ├── pnl-distribution.tsx
│   │   └── trade-table.tsx
│   ├── paper/                     # ⑤ 모의거래
│   │   ├── signal-preview.tsx
│   │   ├── paper-session.tsx
│   │   └── paper-trades.tsx
│   └── control/                   # ⑥ 실행 & 제어
│       ├── mode-toggle.tsx
│       ├── kill-switch.tsx
│       ├── execution-status.tsx
│       └── log-viewer.tsx
├── hooks/
│   ├── use-api.ts                 # fetch 래퍼 (에러, 로딩 상태)
│   ├── use-portfolio.ts           # 포트폴리오 + 5분 폴링
│   ├── use-benchmark.ts           # 벤치마크 + 기간 선택
│   └── use-interval.ts            # 자동 갱신 훅
├── lib/
│   ├── api-client.ts              # /api/* 호출 함수 모음
│   ├── python-proxy.ts            # Python API 프록시 헬퍼 (서버사이드)
│   ├── formatters.ts              # 통화, 퍼센트, 날짜 포맷
│   └── constants.ts               # 차트 색상, 기본값
├── types/
│   ├── portfolio.ts
│   ├── benchmark.ts
│   ├── backtest.ts
│   ├── strategy.ts
│   ├── paper.ts
│   └── common.ts
├── package.json
├── tsconfig.json
├── next.config.mjs
├── postcss.config.mjs
├── tailwind.config.ts
└── components.json                # shadcn/ui 설정
```

### 4.2 Python API (`pyapi/`)

> 이름을 `pyapi/`로 하여 Next.js의 `app/api/`와 명확히 구분한다.

```
pyapi/
├── main.py                        # FastAPI 앱 진입점
├── routers/
│   ├── portfolio.py               # /py/portfolio
│   ├── backtest.py                # /py/backtest
│   ├── bot.py                     # /py/bot/*
│   ├── signals.py                 # /py/signals
│   └── paper.py                   # /py/paper/*
├── schemas.py                     # Pydantic 모델 (요청/응답)
└── deps.py                        # 시크릿 검증 미들웨어
```

> 이전 설계 대비 **벤치마크, 전략 설정 라우터가 제거**됨 (Next.js에서 직접 처리).
> schemas도 단일 파일로 충분 (엔드포인트가 적으므로).

### 4.3 전체 프로젝트 구조

```
D2trader/
├── src/                           ← 기존 그대로 (전략, 브로커, 엔진)
├── config/
│   └── settings.yaml              ← 기존 그대로
├── main.py                        ← 기존 CLI
├── dashboard/                     ← 기존 Streamlit (폴백, 추후 삭제)
├── pyapi/                         ← 신규: 경량 Python API
│   ├── main.py
│   ├── routers/
│   ├── schemas.py
│   └── deps.py
├── web/                           ← 신규: Next.js 풀스택
│   ├── app/                       (프론트 + API Routes)
│   ├── components/
│   ├── hooks/
│   ├── lib/
│   └── types/
├── docs/
│   ├── DESIGN_SYSTEM.md
│   └── WEB_PROJECT_SPEC.md        ← 이 문서
├── data/                          ← 기존 (gitignored)
├── .env                           ← 기존 + PYTHON_API_SECRET 추가
└── requirements.txt               ← 기존 + fastapi, uvicorn 추가
```

---

## 5. API 설계

### 5.1 Next.js API Routes (Python 불필요)

이 엔드포인트들은 Next.js 서버에서 직접 처리한다.

---

#### 벤치마크 (`/api/benchmark`)

| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/benchmark?period=3M` | 벤치마크 비교 데이터 |

**구현**: `yahoo-finance2` npm 패키지로 KOSPI(^KS11), S&P500(^GSPC) 시세를 직접 조회.
포트폴리오 수익률은 Python `/py/portfolio`에서 받은 데이터로 계산.

**쿼리 파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| period | string | "3M" | 1M, 3M, 6M, 1Y, ALL |
| start | string | - | 커스텀 시작일 (YYYY-MM-DD) |
| end | string | - | 커스텀 종료일 (YYYY-MM-DD) |

**응답:**

```json
{
  "data": {
    "dates": ["2025-11-18", "2025-11-19"],
    "portfolio": [100, 100.5],
    "kospi": [100, 99.8],
    "sp500": [100, 100.3],
    "metrics": {
      "portfolio_return": 12.3,
      "kospi_return": 5.1,
      "sp500_return": 8.7,
      "alpha": 3.2,
      "beta": 0.78,
      "information_ratio": 1.15
    },
    "strategy_comparison": [
      { "strategy": "StatArb", "return": 8.2, "benchmark_return": 5.1, "excess_return": 3.1 }
    ]
  },
  "error": null
}
```

---

#### 전략 설정 (`/api/settings`)

| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/settings` | settings.yaml 전체 조회 |
| PUT | `/api/settings` | settings.yaml 저장 |
| PATCH | `/api/settings/strategies/{key}/toggle` | 전략 ON/OFF 토글 |

**구현**: `js-yaml` 패키지로 `config/settings.yaml`을 직접 읽기/쓰기.

```typescript
// web/app/api/settings/route.ts 예시
import yaml from 'js-yaml';
import { readFile, writeFile } from 'fs/promises';

const SETTINGS_PATH = process.cwd() + '/../config/settings.yaml';

export async function GET() {
  const content = await readFile(SETTINGS_PATH, 'utf-8');
  const data = yaml.load(content);
  return Response.json({ data, error: null });
}
```

**GET 응답:**

```json
{
  "data": {
    "strategies": {
      "stat_arb": {
        "enabled": true,
        "pairs": [
          { "name": "Samsung_Hynix", "codes": ["005930", "000660"], "market": "KR" }
        ],
        "zscore_entry": 2.0,
        "zscore_exit": 0.5,
        "zscore_stop": 3.0,
        "lookback": 60
      },
      "dual_momentum": { "enabled": true },
      "quant_factor": { "enabled": false }
    },
    "risk": {},
    "backtest": {}
  },
  "error": null
}
```

---

### 5.2 Python API 엔드포인트 (Python 필수)

Base URL: `http://localhost:8000/py`
인증: `X-Internal-Secret` 헤더 (Next.js 서버 → Python, 브라우저 직접 호출 불가)

---

#### 포트폴리오 (`/py/portfolio`)

| Method | Path | 설명 | 기존 서비스 |
|--------|------|------|-------------|
| GET | `/py/portfolio` | KIS API 잔고 + 리스크 조회 | `portfolio_service.get_portfolio_status()` |

**응답:**

```json
{
  "data": {
    "kr": {
      "total_equity": 52340000,
      "cash": 17890000,
      "positions": [
        { "code": "005930", "name": "삼성전자", "quantity": 10,
          "avg_price": 72000, "current_price": 74500,
          "pnl_pct": 3.47, "value": 745000, "weight": 14.2 }
      ]
    },
    "us": {},
    "risk": {
      "total_equity": 52340000, "cash": 17890000,
      "cash_pct": 34.2, "daily_pnl": 320000,
      "drawdown": -4.2, "mdd": -8.1,
      "positions_count": 5, "max_positions": 10,
      "kill_switch": false,
      "sharpe_ratio": 1.34, "sortino_ratio": 1.87
    },
    "strategies": [
      { "name": "StatArb", "key": "stat_arb", "enabled": true,
        "pnl_pct": 5.2, "positions_count": 3 }
    ]
  },
  "error": null
}
```

---

#### 백테스트 (`/py/backtest`)

| Method | Path | 설명 | 기존 서비스 |
|--------|------|------|-------------|
| POST | `/py/backtest/run` | 백테스트 실행 | `backtest_service.run_backtest()` |
| POST | `/py/backtest/run-per-pair` | 페어별 백테스트 | `backtest_service.run_backtest_per_pair()` |
| GET | `/py/backtest/pairs/{strategy}` | 페어 목록 | `backtest_service.get_pair_names()` |

**POST 요청:**

```json
{
  "strategy": "stat_arb",
  "start_date": "2020-01-01",
  "end_date": "2024-12-31",
  "initial_capital": 50000000,
  "commission_rate": 0.00015,
  "slippage_rate": 0.001,
  "pair_name": null
}
```

**응답 (BacktestResult → JSON 직렬화):**

```json
{
  "data": {
    "metrics": {
      "total_return": 0.452, "cagr": 0.098,
      "sharpe_ratio": 1.34, "sortino_ratio": 1.87,
      "mdd": -0.123, "win_rate": 0.62,
      "profit_factor": 2.15, "total_trades": 48
    },
    "equity_curve": {
      "dates": ["2020-01-02", "2020-01-03"],
      "values": [50000000, 50050000]
    },
    "monthly_returns": {
      "index": [2020, 2021],
      "columns": ["1월", "2월", "3월", "4월", "5월", "6월",
                   "7월", "8월", "9월", "10월", "11월", "12월"],
      "data": [[0.012, -0.003, 0.025, 0.0, 0.0, 0.0,
                0.0, 0.0, 0.0, 0.0, 0.0, 0.0]]
    },
    "trades": [
      { "date": "2020-03-15", "strategy": "StatArb", "code": "005930",
        "market": "KR", "side": "BUY", "quantity": 10, "price": 52000,
        "commission": 78, "pnl": null, "pnl_pct": null, "holding_days": null }
    ],
    "pnl_values": [150000, -30000, 220000]
  },
  "error": null
}
```

**직렬화 코드 (pyapi/routers/backtest.py):**

```python
result, metrics = backtest_service.run_backtest(...)

response = {
    "metrics": metrics,
    "equity_curve": {
        "dates": result.equity_curve.index.strftime("%Y-%m-%d").tolist(),
        "values": result.equity_curve.values.tolist(),
    },
    "trades": [
        {"date": t.date, "strategy": t.strategy, "code": t.code,
         "market": t.market, "side": t.side, "quantity": t.quantity,
         "price": t.price, "commission": t.commission,
         "pnl": t.pnl, "pnl_pct": t.pnl_pct, "holding_days": t.holding_days}
        for t in result.trades
    ],
    "monthly_returns": {
        "index": monthly_df.index.tolist(),
        "columns": monthly_df.columns.tolist(),
        "data": monthly_df.values.tolist(),
    },
    "pnl_values": [t.pnl for t in result.trades if t.pnl is not None],
}
```

---

#### 봇 제어 (`/py/bot`)

| Method | Path | 설명 | 기존 서비스 |
|--------|------|------|-------------|
| POST | `/py/bot/collect` | 데이터 수집 | `bot_service.collect_data()` |
| POST | `/py/bot/run` | 전략 1회 실행 | `bot_service.run_once()` |
| GET | `/py/bot/kill-switch` | Kill Switch 상태 | `bot_service.get_kill_switch_status()` |
| POST | `/py/bot/kill-switch/activate` | 활성화 | `bot_service.activate_kill_switch()` |
| POST | `/py/bot/kill-switch/deactivate` | 비활성화 | `bot_service.deactivate_kill_switch()` |
| GET | `/py/bot/status` | 실행 상태 조회 | 신규 |

---

#### 시그널 (`/py/signals`)

| Method | Path | 설명 | 기존 서비스 |
|--------|------|------|-------------|
| GET | `/py/signals` | 시그널 미리보기 (dry-run) | `paper_trading_service.generate_signals_dry_run()` |

**응답:**

```json
{
  "data": [
    { "strategy": "StatArb", "code": "005930", "market": "KR",
      "signal": "BUY", "quantity": 10, "price": 74500,
      "reason": "Z-Score 2.34 > 진입 임계 2.0" }
  ],
  "error": null
}
```

> `_raw` (Python TradeSignal 객체) 필드는 JSON 직렬화 시 제거.

---

#### 모의거래 (`/py/paper`)

| Method | Path | 설명 | 기존 서비스 |
|--------|------|------|-------------|
| POST | `/py/paper/sessions` | 세션 생성 | `paper_trading_service.create_session()` |
| GET | `/py/paper/sessions/active` | 활성 세션 | `paper_trading_service.get_active_session()` |
| POST | `/py/paper/sessions/{id}/stop` | 세션 종료 | `paper_trading_service.stop_session()` |
| GET | `/py/paper/sessions` | 세션 목록 | `paper_trading_service.get_session_history()` |
| POST | `/py/paper/execute` | 시그널 실행 | `paper_trading_service.execute_signal()` |
| POST | `/py/paper/execute-all` | 전체 실행 | `paper_trading_service.execute_all_signals()` |
| GET | `/py/paper/sessions/{id}/trades` | 거래 내역 | `paper_trading_service.get_paper_trades()` |
| GET | `/py/paper/sessions/{id}/summary` | 거래 요약 | `paper_trading_service.get_session_trade_summary()` |

---

### 5.3 엔드포인트 요약 — 어디서 처리되는가

| 프론트 호출 경로 | 처리 위치 | 이유 |
|-----------------|----------|------|
| `/api/benchmark` | **Next.js API Route** | Yahoo Finance npm 패키지 직접 호출 |
| `/api/settings` | **Next.js API Route** | js-yaml로 YAML 파일 읽기/쓰기 |
| `/api/portfolio` | Next.js → **Python** `/py/portfolio` | KIS API (Python OAuth2) |
| `/api/backtest` | Next.js → **Python** `/py/backtest` | pandas/scipy 백테스트 엔진 |
| `/api/bot/*` | Next.js → **Python** `/py/bot/*` | 전략 실행, KIS 주문 |
| `/api/signals` | Next.js → **Python** `/py/signals` | 전략 시그널 (numpy/pandas) |
| `/api/paper/*` | Next.js → **Python** `/py/paper/*` | 모의 주문 (KIS API) |

---

## 6. TypeScript 타입 정의

### 6.1 공통 (`types/common.ts`)

```typescript
interface ApiResponse<T> {
  data: T | null;
  error: string | null;
}

type Market = "KR" | "US";
type TradeSide = "BUY" | "SELL" | "CLOSE";
```

### 6.2 포트폴리오 (`types/portfolio.ts`)

```typescript
interface Position {
  code: string;
  name: string;
  quantity: number;
  avg_price: number;
  current_price: number;
  pnl_pct: number;
  value: number;
  weight: number;
}

interface RiskSummary {
  total_equity: number;
  cash: number;
  cash_pct: number;
  daily_pnl: number;
  drawdown: number;
  mdd: number;
  positions_count: number;
  max_positions: number;
  kill_switch: boolean;
  sharpe_ratio: number;
  sortino_ratio: number;
}

interface StrategyStatus {
  name: string;
  key: string;
  enabled: boolean;
  pnl_pct: number;
  positions_count: number;
}

interface PortfolioData {
  kr: { total_equity: number; cash: number; positions: Position[] };
  us: { total_equity: number; cash: number; positions: Position[] };
  risk: RiskSummary;
  strategies: StrategyStatus[];
}
```

### 6.3 벤치마크 (`types/benchmark.ts`)

```typescript
interface BenchmarkMetrics {
  portfolio_return: number;
  kospi_return: number;
  sp500_return: number;
  alpha: number;
  beta: number;
  information_ratio: number;
}

interface StrategyComparison {
  strategy: string;
  return_pct: number;
  benchmark_return: number;
  excess_return: number;
}

interface BenchmarkData {
  dates: string[];
  portfolio: number[];
  kospi: number[];
  sp500: number[];
  metrics: BenchmarkMetrics;
  strategy_comparison: StrategyComparison[];
}
```

### 6.4 백테스트 (`types/backtest.ts`)

```typescript
interface BacktestRequest {
  strategy: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  commission_rate?: number;
  slippage_rate?: number;
  pair_name?: string | null;
}

interface BacktestMetrics {
  total_return: number;
  cagr: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  mdd: number;
  win_rate: number;
  profit_factor: number;
  total_trades: number;
  avg_holding_days: number;
}

interface Trade {
  date: string;
  strategy: string;
  code: string;
  market: Market;
  side: TradeSide;
  quantity: number;
  price: number;
  commission: number;
  pnl: number | null;
  pnl_pct: number | null;
  holding_days: number | null;
}

interface BacktestResult {
  metrics: BacktestMetrics;
  equity_curve: { dates: string[]; values: number[] };
  monthly_returns: { index: number[]; columns: string[]; data: number[][] };
  trades: Trade[];
  pnl_values: number[];
}
```

### 6.5 전략 (`types/strategy.ts`)

```typescript
interface StrategyConfig {
  enabled: boolean;
  [key: string]: any;
}

interface StrategiesData {
  strategies: Record<string, StrategyConfig>;
  risk: Record<string, any>;
  backtest: Record<string, any>;
}
```

### 6.6 모의거래 (`types/paper.ts`)

```typescript
interface PaperSession {
  session_id: string;
  start_date: string;
  end_date: string | null;
  status: "active" | "stopped";
  strategy_names: string[];
}

interface PaperSignal {
  strategy: string;
  code: string;
  market: Market;
  signal: string;
  quantity: number;
  price: number;
  reason: string;
}

interface PaperTrade {
  strategy: string;
  code: string;
  market: Market;
  side: TradeSide;
  quantity: number;
  price: number;
  reason: string;
  timestamp: string;
}
```

---

## 7. Python API 프록시 패턴

Next.js API Route에서 Python을 호출하는 공통 헬퍼:

```typescript
// web/lib/python-proxy.ts

const PYTHON_API_URL = process.env.PYTHON_API_URL || 'http://localhost:8000';
const PYTHON_API_SECRET = process.env.PYTHON_API_SECRET || '';

export async function pythonGet(path: string) {
  const res = await fetch(`${PYTHON_API_URL}${path}`, {
    headers: { 'X-Internal-Secret': PYTHON_API_SECRET },
    cache: 'no-store',
  });
  if (!res.ok) throw new Error(`Python API error: ${res.status}`);
  return res.json();
}

export async function pythonPost(path: string, body?: any) {
  const res = await fetch(`${PYTHON_API_URL}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Internal-Secret': PYTHON_API_SECRET,
    },
    body: body ? JSON.stringify(body) : undefined,
    cache: 'no-store',
  });
  if (!res.ok) throw new Error(`Python API error: ${res.status}`);
  return res.json();
}
```

```typescript
// web/app/api/portfolio/route.ts (프록시 예시)

import { pythonGet } from '@/lib/python-proxy';

export async function GET() {
  try {
    const data = await pythonGet('/py/portfolio');
    return Response.json(data);
  } catch (e: any) {
    return Response.json({ data: null, error: e.message }, { status: 502 });
  }
}
```

---

## 8. 구현 체크리스트

### Phase 0: 환경 준비

```
□ D2trader 레포 생성 (또는 기존 레포에 web/, pyapi/ 추가)
□ 기존 src/, config/, main.py 복사 또는 심볼릭 링크
□ .env에 PYTHON_API_SECRET 추가
□ requirements.txt에 fastapi, uvicorn 추가
```

### Phase 1: Python API (경량 — 7개 엔드포인트)

```
□ pyapi/main.py — FastAPI 앱 + 시크릿 검증 미들웨어
□ pyapi/deps.py — X-Internal-Secret 헤더 검증
□ pyapi/routers/portfolio.py  — GET /py/portfolio
□ pyapi/routers/backtest.py   — POST /py/backtest/run, run-per-pair
□ pyapi/routers/bot.py        — POST run/collect, GET/POST kill-switch
□ pyapi/routers/signals.py    — GET /py/signals
□ pyapi/routers/paper.py      — 세션/실행/이력
□ pyapi/schemas.py            — Pydantic 모델
□ curl 테스트 전체 통과
```

### Phase 2: Next.js 프로젝트 기반

```
□ Next.js 14 프로젝트 생성 (web/)
□ Tailwind CSS + globals.css 디자인 토큰 적용
□ shadcn/ui 초기화 (Card, Button, Table, Tabs, Badge, Dialog)
□ Geist 폰트 + next-themes 다크/라이트 모드
□ lib/python-proxy.ts — Python 프록시 헬퍼
□ lib/api-client.ts — /api/* 호출 함수
□ lib/formatters.ts — 통화/퍼센트/날짜 포맷
□ app/api/settings/route.ts — settings.yaml 직접 처리
□ app/api/benchmark/route.ts — Yahoo Finance 직접 처리
□ app/api/portfolio/route.ts — Python 프록시
□ app/api/backtest/route.ts — Python 프록시
□ app/api/bot/*/route.ts — Python 프록시
□ app/api/signals/route.ts — Python 프록시
□ app/api/paper/*/route.ts — Python 프록시
□ components/layout/dashboard-header.tsx — 6탭 네비게이션
□ app/page.tsx — 탭 라우팅 (query param 기반)
□ 빈 페이지 6개 렌더링 확인
```

### Phase 3: 페이지 구현 — 일상 모니터링

```
□ ① 자산 현황
    □ portfolio-kpis.tsx — KPI 카드 4개
    □ strategy-cards.tsx — 전략별 실적 카드
    □ holdings-table.tsx — 보유종목 (KR/US 탭)
    □ risk-indicators.tsx — 위험 지표
    □ hooks/use-portfolio.ts — 5분 자동 갱신
    □ 데이터 연동 테스트

□ ② 벤치마크 비교
    □ benchmark-chart.tsx — 다중 라인 (포트폴리오 vs KOSPI vs S&P500)
    □ alpha-beta-cards.tsx — Alpha/Beta/IR 카드
    □ strategy-vs-market.tsx — 전략별 비교 테이블
    □ hooks/use-benchmark.ts — 기간 선택 연동
    □ 데이터 연동 테스트
```

### Phase 4: 페이지 구현 — 전략 개발

```
□ ③ 전략 설정
    □ strategy-list.tsx — ON/OFF 토글
    □ strategy-editor.tsx — 파라미터 편집
    □ universe-viewer.tsx — 종목 유니버스
    □ 데이터 연동 테스트

□ ④ 백테스트
    □ backtest-form.tsx — 실행 폼
    □ backtest-kpis.tsx — KPI 6개 카드
    □ equity-curve.tsx — Recharts 라인
    □ drawdown-chart.tsx — Recharts 영역
    □ monthly-heatmap.tsx — 커스텀 히트맵
    □ pnl-distribution.tsx — 히스토그램
    □ trade-table.tsx — 거래 내역
    □ 데이터 연동 테스트

□ ⑤ 모의거래
    □ signal-preview.tsx — 시그널 카드
    □ paper-session.tsx — 세션 관리
    □ paper-trades.tsx — 거래 내역
    □ 데이터 연동 테스트
```

### Phase 5: 페이지 구현 — 운영

```
□ ⑥ 실행 & 제어
    □ mode-toggle.tsx — 실거래/모의 전환
    □ kill-switch.tsx — Kill Switch UI
    □ execution-status.tsx — 실행 상태
    □ log-viewer.tsx — 실시간 로그
    □ 데이터 연동 테스트
```

### Phase 6: 배포

```
□ Cloudflare Tunnel 설정
    □ cloudflared 설치
    □ 터널 생성 (Python API용)
    □ DNS 레코드 설정 (api.d2trader.your-domain.com)
□ Cloudflare Pages 배포
    □ GitHub 연동
    □ 빌드 설정 (Next.js)
    □ 환경변수 (PYTHON_API_URL, PYTHON_API_SECRET)
□ (선택) Cloudflare Workers — 추가 인증/Rate Limiting
□ 모바일 접속 테스트
□ 기존 Streamlit 대시보드 비활성화
```

---

## 9. 개발 명령어

```bash
# ── Python API (경량) ──
uvicorn pyapi.main:app --reload --port 8000

# ── Next.js (풀스택) ──
cd web && npm run dev
# → http://localhost:3000

# ── Cloudflare Tunnel (선택) ──
cloudflared tunnel --url http://localhost:8000
```

개발 시 터미널 2개만 띄우면 된다 (Python + Next.js).

---

## 10. 환경변수

### 프로젝트 루트 `.env`

```bash
# 기존 (변경 없음)
KIS_APP_KEY=...
KIS_APP_SECRET=...
KIS_ACCOUNT_NO=...
KIS_ACCOUNT_PRODUCT=01
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...

# D2trader 추가
PYTHON_API_SECRET=your-internal-secret-here
```

### `web/.env.local` (Next.js 서버사이드)

```bash
# Python API 연결 (서버사이드 — 브라우저에 노출 안 됨)
PYTHON_API_URL=http://localhost:8000
PYTHON_API_SECRET=your-internal-secret-here

# 배포 시:
# PYTHON_API_URL=https://api.d2trader.your-domain.com
```

> `NEXT_PUBLIC_` 접두사를 사용하지 않는다.
> Python API 시크릿은 Next.js 서버에서만 사용되고 브라우저에 노출되지 않는다.

---

## 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-02-18 | 초안 작성 — FastAPI 올인 아키텍처 |
| 2026-02-18 | v2 — 하이브리드 아키텍처로 전환 (Next.js API Routes + 경량 Python API) |
