# mainplan.md — D2trader 전체 구현 플랜

> 초기 세팅(Phase 0) 완료 후, 실제 기능 구현을 위한 단계별 실행 계획.
> 각 Phase는 독립적으로 검증 가능한 단위로 구성됨.
> 참조: [`WEB_PROJECT_SPEC.md`](./WEB_PROJECT_SPEC.md), [`DESIGN_SYSTEM.md`](./DESIGN_SYSTEM.md), [`UI_FEATURE_PLAN.md`](./UI_FEATURE_PLAN.md)

---

## 현재 상태 (Phase 0 완료)

### 완료된 항목

| 영역 | 완료 항목 |
|------|----------|
| **프로젝트 구조** | `web/`, `pyapi/` 디렉토리 생성, GitHub 푸시 완료 |
| **Next.js** | v16 + TypeScript + Tailwind v4 + App Router + Turbopack |
| **shadcn/ui** | 16개 컴포넌트 설치 (Card, Button, Table, Tabs, Badge, Dialog 등) |
| **디자인 토큰** | globals.css에 OKLCH 색상, success, market-kr/us 추가 |
| **레이아웃** | layout.tsx (ThemeProvider + TooltipProvider + Geist 폰트) |
| **대시보드 셸** | page.tsx (6탭 전환) + dashboard-header.tsx (반응형 네비) |
| **API Routes** | 11개 프록시 라우트 (portfolio, backtest, bot, signals, paper, settings, benchmark) |
| **라이브러리** | lib/ (python-proxy, api-client, formatters, constants) |
| **커스텀 훅** | hooks/ (use-api, use-interval) |
| **타입 정의** | types/ (common, portfolio, benchmark, backtest, strategy, paper) |
| **Python API** | FastAPI 앱 스캐폴드 (main.py, deps.py, schemas.py) + health 엔드포인트 |
| **환경변수** | .env + web/.env.local (PYTHON_API_SECRET) |

### 미완료 — 이후 Phase에서 구현

| 영역 | 미구현 항목 |
|------|-----------|
| **Python API 라우터** | portfolio, backtest, bot, signals, paper (0/5개) |
| **페이지 컴포넌트** | 6개 탭 모두 플레이스홀더 상태 |
| **차트 컴포넌트** | 없음 |
| **데이터 연동** | 프론트 ↔ 백엔드 실제 통신 미구현 |
| **벤치마크 API** | Yahoo Finance 연동 플레이스홀더 |
| **기존 src/ 코드** | 아직 프로젝트에 미포함 |

---

## Phase 1: Python API 라우터 구현

> **목표**: 기존 src/ 서비스를 FastAPI 엔드포인트로 래핑하여, Next.js에서 호출 가능한 상태로 만든다.
> **의존성**: 기존 `src/`, `config/`, `data/` 디렉토리가 프로젝트 루트에 존재해야 함.
> **검증**: 각 엔드포인트를 curl로 호출하여 JSON 응답 확인.

### 1-0. 기존 코드 통합

```
□ 기존 AlgoTrader KR의 src/, config/, main.py를 프로젝트 루트에 복사/링크
□ requirements.txt 통합 (기존 + fastapi, uvicorn)
□ python3 main.py status 로 기존 코드 정상 동작 확인
□ data/ 디렉토리 확인 (trading_bot.db, 토큰 캐시 등)
```

**검증**: `python3 -c "from src.services.portfolio_service import PortfolioService; print('OK')"`

### 1-1. Portfolio 라우터

```
파일: pyapi/routers/portfolio.py
엔드포인트: GET /py/portfolio
서비스: portfolio_service.get_portfolio_status()
```

**작업 내용**:
- `PortfolioService` import 및 인스턴스 생성
- KIS API 잔고 조회 → JSON 직렬화
- KR/US 분리, risk 지표, strategies 상태 포함
- `verify_secret` 의존성 주입

**응답 스펙**: WEB_PROJECT_SPEC.md 5.2절 참조

**검증**: `curl http://localhost:8000/py/portfolio | python3 -m json.tool`

### 1-2. Backtest 라우터

```
파일: pyapi/routers/backtest.py
엔드포인트:
  POST /py/backtest/run         — 전체 백테스트
  POST /py/backtest/run-per-pair — 페어별 백테스트
  GET  /py/backtest/pairs/{strategy} — 페어 목록
서비스: backtest_service.run_backtest(), run_backtest_per_pair(), get_pair_names()
```

