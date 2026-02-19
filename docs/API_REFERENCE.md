# API Reference

## 개요

- **Python API** (FastAPI, port 8000): 트레이딩 코어 기능 (포트폴리오, 백테스트, 봇, 시그널, 페이퍼)
- **Next.js API Routes** (port 3000): Python API 프록시 + 설정/벤치마크 직접 처리
- **인증**: `X-Internal-Secret` 헤더 (`PYTHON_API_SECRET` 환경변수)
- **응답 형식**: `{ "data": T | null, "error": string | null }`

---

## Python API 엔드포인트

### Health

| Method | Path | 설명 | 인증 |
|--------|------|------|------|
| GET | `/py/health` | API 상태 확인 | 불필요 |

응답: `{ "status": "ok", "message": "D2trader Python API is running" }`

### Portfolio

| Method | Path | 설명 |
|--------|------|------|
| GET | `/py/portfolio` | 현재 포트폴리오 (보유 종목, 리스크 지표, 시뮬레이션/실거래 자동 분기) |
| GET | `/py/portfolio/capital` | 초기 자본금 + 현금 잔고 조회 (시뮬레이션 모드) |
| POST | `/py/portfolio/capital` | 초기 자본금 설정 (포트폴리오 리셋) |
| POST | `/py/portfolio/reset` | 포트폴리오 리셋 (초기 자본금 유지, 포지션 삭제) |

**SetCapitalRequest** (POST body):
```json
{ "amount": 10000000 }
```

### Backtest

| Method | Path | 설명 |
|--------|------|------|
| POST | `/py/backtest/run` | 백테스트 실행 (전체 또는 특정 페어) |
| POST | `/py/backtest/run-per-pair` | 페어별 개별 백테스트 |
| GET | `/py/backtest/pairs/{strategy}` | 전략의 가용 페어 목록 |

**BacktestRequest** (POST body):
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

**BacktestResult** (응답 data):
```json
{
  "metrics": { "total_return": 0.25, "cagr": 0.05, "sharpe_ratio": 1.2, "mdd": -0.15, ... },
  "equity_curve": { "dates": ["2020-01-01", ...], "values": [50000000, ...] },
  "monthly_returns": { "index": [...], "columns": [...], "data": [[...]] },
  "trades": [{ "date", "strategy", "code", "market", "side", "quantity", "price", "commission", "pnl", "pnl_pct", "holding_days" }],
  "pnl_values": [1000, -500, ...]
}
```

### Bot Control

| Method | Path | 설명 |
|--------|------|------|
| GET | `/py/bot/mode` | 현재 운영 모드 조회 (시뮬레이션/실거래) |
| POST | `/py/bot/mode` | 운영 모드 전환 |
| GET | `/py/bot/health/kis` | KIS API 연결 상태 (계좌/토큰/잔고) |
| POST | `/py/bot/collect` | 데이터 수집 실행 |
| POST | `/py/bot/run` | 전략 1회 실행 (수집 → 분석 → 매매) |
| GET | `/py/bot/status` | 봇 통합 상태 (킬스위치 + 스케줄러) |
| GET | `/py/bot/kill-switch` | 킬스위치 상태 조회 |
| POST | `/py/bot/kill-switch/activate` | 킬스위치 활성화 (매매 중단) |
| POST | `/py/bot/kill-switch/deactivate` | 킬스위치 비활성화 |
| POST | `/py/bot/scheduler/start` | 스케줄러 시작 (15분 주기 자동 실행) |
| POST | `/py/bot/scheduler/stop` | 스케줄러 중지 |
| GET | `/py/bot/orders` | 당일 주문/체결 내역 조회 |

Bot 실행 응답: `{ "data": { "log": "실행 로그 문자열" }, "error": null }`

Bot 상태 응답:
```json
{
  "data": {
    "kill_switch": false,
    "scheduler": {
      "running": true,
      "interval_minutes": 15,
      "next_run": "2026-02-19T09:15:00+09:00",
      "last_run": { "time": "...", "status": "success", "total_signals": 3 }
    }
  },
  "error": null
}
```

### Signals

| Method | Path | 설명 |
|--------|------|------|
| GET | `/py/signals` | 현재 매매 시그널 (dry-run 미리보기) |

응답 data: 시그널 객체 배열 `[{ market, code, side, quantity, price, ... }]`

### Paper Trading

| Method | Path | 설명 |
|--------|------|------|
| POST | `/py/paper/sessions` | 새 세션 생성 |
| GET | `/py/paper/sessions` | 전체 세션 목록 |
| GET | `/py/paper/sessions/active` | 활성 세션 조회 |
| POST | `/py/paper/sessions/{session_id}/stop` | 세션 중지 |
| POST | `/py/paper/execute` | 시그널 실행 (페이퍼) |
| GET | `/py/paper/sessions/{session_id}/trades` | 세션별 거래 내역 |
| GET | `/py/paper/sessions/{session_id}/summary` | 세션별 요약 통계 |

**ExecuteRequest** (POST body):
```json
{
  "session_id": "abc-123",
  "signal_index": null
}
```
`signal_index`가 null이면 모든 시그널 실행.

### Benchmark

