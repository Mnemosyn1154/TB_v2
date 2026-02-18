# CLAUDE.md

## 프로젝트 개요

D2trader — 한국/미국 주식 알고리즘 트레이딩 대시보드.
KIS Open API(한국투자증권)를 통해 3개 전략(stat_arb, dual_momentum, quant_factor)을 자동 매매하며,
Next.js 웹 대시보드에서 포트폴리오 모니터링, 백테스트, 페이퍼 트레이딩, 봇 제어를 수행한다.

- **백엔드**: Python 3.x + FastAPI (pyapi/) + 코어 엔진 (src/)
- **프론트엔드**: Next.js 16 + React 19 + TypeScript 5.9 + Tailwind 4 + shadcn/ui
- **DB**: SQLite (data/trading_bot.db)
- **배포**: Cloudflare Pages + Tunnel, systemd, GitHub Actions

## 아키텍처

```
Browser → Next.js (port 3000) → Python API (port 8000) → src/* → KIS API
                                        ↓
CLI (main.py) ─────────────────→ src/* → KIS API
```

4계층 프록시 체인:
1. **Browser** → Next.js 페이지 (client component)
2. **web/lib/api-client.ts** → `/api/*` (Next.js API Route)
3. **web/lib/python-proxy.ts** → `PYTHON_API_URL/py/*` (X-Internal-Secret 헤더)
4. **pyapi/routers/*.py** → `dashboard/services/*.py` → `src/*` → KIS API

예외:
- Settings 라우트: Python API 거치지 않고 `config/settings.yaml` 직접 읽기/쓰기
- Benchmark 라우트: Yahoo Finance API 직접 호출

## 디렉토리 맵

```
TB_v2/
├── main.py                  # CLI 진입점 (run, status, collect, backtest, backtest-yf)
├── config/settings.yaml     # 전략/리스크/브로커 설정 (YAML)
├── src/                     # Python 코어 엔진
│   ├── core/                # KIS 브로커, 설정 로더, DB, 리스크 관리
│   ├── strategies/          # 3개 전략 (BaseStrategy 플러그인 시스템)
│   ├── execution/           # 데이터 수집 + 주문 실행
│   ├── backtest/            # 백테스트 엔진 + 성과 분석
│   └── utils/               # 로거(loguru), 텔레그램 알림
├── pyapi/                   # FastAPI 서버 (src/ 래핑)
│   ├── main.py              # FastAPI 앱 (CORS, 라우터 등록)
│   ├── routers/             # portfolio, backtest, bot, signals, paper
│   ├── deps.py              # verify_secret (X-Internal-Secret 검증)
│   └── schemas.py           # BacktestRequest, ExecuteRequest
├── web/                     # Next.js 프론트엔드
│   ├── app/api/             # API 프록시 라우트 (Next.js → Python API)
│   ├── app/page.tsx         # 메인 대시보드 (6탭 SPA)
│   ├── components/          # 탭별 컴포넌트 (portfolio/, backtest/, 등)
│   ├── components/ui/       # shadcn/ui 프리미티브 (수정 금지)
│   ├── hooks/               # useApi, usePortfolio, useBacktest 등
│   ├── lib/                 # api-client, python-proxy, formatters
│   └── types/               # 도메인별 TypeScript 타입 정의
├── dashboard/               # Streamlit 레거시 UI
│   └── services/            # 비즈니스 로직 (pyapi에서 import)
├── deploy/                  # systemd 서비스, Cloudflare Tunnel, deploy.sh
└── docs/                    # 문서 (ARCHITECTURE, API_REFERENCE, 등)
```

## 코드 컨벤션

### Python
- 모든 .py 파일 첫 줄: `from __future__ import annotations`
- 모듈 docstring에 "Depends on:" / "Used by:" / "Modification Guide:" 포함
- 로깅: `from loguru import logger`
- 설정 접근: `from src.core.config import get_config`
- API 응답 envelope: `{"data": T | null, "error": string | null}`
- pyapi 라우터: 핸들러 함수 내부에서 lazy import (순환 참조 방지)
- pyapi 라우터: `dashboard/services/` 경유, `src/` 직접 import 지양

### TypeScript / React
- 인터랙티브 컴포넌트: `"use client"` 디렉티브 필수
- 데이터 페칭: `useApi<T>(fetcher)` → `{ data, error, loading, refetch }`
- API 클라이언트: `web/lib/api-client.ts`에 모든 API 호출 함수 정의
- 타입 정의: `web/types/` 도메인별 파일 (common.ts, portfolio.ts, backtest.ts 등)
- 공통 타입: `ApiResponse<T> = { data: T | null, error: string | null }`
- 컴포넌트 구조: `{tab}-tab.tsx` (컨테이너) + 하위 컴포넌트
- UI 텍스트: 한국어, 코드/주석: 영어
- shadcn/ui 컴포넌트 (`components/ui/`): 수정 금지

### 스타일링
- Tailwind CSS 4 유틸리티 클래스
- OKLCH 색상 시스템 (globals.css 정의)
- 다크 모드 기본 (ThemeProvider defaultTheme="dark")

## 일반적인 작업 가이드

### 새 전략 추가
1. `src/strategies/new_strategy.py` — BaseStrategy 상속, 5개 추상 메서드 구현
2. `src/strategies/__init__.py` — STRATEGY_REGISTRY에 등록
3. `config/settings.yaml` — strategies 섹션에 파라미터 추가

### 새 API 엔드포인트 추가
1. `pyapi/routers/{domain}.py` — FastAPI 엔드포인트 추가
2. `web/app/api/{domain}/route.ts` — Next.js 프록시 라우트 추가
3. `web/lib/api-client.ts` — 프론트엔드 API 함수 추가
4. `web/types/{domain}.ts` — 타입 정의 추가

### 서버 실행
```bash
# Python API
uvicorn pyapi.main:app --host 0.0.0.0 --port 8000

# Next.js 개발 서버
cd web && npm run dev

# CLI 실행
python3 main.py run                    # 전략 1회 실행
python3 main.py status                 # 상태 확인
python3 main.py collect                # 데이터 수집
python3 main.py backtest-yf -s stat_arb --start 2020-01-01 --end 2024-12-31
```

## 현재 상태

- **Phase 1-9**: 모두 구현 완료 (docs/mainplan.md 참조)
- **벤치마크 탭**: Yahoo Finance 연동 구현됨 (web/app/api/benchmark/route.ts)
- **quant_factor 전략**: settings.yaml에서 disabled (enabled: false)
- **테스트**: 미구현 (테스트 플랜은 docs/TEST_PLAN.md에 작성됨)
- **Settings API**: Python API 없이 Next.js에서 settings.yaml 직접 읽기/쓰기

## 문서 인덱스

| 문서 | 설명 |
|------|------|
| `docs/ARCHITECTURE.md` | 시스템 레이어, 데이터 플로우, DB 스키마, 인증, 배포 |
| `docs/API_REFERENCE.md` | Python API + Next.js API Routes 전체 엔드포인트 |
| `docs/STATUS.md` | 현재 구현 상태, 미완성 항목, 알려진 이슈 |
| `docs/CONVENTIONS.md` | Python/TypeScript 코드 패턴 상세 가이드 |
| `docs/mainplan.md` | 9단계 구현 플랜 (히스토리 참조용) |
| `docs/WEB_PROJECT_SPEC.md` | 웹 대시보드 기술 사양서 |
| `docs/SETUP_GUIDE.md` | 개발 환경 셋업 가이드 |
| `docs/TEST_PLAN.md` | 테스트 전략 및 케이스 |
| `docs/DESIGN_SYSTEM.md` | 디자인 토큰, 색상, 타이포그래피 |
| `src/*/README.md` | 모듈별 문서 (5개 파일) |

---

## 행동 가이드라인

코딩 실수를 줄이기 위한 가이드라인. 속도보다 신중함을 우선시한다.

### 1. Think Before Coding

**가정하지 마라. 혼란을 숨기지 마라. 트레이드오프를 드러내라.**

구현 전:
- 가정을 명시적으로 기술. 불확실하면 질문.
- 여러 해석이 가능하면, 모두 제시 — 조용히 하나를 선택하지 마라.
- 더 단순한 방법이 있으면 말하라. 필요하면 반론을 제기하라.
- 불명확하면 멈추라. 무엇이 혼란스러운지 명시하고 질문하라.

### 2. Simplicity First

**문제를 해결하는 최소한의 코드. 추측성 구현 금지.**

- 요청 범위를 넘는 기능 추가 금지.
- 일회용 코드에 추상화 금지.
- 요청하지 않은 "유연성"이나 "설정 가능성" 금지.
- 불가능한 시나리오에 대한 에러 핸들링 금지.
- 200줄로 쓴 것이 50줄로 가능하면 재작성.

자문: "시니어 엔지니어가 이것은 과도하게 복잡하다고 할까?" 그렇다면 단순화.

### 3. Surgical Changes

**필요한 것만 수정. 자신이 만든 잔해만 정리.**

기존 코드 수정 시:
- 인접 코드, 주석, 포매팅을 "개선"하지 마라.
- 깨지지 않은 것을 리팩터링하지 마라.
- 기존 스타일을 따르라. 본인이 다르게 할 것이라도.
- 무관한 데드 코드를 발견하면, 언급하되 삭제하지 마라.

본인의 변경으로 고아가 된 경우:
- 본인의 변경으로 미사용된 import/변수/함수는 제거.
- 기존 데드 코드는 요청 없이 제거하지 마라.

테스트: 모든 변경 라인이 사용자 요청에 직접 추적 가능해야 한다.

### 4. Goal-Driven Execution

**성공 기준을 정의. 검증될 때까지 반복.**

작업을 검증 가능한 목표로 변환:
- "유효성 검사 추가" → "유효하지 않은 입력에 대한 테스트 작성 후 통과시키기"
- "버그 수정" → "버그를 재현하는 테스트 작성 후 통과시키기"
- "X 리팩터링" → "테스트가 전후로 통과하는지 확인"

다단계 작업 시 간략한 계획:
```
1. [단계] → 검증: [확인사항]
2. [단계] → 검증: [확인사항]
3. [단계] → 검증: [확인사항]
```

강한 성공 기준은 독립적 반복을 가능하게 한다. 약한 기준("되게 만들기")은 지속적 확인이 필요하다.

---

**이 가이드라인이 작동하고 있다면:** diff에 불필요한 변경이 적고, 과도한 복잡성으로 인한 재작성이 적으며, 구현 전에 질문이 먼저 나온다.