**작업 내용**:
- `BacktestRequest` Pydantic 모델로 요청 검증
- `BacktestResult` → JSON 직렬화 (equity_curve, trades, monthly_returns, pnl_values)
- pandas DataFrame → dict 변환 로직

**검증**: POST 요청으로 백테스트 실행, 결과 JSON 구조 확인

### 1-3. Bot 라우터

```
파일: pyapi/routers/bot.py
엔드포인트:
  POST /py/bot/collect              — 데이터 수집
  POST /py/bot/run                  — 전략 1회 실행
  GET  /py/bot/kill-switch          — Kill Switch 상태
  POST /py/bot/kill-switch/activate — 활성화
  POST /py/bot/kill-switch/deactivate — 비활성화
  GET  /py/bot/status               — 실행 상태
서비스: bot_service
```

**작업 내용**:
- `collect_data()`, `run_once()` 래핑
- Kill Switch 상태 조회/토글
- 실행 상태 (마지막 실행 시각, 결과) 반환

**검증**: kill-switch GET → `{"kill_switch": false}`, POST activate → 상태 변경 확인

### 1-4. Signals 라우터

```
파일: pyapi/routers/signals.py
엔드포인트: GET /py/signals
서비스: paper_trading_service.generate_signals_dry_run()
```

**작업 내용**:
- 시그널 dry-run 실행
- TradeSignal 객체 → JSON 직렬화 (`_raw` 필드 제거)
- strategy, code, market, signal, quantity, price, reason 반환

**검증**: `curl http://localhost:8000/py/signals`

### 1-5. Paper Trading 라우터

```
파일: pyapi/routers/paper.py
엔드포인트:
  POST /py/paper/sessions           — 세션 생성
  GET  /py/paper/sessions/active    — 활성 세션
  POST /py/paper/sessions/{id}/stop — 세션 종료
  GET  /py/paper/sessions           — 세션 목록
  POST /py/paper/execute            — 시그널 실행
  POST /py/paper/execute-all        — 전체 실행
  GET  /py/paper/sessions/{id}/trades  — 거래 내역
  GET  /py/paper/sessions/{id}/summary — 거래 요약
서비스: paper_trading_service
```

**작업 내용**:
- 세션 CRUD (생성, 조회, 종료)
- 시그널 실행 (단건, 전체)
- 거래 이력 조회

**검증**: 세션 생성 → 시그널 실행 → 거래 내역 조회 플로우 테스트

### 1-6. 라우터 등록 & 통합 테스트

```
□ pyapi/main.py에 모든 라우터 include
□ Swagger UI (/docs) 에서 전체 엔드포인트 확인
□ curl로 각 엔드포인트 최소 1회 호출 테스트
```

**Phase 1 완료 기준**: `http://localhost:8000/docs`에서 모든 엔드포인트가 목록에 표시되고, 최소 health + portfolio가 실제 데이터 반환.

---

## Phase 2: 자산 현황 탭 (① Portfolio)

> **목표**: 앱을 열면 현재 자산 상태를 한눈에 파악할 수 있는 대시보드 메인 화면.
> **의존성**: Phase 1-1 (Portfolio 라우터), Phase 1-3 (Kill Switch)
> **검증**: localhost:3000 접속 시 실제 KPI 카드, 보유종목 테이블, 위험 지표 표시.

### 2-1. Portfolio 커스텀 훅

```
파일: web/hooks/use-portfolio.ts
기능:
  - /api/portfolio 호출
  - 5분 자동 폴링 (use-interval 활용)
  - 로딩/에러 상태 관리
  - 마지막 업데이트 타임스탬프
```

### 2-2. KPI 카드 컴포넌트

```
파일: web/components/common/metrics-card.tsx
패턴: prism-insight의 metrics-cards.tsx 참고
기능:
  - 아이콘 + 레이블 + 설명 텍스트
  - 큰 숫자 (2xl, bold) + 변화량 (색상 코딩)
  - 시장별 그라데이션 배경 (KR=blue/indigo, US=emerald/teal)
  - 3~4열 반응형 그리드

파일: web/components/portfolio/portfolio-kpis.tsx
기능:
  - MetricsCard 4개: 총자산, 총수익률, 현금비중, 일일손익
  - PortfolioData.risk에서 데이터 추출
```

