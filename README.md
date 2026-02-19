# D2trader

한국/미국 주식 알고리즘 트레이딩 대시보드. KIS Open API(한국투자증권)를 통한 자동 매매 + Next.js 웹 대시보드.

## 아키텍처

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────────┐     ┌─────────┐
│   Browser   │────▶│  Next.js :3000   │────▶│  FastAPI :8000   │────▶│ KIS API │
│  (React 19) │     │  (API Routes)    │     │  (pyapi/)        │     │         │
└─────────────┘     └──────────────────┘     └──────────────────┘     └─────────┘
                                                      ▲
                    ┌──────────────────┐               │
                    │   CLI (main.py)  │───────────────┘
                    └──────────────────┘        src/* (코어 엔진)
```

4계층 프록시 체인:
1. **Browser** → Next.js 페이지 (client component)
2. **web/lib/api-client.ts** → `/api/*` (Next.js API Route)
3. **web/lib/python-proxy.ts** → `PYTHON_API_URL/py/*` (X-Internal-Secret 헤더)
4. **pyapi/routers/*.py** → `src/*` (코어 엔진 직접 import)

## 전략

| 전략 | 설명 | 방식 |
|------|------|------|
| **stat_arb** | 통계적 차익거래 | 공적분 기반 페어 트레이딩 (z-score 진입/청산) |
| **dual_momentum** | 듀얼 모멘텀 | 상대 모멘텀 + 절대 모멘텀, 월 1회 리밸런싱 |
| **quant_factor** | 퀀트 팩터 | 멀티팩터 스코어링 (가치+퀄리티+모멘텀) + 절대 모멘텀 필터 |
| **sector_rotation** | 섹터 로테이션 | US/KR 섹터 ETF 모멘텀 기반 상위 N개 투자 |
| **volatility_breakout** | 변동성 돌파 | 래리 윌리엄스 방식, OHLC 기반 일중 전략 |

## Quick Start

```bash
# 1. Python 환경 (pyenv 3.12.12 권장)
pip install -r requirements.txt

# 2. 환경변수 설정
cp .env.example .env
# .env에 KIS_APP_KEY, KIS_APP_SECRET, KIS_ACCOUNT_NO 등 입력

# 3. Node 의존성
cd web && npm install && cd ..

# 4. Python API 서버
PYTHON_API_SECRET=dev-secret uvicorn pyapi.main:app --host 0.0.0.0 --port 8000

# 5. Next.js 개발 서버 (별도 터미널)
cd web && npm run dev
```

## 프로젝트 구조

```
TB_v2/
├── main.py                  # CLI (run, status, collect, backtest, backtest-yf)
├── config/settings.yaml     # 전략/리스크/브로커 설정
├── src/                     # Python 코어 엔진
│   ├── core/                # 브로커, 설정, DB, 리스크 관리
│   ├── strategies/          # 5개 매매 전략 (BaseStrategy 플러그인)
│   ├── execution/           # 데이터 수집 + 주문 실행
│   ├── backtest/            # 백테스트 엔진
│   └── utils/               # 로거(loguru), 텔레그램 알림
├── pyapi/                   # FastAPI 서버 (6개 라우터)
│   └── routers/             # portfolio, backtest, bot, signals, paper, benchmark
├── web/                     # Next.js 16 프론트엔드 (6탭 SPA)
├── tests/                   # pytest (85 tests)
├── dashboard/               # Streamlit 레거시 UI (deprecated)
├── deploy/                  # 배포 (systemd, Cloudflare, GitHub Actions)
└── docs/                    # 문서
```

## CLI 사용법

```bash
python3 main.py run                              # 전략 1회 실행 (수집 → 분석 → 매매)
python3 main.py status                           # 전략 + 리스크 상태 확인
python3 main.py collect                          # 데이터 수집만 실행
python3 main.py backtest --strategy stat_arb     # DB 기반 백테스트
python3 main.py backtest-yf -s stat_arb --start 2020-01-01 --end 2024-12-31
python3 main.py backtest-yf -s all --start 2020-01-01 --end 2024-12-31 --capital 50000000
python3 main.py backtest-yf -s stat_arb --per-pair --start 2020-01-01 --end 2024-12-31
```

## 기술 스택

**백엔드**: Python 3.12 (pyenv), FastAPI, SQLAlchemy, pandas, numpy, scipy, statsmodels, yfinance, APScheduler
**프론트엔드**: Next.js 16, React 19, TypeScript 5.9, Tailwind CSS 4, shadcn/ui, Recharts
**DB**: SQLite
**배포**: Cloudflare Pages + Tunnel, systemd, GitHub Actions

## 테스트

```bash
python -m pytest tests/             # 전체 85 tests
python -m pytest tests/ -v          # verbose
```

| 파일 | 테스트 수 | 대상 |
|------|----------|------|
| `test_simulation_e2e.py` | 13 | PortfolioTracker E2E (매수/매도/P&L/스냅샷) |
| `test_strategies.py` | 72 | StatArb/DualMomentum/QuantFactor/AbsMomentum/SectorRotation/VolatilityBreakout |

## 문서

| 문서 | 설명 |
|------|------|
| [CLAUDE.md](CLAUDE.md) | AI 코딩 가이드라인 + 프로젝트 개요 (가장 포괄적) |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | 시스템 아키텍처 및 데이터 플로우 |
| [API_REFERENCE.md](docs/API_REFERENCE.md) | API 엔드포인트 레퍼런스 |
| [SETUP_GUIDE.md](docs/SETUP_GUIDE.md) | 개발 환경 셋업 가이드 |
| [STATUS.md](docs/STATUS.md) | 현재 구현 상태 |
| [CONVENTIONS.md](docs/CONVENTIONS.md) | 코드 패턴 가이드 |
| [USER_MANUAL.md](docs/USER_MANUAL.md) | 사용자 매뉴얼 |
| [TEST_PLAN.md](docs/TEST_PLAN.md) | 테스트 전략 및 케이스 |
| [SIMULATION_ISSUES.md](docs/SIMULATION_ISSUES.md) | 시뮬레이션 이슈 분석 & 수정 이력 |
