# Test Plan — Phase 1, 2, 3

> Phase 1 (Python API 라우터), Phase 2 (자산 현황 탭), Phase 3 (벤치마크 비교 탭) 구현에 대한 테스트 계획.
> 작성일: 2026-02-18
>
> **현재 구현 상태 (2026-02-19)**:
> - Python 테스트: 94 tests 통과 (시뮬레이션 E2E 13개 + 전략 유닛 81개)
> - 테스트 위치: `tests/test_simulation_e2e.py`, `tests/test_strategies.py`
> - 프론트엔드 테스트: 미구현 (Vitest 미설정)
> - API 라우터 테스트: 미구현 (아래 계획 중 `tests/api/` 부분 미시작)
>
> 실제 구현된 테스트는 아래 계획과 다른 구조입니다.
> 계획의 `tests/api/` 라우터 테스트와 `web/__tests__/` 프론트엔드 테스트는 향후 구현 대상입니다.

---

## 목차

1. [테스트 인프라 구성](#1-테스트-인프라-구성)
2. [Phase 1: Python API 테스트](#2-phase-1-python-api-테스트)
3. [Phase 2: Portfolio 프론트엔드 테스트](#3-phase-2-portfolio-프론트엔드-테스트)
4. [Phase 3: Benchmark 테스트](#4-phase-3-benchmark-테스트)
5. [통합 테스트 (E2E)](#5-통합-테스트-e2e)
6. [테스트 실행 방법](#6-테스트-실행-방법)

---

## 1. 테스트 인프라 구성

### Python (pytest)

```
필요 패키지: pytest, pytest-asyncio, httpx (TestClient용)
위치: tests/api/
설정: conftest.py에 공통 fixture 정의
```

| 항목 | 설정 |
|------|------|
| 프레임워크 | pytest + httpx (FastAPI TestClient) |
| Mock | unittest.mock (서비스 레이어 mock) |
| 구조 | `tests/api/` 하위에 라우터별 파일 |
| 환경변수 | `PYTHON_API_SECRET=""` (테스트 시 인증 우회) |

### Frontend (Vitest + React Testing Library)

```
필요 패키지: vitest, @testing-library/react, @testing-library/jest-dom, msw
위치: web/__tests__/
설정: vitest.config.ts
```

| 항목 | 설정 |
|------|------|
| 프레임워크 | Vitest (Next.js 호환) |
| 컴포넌트 테스트 | React Testing Library |
| API Mock | MSW (Mock Service Worker) |
| 구조 | `web/__tests__/` 하위에 도메인별 파일 |

---

## 2. Phase 1: Python API 테스트

### 2-1. 시크릿 인증 미들웨어 (`pyapi/deps.py`)

| ID | 테스트 케이스 | 검증 항목 | 우선순위 |
|----|-------------|----------|---------|
| AUTH-01 | 시크릿 미설정 시 모든 요청 통과 | `PYTHON_API_SECRET=""` → 403 없이 정상 응답 | P0 |
| AUTH-02 | 올바른 시크릿 전송 | `X-Internal-Secret` 일치 → 정상 응답 | P0 |
| AUTH-03 | 잘못된 시크릿 전송 | `X-Internal-Secret` 불일치 → 403 | P0 |
| AUTH-04 | 시크릿 헤더 누락 | 헤더 없음 → 403 | P0 |

```python
# tests/api/test_auth.py 구조
def test_no_secret_env_allows_all(client_no_secret):
    """PYTHON_API_SECRET 미설정 → 인증 우회"""
    res = client_no_secret.get("/py/health")
    assert res.status_code == 200

def test_valid_secret_passes(client):
    """올바른 시크릿 → 정상 응답"""
    res = client.get("/py/health", headers={"X-Internal-Secret": "test-secret"})
    assert res.status_code == 200

def test_invalid_secret_rejected(client):
    """잘못된 시크릿 → 403"""
    res = client.get("/py/portfolio", headers={"X-Internal-Secret": "wrong"})
    assert res.status_code == 403
```

### 2-2. Portfolio 라우터 (`pyapi/routers/portfolio.py`)

| ID | 테스트 케이스 | 검증 항목 | 우선순위 |
|----|-------------|----------|---------|
| PORT-01 | 정상 포트폴리오 조회 | GET `/py/portfolio` → `{data: {...}, error: null}` | P0 |
| PORT-02 | 응답 구조 검증 | `data`에 `kr`, `us`, `risk` 키 존재 | P0 |
| PORT-03 | KIS API 실패 시 에러 전달 | 서비스 예외 → `{data: {error: "..."}, error: null}` | P1 |
| PORT-04 | risk 필드 구조 검증 | `total_equity`, `cash`, `cash_pct`, `daily_pnl`, `drawdown`, `positions_count`, `max_positions`, `kill_switch` 존재 | P1 |

```python
# tests/api/test_portfolio.py 구조
@patch("pyapi.routers.portfolio.get_portfolio_status")
def test_get_portfolio_success(mock_service, client):
    """정상 조회 → data에 kr/us/risk 포함"""
    mock_service.return_value = {
        "kr": {"positions": []},
        "us": {"positions": []},
        "risk": {"total_equity": 50000000, "cash": 30000000, ...},
    }
    res = client.get("/py/portfolio")
    assert res.status_code == 200
    body = res.json()
    assert body["error"] is None
    assert "kr" in body["data"]
    assert "us" in body["data"]
    assert "risk" in body["data"]
```

### 2-3. Backtest 라우터 (`pyapi/routers/backtest.py`)

| ID | 테스트 케이스 | 검증 항목 | 우선순위 |
|----|-------------|----------|---------|
| BT-01 | 백테스트 실행 성공 | POST `/py/backtest/run` → metrics, equity_curve, trades 포함 | P0 |
| BT-02 | 요청 검증 (Pydantic) | 필수 필드 누락 → 422 | P0 |
| BT-03 | 기본값 적용 | `initial_capital`, `commission_rate`, `slippage_rate` 기본값 | P1 |
| BT-04 | 페어별 백테스트 | POST `/py/backtest/run-per-pair` → 페어별 결과 dict | P1 |
| BT-05 | 페어 목록 조회 | GET `/py/backtest/pairs/{strategy}` → 문자열 배열 | P1 |
| BT-06 | 존재하지 않는 전략 | 서비스 예외 → `{data: null, error: "..."}` | P1 |
| BT-07 | equity_curve 직렬화 | dates(문자열 배열) + values(숫자 배열) 구조 | P1 |
| BT-08 | trades 직렬화 | 각 trade에 date, strategy, code, market, side, quantity, price, pnl 필드 | P1 |
| BT-09 | monthly_returns 직렬화 | index, columns, data 키 존재 | P2 |
| BT-10 | pnl_values 필터링 | pnl이 None이거나 0인 항목 제외 | P2 |

```python
# tests/api/test_backtest.py 구조
@patch("pyapi.routers.backtest.run_backtest")
def test_run_backtest_success(mock_run, client):
    """정상 실행 → 직렬화된 결과"""
    mock_run.return_value = (mock_backtest_result(), {"total_return": 0.15, ...})
    res = client.post("/py/backtest/run", json={
        "strategy": "stat_arb",
        "start_date": "2025-01-01",
        "end_date": "2025-12-31",
    })
    assert res.status_code == 200
    data = res.json()["data"]
    assert "metrics" in data
    assert "equity_curve" in data
    assert "trades" in data

def test_missing_required_fields(client):
    """필수 필드 누락 → 422"""
    res = client.post("/py/backtest/run", json={"strategy": "stat_arb"})
    assert res.status_code == 422
```

### 2-4. Bot 라우터 (`pyapi/routers/bot.py`)

| ID | 테스트 케이스 | 검증 항목 | 우선순위 |
|----|-------------|----------|---------|
| BOT-01 | 데이터 수집 성공 | POST `/py/bot/collect` → `{data: {log: "..."}}` | P0 |
| BOT-02 | 전략 1회 실행 성공 | POST `/py/bot/run` → `{data: {log: "..."}}` | P0 |
| BOT-03 | Kill Switch 상태 조회 | GET `/py/bot/kill-switch` → `{data: {kill_switch: bool}}` | P0 |
| BOT-04 | Kill Switch 활성화 | POST `/py/bot/kill-switch/activate` → `{data: {kill_switch: true}}` | P0 |
| BOT-05 | Kill Switch 비활성화 | POST `/py/bot/kill-switch/deactivate` → `{data: {kill_switch: false}}` | P0 |
| BOT-06 | 데이터 수집 실패 | 서비스 예외 → `{data: null, error: "..."}` | P1 |
| BOT-07 | 전략 실행 실패 | 서비스 예외 → `{data: null, error: "..."}` | P1 |

### 2-5. Signals 라우터 (`pyapi/routers/signals.py`)

| ID | 테스트 케이스 | 검증 항목 | 우선순위 |
|----|-------------|----------|---------|
| SIG-01 | 시그널 조회 성공 | GET `/py/signals` → 시그널 배열 | P0 |
| SIG-02 | `_raw` 필드 제거 | 응답에 `_raw` 키 없음 | P0 |
| SIG-03 | 시그널 필드 검증 | 각 시그널에 strategy, code, market, signal, quantity, price, reason 포함 | P1 |
| SIG-04 | 빈 시그널 | 시그널 없을 때 → `{data: [], error: null}` | P1 |
| SIG-05 | 서비스 예외 | 예외 → `{data: null, error: "..."}` | P1 |

### 2-6. Paper Trading 라우터 (`pyapi/routers/paper.py`)

| ID | 테스트 케이스 | 검증 항목 | 우선순위 |
|----|-------------|----------|---------|
| PAP-01 | 세션 생성 | POST `/py/paper/sessions` → 세션 정보 반환 | P0 |
| PAP-02 | 활성 세션 조회 | GET `/py/paper/sessions/active` → 세션 또는 null | P0 |
| PAP-03 | 세션 종료 | POST `/py/paper/sessions/{id}/stop` → `{stopped: true}` | P0 |
| PAP-04 | 세션 목록 조회 | GET `/py/paper/sessions` → 세션 배열 | P1 |
| PAP-05 | 단건 시그널 실행 | POST `/py/paper/execute` (signal_index 포함) → 단건 결과 | P1 |
| PAP-06 | 전체 시그널 실행 | POST `/py/paper/execute` (signal_index 없음) → 전체 결과 | P1 |
| PAP-07 | 인덱스 범위 초과 | `signal_index >= len(signals)` → 에러 메시지 | P1 |
| PAP-08 | 시그널 없을 때 실행 | 빈 시그널 → 안내 메시지 | P1 |
| PAP-09 | 거래 내역 조회 | GET `/py/paper/sessions/{id}/trades` → 거래 배열 | P1 |
| PAP-10 | 거래 요약 조회 | GET `/py/paper/sessions/{id}/summary` → total_trades, buy_count, sell_count | P1 |
| PAP-11 | 존재하지 않는 세션 | 없는 session_id → 빈 결과 또는 에러 | P2 |

### 2-7. Pydantic 스키마 검증 (`pyapi/schemas.py`)

| ID | 테스트 케이스 | 검증 항목 | 우선순위 |
|----|-------------|----------|---------|
| SCH-01 | BacktestRequest 기본값 | initial_capital=50_000_000, commission=0.00015, slippage=0.001 | P1 |
| SCH-02 | BacktestRequest 전체 필드 | 모든 필드 설정 시 정상 파싱 | P1 |
| SCH-03 | BacktestRequest 필수 필드 누락 | strategy, start_date, end_date 누락 → ValidationError | P1 |
| SCH-04 | pair_name 선택적 | pair_name 없이도 유효 | P2 |

### 2-8. Health Check & 라우터 등록

| ID | 테스트 케이스 | 검증 항목 | 우선순위 |
|----|-------------|----------|---------|
| APP-01 | Health 엔드포인트 | GET `/py/health` → `{status: "ok"}` | P0 |
| APP-02 | CORS 설정 | `Access-Control-Allow-Origin: http://localhost:3000` | P1 |
| APP-03 | 모든 라우터 등록 확인 | OpenAPI 스키마에 5개 라우터의 엔드포인트 전체 포함 | P1 |

---

## 3. Phase 2: Portfolio 프론트엔드 테스트

### 3-1. `MetricsCard` 컴포넌트 (`web/components/common/metrics-card.tsx`)

| ID | 테스트 케이스 | 검증 항목 | 우선순위 |
|----|-------------|----------|---------|
| MC-01 | 기본 렌더링 | icon, label, value가 화면에 표시 | P0 |
| MC-02 | description 표시 | description prop → 텍스트 노출 | P1 |
| MC-03 | 양수 change 스타일 | `changePositive=true` → `text-success` 클래스 | P1 |
| MC-04 | 음수 change 스타일 | `changePositive=false` → `text-destructive` 클래스 | P1 |
| MC-05 | change 미제공 | change prop 없음 → 변화량 영역 미표시 | P2 |

### 3-2. `PortfolioKPIs` 컴포넌트 (`web/components/portfolio/portfolio-kpis.tsx`)

| ID | 테스트 케이스 | 검증 항목 | 우선순위 |
|----|-------------|----------|---------|
| KPI-01 | 4개 KPI 카드 렌더링 | 총자산, 일일 손익, 현금 비중, 드로다운 카드 모두 표시 | P0 |
| KPI-02 | 총자산 포맷 | `risk.total_equity` → KRW 포맷 (₩) | P0 |
| KPI-03 | 현금 비중 파싱 | `risk.cash_pct = "45.2%"` → `+45.2%` 표시 | P1 |
| KPI-04 | 일일 손익 색상 | 양수 → 녹색 change, 음수 → 빨강 change | P1 |
| KPI-05 | 포지션 정보 | `포지션 N / M` 형태로 description 표시 | P2 |

### 3-3. `StrategyCards` 컴포넌트 (`web/components/portfolio/strategy-cards.tsx`)

| ID | 테스트 케이스 | 검증 항목 | 우선순위 |
|----|-------------|----------|---------|
| SC-01 | 전략 카드 렌더링 | 전략별 이름, ON/OFF Badge 표시 | P0 |
| SC-02 | 활성 전략 수익률 | `enabled=true` → 수익률 + 포지션 수 표시 | P0 |
| SC-03 | 비활성 전략 스타일 | `enabled=false` → `opacity-50` + "비활성" 텍스트 | P1 |
| SC-04 | 양수 수익률 색상 | `pnl_pct > 0` → `text-success` | P1 |
| SC-05 | 음수 수익률 색상 | `pnl_pct < 0` → `text-destructive` | P1 |
| SC-06 | 빈 배열 | `strategies=[]` → null 반환 (렌더링 안 함) | P2 |

### 3-4. `HoldingsTable` 컴포넌트 (`web/components/portfolio/holdings-table.tsx`)

| ID | 테스트 케이스 | 검증 항목 | 우선순위 |
|----|-------------|----------|---------|
| HT-01 | KR 탭 기본 표시 | 초기 상태에서 "국내" 탭 활성 | P0 |
| HT-02 | 종목 데이터 렌더링 | 종목명, 수량, 평균가, 현재가, 수익률, 평가손익 표시 | P0 |
| HT-03 | KR/US 탭 전환 | "해외" 클릭 → US 포지션 표시 | P0 |
| HT-04 | 통화 포맷 분기 | KR → ₩, US → $ | P1 |
| HT-05 | 수익률 색상 | 양수 → `text-success`, 음수 → `text-destructive` | P1 |
| HT-06 | 빈 상태 | `positions=[]` → "보유 종목이 없습니다" 표시 | P1 |
| HT-07 | 탭 활성 스타일 | 선택된 탭 → `bg-primary text-primary-foreground` | P2 |

### 3-5. `RiskIndicators` 컴포넌트 (`web/components/portfolio/risk-indicators.tsx`)

| ID | 테스트 케이스 | 검증 항목 | 우선순위 |
|----|-------------|----------|---------|
| RI-01 | MDD 표시 | `risk.drawdown` 값 렌더링 | P0 |
| RI-02 | 포지션 비율 표시 | `N / M` 형태 | P0 |
| RI-03 | Kill Switch OFF | `kill_switch=false` → "OFF" Badge + 녹색 스타일 | P0 |
| RI-04 | Kill Switch ON | `kill_switch=true` → "ON" Badge + destructive 스타일 | P0 |
| RI-05 | 툴팁 텍스트 | MDD, 포지션 지표에 설명 툴팁 | P2 |

### 3-6. `PortfolioTab` 컴포넌트 (`web/components/portfolio/portfolio-tab.tsx`)

| ID | 테스트 케이스 | 검증 항목 | 우선순위 |
|----|-------------|----------|---------|
| PT-01 | 로딩 상태 | `loading=true, data=null` → 스피너 표시 | P0 |
| PT-02 | 에러 상태 | `error="...", data=null` → 에러 메시지 + "다시 시도" 버튼 | P0 |
| PT-03 | 정상 데이터 렌더링 | data 있음 → KPI + 전략 + 종목 + 리스크 표시 | P0 |
| PT-04 | 새로고침 버튼 | 클릭 → `refetch()` 호출 | P1 |
| PT-05 | 전략 데이터 없음 | `strategies=[]` → 전략 섹션 미표시 | P1 |
| PT-06 | data=null | `loading=false, error=null, data=null` → null 반환 | P2 |

### 3-7. `usePortfolio` 훅 (`web/hooks/use-portfolio.ts`)

| ID | 테스트 케이스 | 검증 항목 | 우선순위 |
|----|-------------|----------|---------|
| UP-01 | 초기 fetch | 마운트 시 `getPortfolio()` 호출 | P0 |
| UP-02 | 성공 응답 처리 | `{data: {...}, error: null}` → data 세팅 | P0 |
| UP-03 | 에러 응답 처리 | `{data: null, error: "..."}` → error 세팅 | P0 |
| UP-04 | 5분 폴링 | `useInterval(refetch, 300000)` 호출 | P1 |
| UP-05 | refetch 함수 | 수동 호출 시 재조회 | P1 |
| UP-06 | fetch 예외 처리 | 네트워크 에러 → error 상태 | P1 |

### 3-8. `useApi` 훅 (`web/hooks/use-api.ts`)

| ID | 테스트 케이스 | 검증 항목 | 우선순위 |
|----|-------------|----------|---------|
| UA-01 | 초기 상태 | `loading=true, data=null, error=null` | P0 |
| UA-02 | 성공 후 상태 | `loading=false, data={...}, error=null` | P0 |
| UA-03 | API 에러 후 상태 | `loading=false, data=null, error="..."` | P0 |
| UA-04 | 네트워크 에러 | throw Error → `error=에러메시지` | P1 |
| UA-05 | refetch | `refetch()` 호출 → loading 재설정 후 fetch | P1 |

### 3-9. 포맷터 유틸리티 (`web/lib/formatters.ts`)

| ID | 테스트 케이스 | 검증 항목 | 우선순위 |
|----|-------------|----------|---------|
| FMT-01 | `formatKRW(50000000)` | `₩50,000,000` | P0 |
| FMT-02 | `formatKRW(0)` | `₩0` | P1 |
| FMT-03 | `formatKRW(-1500000)` | `-₩1,500,000` | P1 |
| FMT-04 | `formatUSD(1234.56)` | `$1,234.56` | P0 |
| FMT-05 | `formatPercent(12.5)` | `+12.5%` | P0 |
| FMT-06 | `formatPercent(-3.2)` | `-3.2%` | P0 |
| FMT-07 | `formatPercent(0)` | `0.0%` | P1 |
| FMT-08 | `formatNumber(10000)` | `10,000` | P1 |
| FMT-09 | `formatDate("2026-01-15")` | `2026. 01. 15.` | P1 |
| FMT-10 | `formatDateShort("2026-01-15")` | `01. 15.` | P2 |

### 3-10. API Client (`web/lib/api-client.ts`)

| ID | 테스트 케이스 | 검증 항목 | 우선순위 |
|----|-------------|----------|---------|
| AC-01 | `getPortfolio()` 호출 | GET `/api/portfolio` 요청 | P0 |
| AC-02 | `getBenchmark("6M")` 호출 | GET `/api/benchmark?period=6M` 요청 | P1 |
| AC-03 | `runBacktest(params)` 호출 | POST `/api/backtest/run` + JSON body | P1 |
| AC-04 | Content-Type 헤더 | `application/json` 설정 | P1 |

### 3-11. Python Proxy (`web/lib/python-proxy.ts`)

| ID | 테스트 케이스 | 검증 항목 | 우선순위 |
|----|-------------|----------|---------|
| PP-01 | `pythonGet` 정상 응답 | Python API → JSON 반환 | P0 |
| PP-02 | `pythonPost` body 전달 | JSON.stringify된 body + Content-Type | P0 |
| PP-03 | `X-Internal-Secret` 헤더 전송 | 환경변수 값이 헤더에 포함 | P0 |
| PP-04 | Python API 비정상 응답 | `res.ok=false` → Error throw | P1 |
| PP-05 | `cache: "no-store"` 설정 | 캐시 미사용 확인 | P2 |

### 3-12. Next.js API Route (`web/app/api/portfolio/route.ts`)

| ID | 테스트 케이스 | 검증 항목 | 우선순위 |
|----|-------------|----------|---------|
| NR-01 | 정상 프록시 | GET → `pythonGet("/py/portfolio")` 호출 후 JSON 반환 | P0 |
| NR-02 | Python API 연결 실패 | catch → `{data: null, error: "..."}` + status 502 | P0 |

---

## 4. Phase 3: Benchmark 테스트

> Phase 3는 현재 플레이스홀더 상태이므로, 기존 스캐폴딩(타입, API 라우트, api-client 함수)에 대한 테스트와 구현 시 필요한 테스트 명세를 함께 기술.

### 4-1. Benchmark 타입 정의 (`web/types/benchmark.ts`)

| ID | 테스트 케이스 | 검증 항목 | 우선순위 |
|----|-------------|----------|---------|
| BT-T01 | `BenchmarkMetrics` 타입 호환성 | 필수 필드: portfolio_return, kospi_return, sp500_return, alpha, beta, information_ratio | P1 |
| BT-T02 | `StrategyComparison` 타입 호환성 | 필수 필드: strategy, return_pct, benchmark_return, excess_return | P1 |
| BT-T03 | `BenchmarkData` 타입 호환성 | dates, portfolio, kospi, sp500, metrics, strategy_comparison 필드 | P1 |

> TypeScript 컴파일 시 타입 에러 없으면 통과 (별도 런타임 테스트 불필요)

### 4-2. Benchmark API Route (`web/app/api/benchmark/route.ts`) — 현재 플레이스홀더

| ID | 테스트 케이스 | 검증 항목 | 우선순위 |
|----|-------------|----------|---------|
| BM-01 | 플레이스홀더 응답 구조 | `{data: {dates:[], portfolio:[], ...}, error: null}` | P0 |
| BM-02 | period 파라미터 전달 | `?period=6M` → 응답의 `period: "6M"` | P1 |
| BM-03 | period 기본값 | 파라미터 없으면 `period: "3M"` | P1 |

### 4-3. Benchmark API Client 함수

| ID | 테스트 케이스 | 검증 항목 | 우선순위 |
|----|-------------|----------|---------|
| BC-01 | `getBenchmark()` 기본 호출 | GET `/api/benchmark?period=3M` | P1 |
| BC-02 | `getBenchmark("1Y")` | GET `/api/benchmark?period=1Y` | P1 |

### 4-4. 구현 시 추가 테스트 (향후)

Phase 3 구현 완료 시 아래 테스트가 필요함:

#### Yahoo Finance 데이터 조회

| ID | 테스트 케이스 | 검증 항목 | 우선순위 |
|----|-------------|----------|---------|
| YF-01 | KOSPI 데이터 조회 | `^KS11` 심볼로 시세 조회 성공 | P0 |
| YF-02 | S&P500 데이터 조회 | `^GSPC` 심볼로 시세 조회 성공 | P0 |
| YF-03 | 기간별 데이터 | 1M, 3M, 6M, 1Y, ALL 각각 정상 조회 | P1 |
| YF-04 | Yahoo Finance 실패 | API 에러 → 에러 응답 | P1 |

#### Alpha/Beta/IR 계산

| ID | 테스트 케이스 | 검증 항목 | 우선순위 |
|----|-------------|----------|---------|
| ABIR-01 | Alpha 계산 | 포트폴리오 수익률 - 벤치마크 수익률 | P0 |
| ABIR-02 | Beta 계산 | 포트폴리오와 벤치마크의 공분산/분산 | P0 |
| ABIR-03 | IR 계산 | 초과수익률 / 추적오차 | P0 |
| ABIR-04 | 데이터 부족 시 | 데이터 포인트 불충분 → 0 또는 null 반환 | P1 |

#### Benchmark 커스텀 훅 (use-benchmark.ts — 미구현)

| ID | 테스트 케이스 | 검증 항목 | 우선순위 |
|----|-------------|----------|---------|
| UB-01 | 초기 로드 | 마운트 시 기본 기간(3M)으로 fetch | P0 |
| UB-02 | 기간 변경 | period 상태 변경 → 자동 재조회 | P0 |
| UB-03 | 로딩/에러 상태 | useApi와 동일한 상태 관리 | P1 |

#### Benchmark 컴포넌트 (미구현)

| ID | 테스트 케이스 | 검증 항목 | 우선순위 |
|----|-------------|----------|---------|
| BC-C01 | PeriodSelector 렌더링 | 1M, 3M, 6M, 1Y, 전체 버튼 표시 | P0 |
| BC-C02 | PeriodSelector 클릭 | 기간 선택 → onPeriodChange 콜백 호출 | P0 |
| BC-C03 | BenchmarkChart 렌더링 | 3개 라인 (포트폴리오, KOSPI, S&P500) 표시 | P0 |
| BC-C04 | AlphaBetaCards 렌더링 | Alpha, Beta, IR 3개 카드 표시 | P0 |
| BC-C05 | AlphaBetaCards 색상 | Alpha > 0 → 녹색, < 0 → 빨강 | P1 |
| BC-C06 | StrategyVsMarket 테이블 | 전략별 수익률 vs 벤치마크 수익률 + 초과수익 표시 | P1 |
| BC-C07 | 빈 데이터 | 데이터 없음 → 안내 메시지 | P2 |

---

## 5. 통합 테스트 (E2E)

### 5-1. Phase 1 통합: Python API 전체 플로우

| ID | 테스트 케이스 | 검증 항목 | 우선순위 |
|----|-------------|----------|---------|
| E2E-01 | Health → Portfolio 순차 호출 | 두 엔드포인트 모두 정상 응답 | P0 |
| E2E-02 | 시크릿 인증 + API 호출 | 올바른 시크릿으로 모든 라우터 접근 가능 | P0 |
| E2E-03 | Paper Trading 전체 플로우 | 세션 생성 → 시그널 조회 → 실행 → 거래 내역 → 세션 종료 | P1 |
| E2E-04 | Kill Switch 전체 플로우 | 상태 조회 → 활성화 → 상태 확인 → 비활성화 → 상태 확인 | P1 |

### 5-2. Phase 2 통합: 프론트엔드 ↔ 백엔드

| ID | 테스트 케이스 | 검증 항목 | 우선순위 |
|----|-------------|----------|---------|
| E2E-05 | Portfolio 탭 데이터 로드 | 브라우저 → Next.js API → Python API → KIS API → 화면 표시 | P0 |
| E2E-06 | 자동 폴링 | 5분 후 자동 갱신 확인 | P2 |
| E2E-07 | Python API 미연결 시 | 에러 메시지 + "다시 시도" 버튼 표시 | P1 |

### 5-3. Phase 3 통합 (구현 후)

| ID | 테스트 케이스 | 검증 항목 | 우선순위 |
|----|-------------|----------|---------|
| E2E-08 | Benchmark 탭 기간 선택 | 기간 버튼 클릭 → 차트 업데이트 | P0 |
| E2E-09 | Alpha/Beta/IR 표시 | 벤치마크 데이터 로드 → 지표 카드 표시 | P0 |
| E2E-10 | 전략별 비교 테이블 | 전략별 수익률 vs 벤치마크 데이터 표시 | P1 |

---

## 6. 테스트 실행 방법

### Python 테스트

```bash
# 루트에서 실행
pytest tests/api/ -v

# 특정 파일
pytest tests/api/test_portfolio.py -v

# 특정 테스트
pytest tests/api/test_portfolio.py::test_get_portfolio_success -v
```

### Frontend 테스트

```bash
# web/ 디렉토리에서 실행
cd web && npx vitest run

# watch 모드
cd web && npx vitest

# 특정 파일
cd web && npx vitest run __tests__/portfolio-kpis.test.tsx

# 커버리지
cd web && npx vitest run --coverage
```

### conftest.py 구조 (Python)

```python
# tests/api/conftest.py
import os
import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def client():
    """시크릿 설정된 테스트 클라이언트"""
    os.environ["PYTHON_API_SECRET"] = "test-secret"
    from pyapi.main import app
    return TestClient(app)

@pytest.fixture
def client_no_secret():
    """시크릿 미설정 테스트 클라이언트"""
    os.environ.pop("PYTHON_API_SECRET", None)
    from pyapi.main import app
    return TestClient(app)

@pytest.fixture
def auth_headers():
    return {"X-Internal-Secret": "test-secret"}
```

---

## 테스트 커버리지 목표

| 영역 | 현재 | 목표 | 비고 |
|------|------|------|------|
| Python API 라우터 | 0% | 80%+ | 서비스 레이어는 mock |
| 프론트엔드 컴포넌트 | 0% | 70%+ | 렌더링 + 인터랙션 |
| 유틸리티 함수 | 0% | 90%+ | 순수 함수, 테스트 용이 |
| 커스텀 훅 | 0% | 70%+ | renderHook 사용 |
| 통합 (E2E) | 0% | 주요 플로우 | P0 시나리오 |

---

## 우선순위 정의

| 등급 | 의미 | 기준 |
|------|------|------|
| P0 | 필수 | 핵심 기능 정상 동작 확인. 머지 전 반드시 통과 |
| P1 | 중요 | 에지 케이스, 에러 처리. 릴리스 전 통과 권장 |
| P2 | 보조 | 스타일, 접근성, 마이너 케이스. 여유 시 추가 |

---

## 파일 구조 (예상)

```
TB_v2/
├── tests/
│   └── api/
│       ├── conftest.py
│       ├── test_auth.py           # AUTH-01~04
│       ├── test_health.py         # APP-01~03
│       ├── test_portfolio.py      # PORT-01~04
│       ├── test_backtest.py       # BT-01~10
│       ├── test_bot.py            # BOT-01~07
│       ├── test_signals.py        # SIG-01~05
│       ├── test_paper.py          # PAP-01~11
│       └── test_schemas.py        # SCH-01~04
├── web/
│   └── __tests__/
│       ├── setup.ts               # Vitest 전역 설정
│       ├── mocks/
│       │   └── portfolio-data.ts  # 테스트 fixture 데이터
│       ├── components/
│       │   ├── metrics-card.test.tsx     # MC-01~05
│       │   ├── portfolio-kpis.test.tsx   # KPI-01~05
│       │   ├── strategy-cards.test.tsx   # SC-01~06
│       │   ├── holdings-table.test.tsx   # HT-01~07
│       │   ├── risk-indicators.test.tsx  # RI-01~05
│       │   └── portfolio-tab.test.tsx    # PT-01~06
│       ├── hooks/
│       │   ├── use-api.test.ts           # UA-01~05
│       │   └── use-portfolio.test.ts     # UP-01~06
│       └── lib/
│           ├── formatters.test.ts        # FMT-01~10
│           └── api-client.test.ts        # AC-01~04
```