### 2-3. 전략별 실적 카드

```
파일: web/components/portfolio/strategy-cards.tsx
기능:
  - 전략별 카드 (이름, ON/OFF 상태, 수익률, 포지션 수)
  - 활성 전략은 수익률 색상 코딩, 비활성은 회색 처리
  - PortfolioData.strategies 배열 렌더링
```

### 2-4. 보유종목 테이블

```
파일: web/components/portfolio/holdings-table.tsx
패턴: prism-insight의 holdings-table.tsx 참고
기능:
  - KR/US 탭 (shadcn Tabs)
  - 컬럼: 종목명, 수량, 평균가, 현재가, 수익률(▲▼ + 색상), 비중
  - 통화 포맷 (KR=₩, US=$)
  - 빈 상태 처리 ("보유 종목이 없습니다")
```

### 2-5. 위험 지표 바

```
파일: web/components/portfolio/risk-indicators.tsx
기능:
  - 하단 요약 바: MDD, Sharpe Ratio, Sortino Ratio
  - Kill Switch 상태 표시 (ON=빨강, OFF=초록)
  - 각 지표에 ⓘ 툴팁 (shadcn Tooltip)
```

### 2-6. 탭 통합

```
□ app/page.tsx에서 portfolio 탭에 실제 컴포넌트 연결
□ 로딩 스피너 표시 (API 대기 시)
□ 에러 상태 UI (Python API 미연결 시 안내 메시지)
□ 반응형 확인 (모바일 1열, 데스크톱 3~4열)
```

**Phase 2 완료 기준**: 자산 현황 탭에서 실제 포트폴리오 데이터가 KPI 카드, 전략 카드, 종목 테이블, 위험 지표로 표시됨. 5분마다 자동 갱신.

---

## Phase 3: 벤치마크 비교 탭 (② Benchmark)

> **목표**: 내 포트폴리오 vs 시장 지수 비교 차트와 초과수익 지표.
> **의존성**: Phase 1-1 (포트폴리오 수익률), Yahoo Finance API 연동
> **검증**: 기간 선택 시 차트가 업데이트되고 Alpha/Beta/IR 카드가 계산됨.

### 3-1. 벤치마크 API 구현

```
파일: web/app/api/benchmark/route.ts (기존 플레이스홀더 교체)
기능:
  - yahoo-finance2로 ^KS11 (KOSPI), ^GSPC (S&P500) 시세 조회
  - 기간 파라미터 처리 (1M, 3M, 6M, 1Y, ALL, 커스텀)
  - 포트폴리오 수익률은 /py/portfolio에서 가져와 정규화
  - Alpha, Beta, Information Ratio 계산
  - 전략별 비교 데이터 구성
```

### 3-2. 벤치마크 커스텀 훅

```
파일: web/hooks/use-benchmark.ts
기능:
  - 기간 상태 관리 (period state)
  - /api/benchmark?period={period} 호출
  - 기간 변경 시 자동 재조회
```

### 3-3. 기간 선택기

```
파일: web/components/benchmark/period-selector.tsx
기능:
  - [1M] [3M] [6M] [1Y] [전체] 버튼 그룹 (shadcn ToggleGroup 또는 커스텀)
  - 활성 기간 하이라이트
```

### 3-4. 수익률 비교 차트

```
파일: web/components/benchmark/benchmark-chart.tsx
패턴: prism-insight의 performance-chart-new.tsx 참고
기능:
  - Recharts LineChart + 다중 Line
  - 포트폴리오 (퍼플, 실선, 굵게) vs KOSPI (블루, 점선) vs S&P500 (에메랄드, 점선)
  - 동적 Y축 스케일링 (min/max + 15% 패딩)
  - 커스텀 Tooltip (날짜 + 모든 계열 값)
  - 반응형 높이
```

### 3-5. Alpha/Beta/IR 카드

```
파일: web/components/benchmark/alpha-beta-cards.tsx
기능:
  - 3열 카드: Alpha, Beta, Information Ratio
  - MetricsCard 재사용
  - 색상 코딩 (Alpha > 0 = 녹색, < 0 = 빨강)
```

### 3-6. 전략별 비교 테이블

```
파일: web/components/benchmark/strategy-vs-market.tsx
기능:
  - 전략명, 내 수익률, 벤치마크 수익률, 초과수익, 판정(✅/⚠️)
  - shadcn Table
```

