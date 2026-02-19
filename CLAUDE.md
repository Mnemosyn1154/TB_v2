# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

---

## 프로젝트 개요

D2trader — 한국/미국 주식 알고리즘 트레이딩 대시보드.
KIS Open API(한국투자증권)를 통해 5개 전략(stat_arb, dual_momentum, quant_factor, sector_rotation, volatility_breakout)을 자동 매매하며,
Next.js 웹 대시보드에서 포트폴리오 모니터링, 백테스트, 페이퍼 트레이딩, 봇 제어를 수행한다.

- **백엔드**: Python 3.12 + FastAPI (pyapi/) + 코어 엔진 (src/)
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
4. **pyapi/routers/*.py** → `src/*` (직접 import 또는 `dashboard/services/` 경유)

예외:
- Settings 라우트: Python API 거치지 않고 `config/settings.yaml` 직접 읽기/쓰기

## 디렉토리 맵

```
TB_v2/
├── main.py                  # CLI 진입점 (run, status, collect, backtest, backtest-yf)
├── config/settings.yaml     # 전략/리스크/브로커 설정 (YAML)
├── src/                     # Python 코어 엔진
│   ├── core/                # KIS 브로커, 설정 로더, DB, 리스크 관리
│   ├── strategies/          # 5개 전략 (BaseStrategy 플러그인 시스템)
│   ├── execution/           # 데이터 수집 + 주문 실행
│   ├── backtest/            # 백테스트 엔진 + 성과 분석
│   └── utils/               # 로거(loguru), 텔레그램 알림
├── pyapi/                   # FastAPI 서버 (src/ 래핑)
│   ├── main.py              # FastAPI 앱 (CORS, 라우터 등록, lifespan 스케줄러)
│   ├── scheduler.py         # APScheduler 래퍼 (start/stop/status, 장중 체크)
│   ├── routers/             # portfolio, backtest, bot, signals, paper, benchmark
│   ├── deps.py              # verify_secret (X-Internal-Secret 검증)
│   └── schemas.py           # BacktestRequest, ExecuteRequest
├── web/                     # Next.js 프론트엔드
│   ├── app/api/             # API 프록시 라우트 (Next.js → Python API)
│   ├── app/page.tsx         # 메인 대시보드 (6탭 SPA)
│   ├── components/          # 탭별 컴포넌트 (portfolio/, backtest/, 등)
│   ├── components/ui/       # shadcn/ui 프리미티브 (수정 금지)
│   ├── hooks/               # useApi, usePortfolio, useBacktest 등
│   ├── lib/                 # api-client, python-proxy, formatters, strategy-utils
│   └── types/               # 도메인별 TypeScript 타입 정의
├── tests/                   # pytest 테스트
│   ├── conftest.py          # 공통 fixture (in-memory SQLite tracker)
│   ├── test_simulation_e2e.py  # 시뮬레이션 E2E (매수/매도/P&L/스냅샷)
│   └── test_strategies.py   # 전략 유닛 테스트 (StatArb/DualMomentum/QuantFactor/VolatilityBreakout)
├── dashboard/               # Streamlit 레거시 UI
│   └── services/            # 비즈니스 로직 (일부 pyapi에서 import)
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
- pyapi 라우터: 복잡한 로직은 `dashboard/services/` 경유, 단순한 경우 `src/` 직접 import 가능

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
# Python API (환경변수 필요)
PYTHON_API_SECRET=dev-secret-change-in-production python3 -m uvicorn pyapi.main:app --host 0.0.0.0 --port 8000

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
- **시뮬레이션 이슈 Phase 1-4**: 모두 수정 완료 (docs/SIMULATION_ISSUES.md 참조)
- **벤치마크 탭**: Python API 경유 DB 캐시 + yfinance 보충 + 포트폴리오 시계열 연동
- **APScheduler**: 15분 주기 자동 전략 실행 (`scheduler.enabled`, 장중에만 실행, 킬스위치 연동)
- **시뮬레이션 모드**: SQLite 기반 가상 포트폴리오 (기본 ON, `simulation.enabled` 토글)
  - 실주문 차단 가드, DB 트랜잭션, 포지션 가격 갱신, 스냅샷 기록
- **Python 3.12**: pyenv로 3.12.12 사용 (`.python-version`), 3.10+ 타입 문법 지원
- **활성 전략** (settings.yaml `enabled: true`): dual_momentum, quant_factor, volatility_breakout
- **비활성 전략**: stat_arb, sector_rotation, sam_hynix (각 `enabled: false`)
- **백테스트 리스크**: 백테스트 모드에서 MDD/킬스위치/일일손실 체크 자동 비활성화
- **테스트**: 85 tests 통과 (`python -m pytest tests/`)
  - `tests/test_simulation_e2e.py` — PortfolioTracker E2E (13 tests)
  - `tests/test_strategies.py` — StatArb/DualMomentum/QuantFactor/AbsMomentum/SectorRotation/VolatilityBreakout 유닛 (72 tests)
- **Settings API**: Python API 없이 Next.js에서 settings.yaml 직접 읽기/쓰기
- **전략 편집**: StrategyEditor에서 숫자/문자열 파라미터, pairs, universe_codes 편집 가능
- **백테스트**: inf/NaN 안전 직렬화, 사람이 읽을 수 있는 실행 로그 제공
- **대시보드 UX**: 토스트 에러 알림, bot/run 후 캐시 자동 무효화

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
| `docs/SIMULATION_ISSUES.md` | 시뮬레이션 이슈 분석 & 수정 이력 (Phase 1-4 완료) |
| `docs/DESIGN_SYSTEM.md` | 디자인 토큰, 색상, 타이포그래피 |
| `src/*/README.md` | 모듈별 문서 (5개 파일) |
