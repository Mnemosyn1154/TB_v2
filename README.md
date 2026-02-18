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

## 전략

| 전략 | 설명 | 방식 |
|------|------|------|
| **stat_arb** | 통계적 차익거래 | 공적분 기반 페어 트레이딩 (z-score 진입/청산) |
| **dual_momentum** | 듀얼 모멘텀 | 상대 모멘텀 + 절대 모멘텀, 월 1회 리밸런싱 |
| **quant_factor** | 퀀트 팩터 | 멀티팩터 스코어링 (가치+퀄리티+모멘텀) |

## Quick Start

```bash
# 1. 환경변수 설정
cp .env.example .env
# .env에 KIS_APP_KEY, KIS_APP_SECRET, KIS_ACCOUNT_NO 등 입력

# 2. Python 의존성
pip install -r requirements.txt

# 3. Node 의존성
cd web && npm install && cd ..

# 4. Python API 서버
uvicorn pyapi.main:app --host 0.0.0.0 --port 8000

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
│   ├── strategies/          # 매매 전략 (BaseStrategy 플러그인)
│   ├── execution/           # 데이터 수집 + 주문 실행
│   ├── backtest/            # 백테스트 엔진
│   └── utils/               # 로거, 텔레그램 알림
├── pyapi/                   # FastAPI 서버 (5개 라우터)
├── web/                     # Next.js 16 프론트엔드 (6탭 SPA)
├── dashboard/               # Streamlit 레거시 UI
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

**백엔드**: Python 3.x, FastAPI, SQLAlchemy, pandas, numpy, scipy, statsmodels, yfinance
**프론트엔드**: Next.js 16, React 19, TypeScript 5.9, Tailwind CSS 4, shadcn/ui, Recharts
**DB**: SQLite
**배포**: Cloudflare Pages + Tunnel, systemd, GitHub Actions

## 문서

- [ARCHITECTURE.md](docs/ARCHITECTURE.md) — 시스템 아키텍처 및 데이터 플로우
- [API_REFERENCE.md](docs/API_REFERENCE.md) — API 엔드포인트 레퍼런스
- [SETUP_GUIDE.md](docs/SETUP_GUIDE.md) — 개발 환경 셋업 가이드
- [STATUS.md](docs/STATUS.md) — 현재 구현 상태
- [CONVENTIONS.md](docs/CONVENTIONS.md) — 코드 패턴 가이드