**Phase 3 완료 기준**: 벤치마크 탭에서 기간 선택 시 다중 라인 차트가 업데이트되고, Alpha/Beta/IR 지표 카드와 전략별 비교 테이블이 표시됨.

---

## Phase 4: 전략 설정 탭 (③ Strategy)

> **목표**: settings.yaml의 전략 파라미터를 시각적으로 확인/편집.
> **의존성**: /api/settings (이미 구현됨)
> **검증**: 전략 ON/OFF 토글, 파라미터 편집 후 저장, settings.yaml 반영 확인.

### 4-1. 전략 목록 카드

```
파일: web/components/strategy/strategy-list.tsx
기능:
  - settings.yaml의 strategies 키 순회
  - 전략별 카드: 이름, ON/OFF 토글 (shadcn Switch)
  - 토글 시 PATCH /api/settings/strategies/{key}/toggle 호출
  - 주요 파라미터 요약 표시
```

### 4-2. 파라미터 편집기

```
파일: web/components/strategy/strategy-editor.tsx
기능:
  - Dialog/Sheet로 열리는 편집 폼
  - 전략별 동적 폼 필드 (숫자 입력, 슬라이더)
  - StatArb: zscore_entry, zscore_exit, zscore_stop, lookback
  - DualMomentum: lookback, rebalance_frequency
  - 저장 시 PUT /api/settings 호출
  - 변경사항 diff 표시 (선택)
```

### 4-3. 종목 유니버스 뷰어

```
파일: web/components/strategy/universe-viewer.tsx
기능:
  - 전략별 등록된 종목/페어 목록
  - StatArb: 페어 리스트 (이름 + 종목코드 2개 + 시장)
  - DualMomentum: ETF 리스트
  - 읽기 전용 (편집은 strategy-editor에서)
```

### 4-4. Settings API 보강

```
파일: web/app/api/settings/strategies/[key]/toggle/route.ts (신규)
기능:
  - PATCH 요청으로 특정 전략의 enabled 필드만 토글
  - 전체 YAML 읽기 → 해당 키 토글 → 전체 YAML 쓰기
```

**Phase 4 완료 기준**: 전략 설정 탭에서 ON/OFF 토글이 동작하고, 파라미터 편집/저장 후 settings.yaml에 반영됨.

---

## Phase 5: 백테스트 탭 (④ Backtest)

> **목표**: 전략을 과거 데이터로 검증하고 결과를 다양한 차트로 시각화.
> **의존성**: Phase 1-2 (Backtest 라우터)
> **검증**: 백테스트 실행 → KPI 6개 + 에퀴티 커브 + 드로다운 + 히트맵 + 거래 내역 표시.

### 5-1. 백테스트 실행 폼

```
파일: web/components/backtest/backtest-form.tsx
기능:
  - 전략 선택 (드롭다운, /api/settings에서 전략 목록 가져오기)
  - 기간 선택 (시작일, 종료일 — input type="date")
  - 초기 자본금 입력
  - 페어별 비교 체크박스 (StatArb용)
  - [▶ 백테스트 실행] 버튼 → POST /api/backtest/run
  - 실행 중 로딩 상태
```

### 5-2. KPI 카드 6개

```
파일: web/components/backtest/backtest-kpis.tsx
기능:
  - 6열 반응형 그리드 (모바일 2열, 태블릿 3열, 데스크톱 6열)
  - 수익률, CAGR, Sharpe, MDD, 승률, 손익비
  - MetricsCard 재사용
```

### 5-3. 에퀴티 커브

```
파일: web/components/backtest/equity-curve.tsx
기능:
  - Recharts LineChart + fill 영역 (AreaChart)
  - X축: 날짜, Y축: 자산 가치
  - 초기 자본금 기준선 (점선)
```

### 5-4. 드로다운 차트

```
파일: web/components/backtest/drawdown-chart.tsx
기능:
  - Recharts AreaChart (음수 영역, 빨강 fill)
  - 에퀴티 커브에서 고점 대비 하락률 계산
  - MDD 지점 강조 표시
```

### 5-5. 월별 히트맵

