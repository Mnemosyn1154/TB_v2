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
| GET | `/py/portfolio` | 현재 포트폴리오 (보유 종목, 리스크 지표) |

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
| POST | `/py/bot/collect` | 데이터 수집 실행 |
| POST | `/py/bot/run` | 전략 1회 실행 (수집 → 분석 → 매매) |
| GET | `/py/bot/kill-switch` | 킬스위치 상태 조회 |
| POST | `/py/bot/kill-switch/activate` | 킬스위치 활성화 (매매 중단) |
| POST | `/py/bot/kill-switch/deactivate` | 킬스위치 비활성화 |

Bot 실행 응답: `{ "data": { "log": "실행 로그 문자열" }, "error": null }`

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

---

## Next.js API Routes

### Python API 프록시 라우트

| Next.js Path | Method | Python Endpoint |
|-------------|--------|-----------------|
| `/api/portfolio` | GET | `/py/portfolio` |
| `/api/signals` | GET | `/py/signals` |
| `/api/backtest/run` | POST | `/py/backtest/run` |
| `/api/backtest/run-per-pair` | POST | `/py/backtest/run-per-pair` |
| `/api/backtest/pairs/[strategy]` | GET | `/py/backtest/pairs/{strategy}` |
| `/api/bot/status` | GET | `/py/bot/status` |
| `/api/bot/run` | POST | `/py/bot/run` |
| `/api/bot/collect` | POST | `/py/bot/collect` |
| `/api/bot/kill-switch` | GET | `/py/bot/kill-switch` |
| `/api/bot/kill-switch` | POST | `/py/bot/kill-switch/{action}` |
| `/api/paper/sessions` | GET/POST | `/py/paper/sessions` |
| `/api/paper/sessions/active` | GET | `/py/paper/sessions/active` |
| `/api/paper/sessions/[id]/summary` | GET | `/py/paper/sessions/{id}/summary` |
| `/api/paper/sessions/[id]/trades` | GET | `/py/paper/sessions/{id}/trades` |
| `/api/paper/sessions/[id]/stop` | POST | `/py/paper/sessions/{id}/stop` |
| `/api/paper/execute` | POST | `/py/paper/execute` |

### 직접 처리 라우트 (Python API 미사용)

| Next.js Path | Method | 처리 방식 |
|-------------|--------|----------|
| `/api/settings` | GET | `config/settings.yaml` 파일 읽기 |
| `/api/settings` | PUT | `config/settings.yaml` 파일 쓰기 |
| `/api/settings/strategies` | POST | settings.yaml에 새 전략 인스턴스 추가 |
| `/api/settings/strategies/[key]` | DELETE | settings.yaml에서 전략 인스턴스 삭제 |
| `/api/settings/strategies/[key]/toggle` | PATCH | 전략 enabled/disabled 토글 |
| `/api/benchmark` | GET | yahoo-finance2로 KOSPI/S&P500 데이터 조회 |

Benchmark 쿼리 파라미터: `?period=1M|3M|6M|1Y|ALL`

---

## 프론트엔드 API 클라이언트

`web/lib/api-client.ts`에 정의된 함수:

```typescript
// Portfolio (5분 캐시)
getPortfolio()

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