| Method | Path | 설명 |
|--------|------|------|
| GET | `/py/benchmark/data` | 벤치마크 인덱스 가격 (KOSPI, S&P 500, DB 캐시 + yfinance 보충) |
| GET | `/py/benchmark/data-range` | 커스텀 기간 벤치마크 데이터 (백테스트 비교용) |
| GET | `/py/benchmark/portfolio-series` | 시뮬레이션 포트폴리오 일별 시계열 (스냅샷 기반) |

#### `/py/benchmark/data`

쿼리 파라미터: `?period=1M|3M|6M|1Y|ALL`

응답 data:
```json
{
  "kospi": { "dates": ["2024-01-02", ...], "prices": [2600.5, ...] },
  "sp500": { "dates": ["2024-01-02", ...], "prices": [4750.2, ...] }
}
```

#### `/py/benchmark/data-range`

쿼리 파라미터: `?start=2020-01-01&end=2024-12-31`

커스텀 날짜 범위로 벤치마크 데이터 조회. 백테스트 결과와 시장 지수 비교 시 사용.

응답 data: `/py/benchmark/data`와 동일한 형식.

#### `/py/benchmark/portfolio-series`

쿼리 파라미터: `?period=3M` (기본 3M)

시뮬레이션 포트폴리오의 일별 총자산 시계열. `PortfolioTracker`의 스냅샷 데이터 기반.

응답 data:
```json
{
  "dates": ["2026-02-01", "2026-02-02", ...],
  "values": [10000000, 10050000, ...]
}
```

---

## Next.js API Routes

### Python API 프록시 라우트

| Next.js Path | Method | Python Endpoint |
|-------------|--------|-----------------|
| `/api/portfolio` | GET | `/py/portfolio` |
| `/api/portfolio/capital` | GET/POST | `/py/portfolio/capital` |
| `/api/portfolio/reset` | POST | `/py/portfolio/reset` |
| `/api/signals` | GET | `/py/signals` |
| `/api/backtest/run` | POST | `/py/backtest/run` |
| `/api/backtest/run-per-pair` | POST | `/py/backtest/run-per-pair` |
| `/api/backtest/pairs/[strategy]` | GET | `/py/backtest/pairs/{strategy}` |
| `/api/bot/status` | GET | `/py/bot/status` |
| `/api/bot/run` | POST | `/py/bot/run` |
| `/api/bot/collect` | POST | `/py/bot/collect` |
| `/api/bot/kill-switch` | GET | `/py/bot/kill-switch` |
| `/api/bot/kill-switch` | POST | `/py/bot/kill-switch/{action}` |
| `/api/bot/scheduler` | POST | `/py/bot/scheduler/{action}` |
| `/api/bot/mode` | GET/POST | `/py/bot/mode` |
| `/api/bot/health` | GET | `/py/bot/health/kis` |
| `/api/bot/orders` | GET | `/py/bot/orders` |
| `/api/paper/sessions` | GET/POST | `/py/paper/sessions` |
| `/api/paper/sessions/active` | GET | `/py/paper/sessions/active` |
| `/api/paper/sessions/[id]/summary` | GET | `/py/paper/sessions/{id}/summary` |
| `/api/paper/sessions/[id]/trades` | GET | `/py/paper/sessions/{id}/trades` |
| `/api/paper/sessions/[id]/stop` | POST | `/py/paper/sessions/{id}/stop` |
| `/api/paper/execute` | POST | `/py/paper/execute` |
| `/api/benchmark` | GET | `/py/benchmark/data` |
| `/api/benchmark/portfolio-series` | GET | `/py/benchmark/portfolio-series` |

### 직접 처리 라우트 (Python API 미사용)

| Next.js Path | Method | 처리 방식 |
|-------------|--------|----------|
| `/api/settings` | GET | `config/settings.yaml` 파일 읽기 |
| `/api/settings` | PUT | `config/settings.yaml` 파일 쓰기 |
| `/api/settings/strategies` | POST | settings.yaml에 새 전략 인스턴스 추가 |
| `/api/settings/strategies/[key]` | DELETE | settings.yaml에서 전략 인스턴스 삭제 |
| `/api/settings/strategies/[key]/toggle` | PATCH | 전략 enabled/disabled 토글 |

---

## 프론트엔드 API 클라이언트

`web/lib/api-client.ts`에 정의된 함수:

```typescript
// Portfolio (5분 캐시)
getPortfolio()
getCapital()
setCapital(amount: number)
resetPortfolio()

// Benchmark (15분 캐시)
getBenchmark(period?: string)

// Settings
getSettings()
updateSettings(data)

// Backtest
runBacktest(params)
runBacktestPerPair(params)
getBacktestPairs(strategy)

// Bot
runBot()
collectData()
getKillSwitch()
toggleKillSwitch(action: "activate" | "deactivate")
getBotStatus()
toggleScheduler(action: "start" | "stop")

// Signals
getSignals()

// Paper Trading
getPaperSessions()
getActivePaperSession()
createPaperSession()
stopPaperSession(id)
getPaperTrades(id)
getPaperSummary(id)
executePaperSignals(sessionId, signalIndex?)
```

모든 함수는 `Promise<ApiResponse<T>>` 반환: `{ data: T | null, error: string | null }`.