```
파일: web/components/backtest/monthly-heatmap.tsx
기능:
  - 12열(월) x N행(년) 히트맵
  - RdYlGn 색상 스케일 (빨강=손실, 초록=수익)
  - 셀 내 수익률 % 표시
  - Recharts 커스텀 또는 순수 div 기반
```

### 5-6. 손익 분포 히스토그램

```
파일: web/components/backtest/pnl-distribution.tsx
기능:
  - Recharts BarChart
  - X축: 손익 구간, Y축: 거래 수
  - 양수=녹색, 음수=빨강 바
```

### 5-7. 거래 내역 테이블

```
파일: web/components/backtest/trade-table.tsx
기능:
  - shadcn Table (정렬 가능)
  - 컬럼: 날짜, 전략, 종목, 방향, 가격, 손익, 수익률, 보유일수
  - 수익률 색상 코딩
  - 향후 행 확장(아코디언)으로 시그널 근거 표시 가능하도록 구조 설계
```

**Phase 5 완료 기준**: 백테스트 탭에서 전략/기간 선택 후 실행하면 KPI 카드 6개, 에퀴티 커브, 드로다운 차트, 월별 히트맵, 손익 분포, 거래 내역이 모두 표시됨.

---

## Phase 6: 모의거래 탭 (⑤ Paper Trading)

> **목표**: 실시간 시그널 미리보기 + 모의 실행 + 결과 확인.
> **의존성**: Phase 1-4 (Signals), Phase 1-5 (Paper Trading)
> **검증**: 시그널 생성 → 모의 실행 → 거래 내역 확인 플로우.

### 6-1. 시그널 미리보기

```
파일: web/components/paper/signal-preview.tsx
기능:
  - GET /api/signals 호출하여 현재 시그널 표시
  - 전략별 그룹핑 (StatArb, DualMomentum 등)
  - 시그널 정보: 종목, 방향, 수량, 가격, 근거
  - [▶ 모의 실행] [시그널만 확인] 버튼
```

### 6-2. 세션 관리

```
파일: web/components/paper/paper-session.tsx
기능:
  - 활성 세션 표시 (세션 ID, 시작일, 전략 목록)
  - [새 세션 시작] / [세션 종료] 버튼
  - 세션 히스토리 목록 (과거 세션)
```

### 6-3. 모의거래 내역

```
파일: web/components/paper/paper-trades.tsx
기능:
  - 현재 세션의 거래 내역 테이블
  - trade-table.tsx 컴포넌트 재사용 (Phase 5-7)
  - 누적 수익률 요약
```

**Phase 6 완료 기준**: 모의거래 탭에서 시그널 미리보기 → 모의 실행 → 거래 내역 확인이 가능함.

---

## Phase 7: 실행 & 제어 탭 (⑥ Control)

> **목표**: 실거래 운영과 긴급 제어.
> **의존성**: Phase 1-3 (Bot 라우터)
> **검증**: 모드 전환, Kill Switch 작동, 데이터 수집/전략 실행 트리거, 로그 확인.

### 7-1. 모드 토글

```
파일: web/components/control/mode-toggle.tsx
기능:
  - [모의투자 🔵 | 실거래 🔴] 토글
  - 실거래 전환 시 확인 Dialog ("정말 실거래 모드로 전환하시겠습니까?")
  - 현재 모드를 헤더에도 표시 (dashboard-header.tsx 업데이트)
```

### 7-2. Kill Switch

```
파일: web/components/control/kill-switch.tsx
기능:
  - 큰 빨간 버튼 UI
  - 현재 상태: ON(빨강 배경) / OFF(초록 배경)
  - 활성화 시 확인 Dialog ("모든 전략 실행이 중단됩니다")
  - POST /api/bot/kill-switch 호출
```

### 7-3. 실행 상태

```
파일: web/components/control/execution-status.tsx
기능:
  - [▶ 전체 사이클 실행] [📥 데이터 수집] 버튼
  - 마지막 실행 시각, 결과 요약
  - 전략별 실행 상태 (마지막 실행 시각, 정상/에러)
  - 실행 중 상태 (스피너 + 비활성 버튼)
```

### 7-4. 로그 뷰어 (P1 — 선택)

```
파일: web/components/control/log-viewer.tsx
기능:
  - 실행 로그 실시간 표시 (ScrollArea)
  - 로그 레벨 색상 (INFO=회색, WARN=노랑, ERROR=빨강)
  - [로그 지우기] 버튼
  - 10초 폴링으로 업데이트 (전략 실행 중일 때만)
```

**Phase 7 완료 기준**: 실행 & 제어 탭에서 모드 전환, Kill Switch, 데이터 수집, 전략 실행이 동작함.

---

## Phase 8: 통합 & 마무리

> **목표**: 전체 페이지 간 데이터 흐름 검증, UX 개선, 반응형 확인.

### 8-1. 공통 개선

```
□ 로딩 스피너 컴포넌트 통일 (web/components/common/loading-spinner.tsx)
□ 에러 바운더리 (web/components/common/error-boundary.tsx)
□ 빈 상태 컴포넌트 (데이터 없을 때 안내)
□ 마지막 업데이트 타임스탬프 표시 (자산 현황)
□ 헤더에 현재 모드(실거래/모의) + Kill Switch 상태 표시
```

### 8-2. 반응형 검증

```
□ 모바일 (375px): 모든 탭 1열 스택, 핵심 KPI만
□ 태블릿 (768px): 2~3열 그리드
□ 데스크톱 (1280px): 4~6열 그리드, 모든 정보
□ 차트 반응형 높이 조정
□ 테이블 수평 스크롤 (모바일)
```

### 8-3. 성능 최적화

```
□ API 응답 캐싱 전략 (벤치마크: 15분, 포트폴리오: 5분)
□ 불필요한 리렌더링 방지 (useMemo, useCallback)
□ 차트 데이터 포인트 제한 (1000개 이상 시 다운샘플링)
```

**Phase 8 완료 기준**: 모든 6개 탭이 데이터 연동되어 동작하고, 모바일/태블릿/데스크톱에서 정상 표시됨.

---

## Phase 9: 배포

> **목표**: Cloudflare Pages + Tunnel로 외부 접속 가능.
> **의존성**: Phase 1~8 모두 완료.

```
□ Cloudflare Tunnel 설정
  □ cloudflared 설치 및 로그인
  □ 터널 생성 (d2trader-api)
  □ DNS 레코드 (api.d2trader.your-domain.com)
  □ config.yml 작성

□ Cloudflare Pages 배포
  □ GitHub 연동 (TB_v2 레포)
  □ 빌드 설정: cd web && npm run build
  □ 환경변수: PYTHON_API_URL, PYTHON_API_SECRET

□ 배포 후 확인
  □ HTTPS 접속 확인
  □ 모바일 접속 테스트
  □ Python API ↔ Next.js 통신 확인
```

**Phase 9 완료 기준**: 외부 URL로 D2trader 대시보드에 접속 가능하고, 모든 기능이 정상 동작.

---

## 구현 순서 요약

```
Phase 1  Python API 라우터       ← 백엔드 기반
Phase 2  ① 자산 현황 탭          ← 가장 자주 보는 페이지
Phase 3  ② 벤치마크 비교 탭      ← 일상 모니터링 완성
Phase 4  ③ 전략 설정 탭          ← 가장 간단한 CRUD
Phase 5  ④ 백테스트 탭           ← 차트 컴포넌트 가장 많음
Phase 6  ⑤ 모의거래 탭           ← 실거래 전 검증
Phase 7  ⑥ 실행 & 제어 탭       ← 운영 기능
Phase 8  통합 & 마무리            ← UX, 반응형, 성능
Phase 9  배포                     ← Cloudflare
```

### 의존성 다이어그램

```
Phase 0 (완료)
  │
  ▼
Phase 1 (Python API) ──────────────────────────┐
  │                                             │
  ├─► Phase 2 (자산 현황) ─┐                    │
  │                        ├─► Phase 8 (통합) ─► Phase 9 (배포)
  ├─► Phase 3 (벤치마크) ──┤
  │                        │
  ├─► Phase 4 (전략 설정) ─┤
  │                        │
  ├─► Phase 5 (백테스트) ──┤
  │                        │
  ├─► Phase 6 (모의거래) ──┤
  │                        │
  └─► Phase 7 (실행&제어) ─┘
```

> Phase 2~7은 Phase 1이 완료되면 각각 독립적으로 진행 가능.
> 다만 Phase 5의 trade-table은 Phase 6에서 재사용하므로, 5 → 6 순서 권장.

---

## 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-02-18 | 초안 작성 — Phase 0 완료 상태 기준, 9단계 구현 플랜 |
