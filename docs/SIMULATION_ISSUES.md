# 시뮬레이션 모드 이슈 & 구현 계획

> 작성일: 2026-02-18 (updated: 2026-02-19)
> 목적: 대시보드만으로 퀀트 전략 시뮬레이션 실행 시 발생하는 문제점 정리 및 수정 계획

---

## 현재 상태 요약

| 영역 | 구현도 | 실사용 가능? |
|------|--------|-------------|
| 전략 실행 (3개) | 100% | 동작하지만 사일런트 실패 위험 |
| 데이터 수집 | 90% | 휴일/마감일 미처리 |
| 시뮬레이션 모드 | 80% | **포지션 가격 갱신 안 됨** |
| 페이퍼 트레이딩 | 90% | 잔고 제한 없음 |
| 대시보드 UI | 95% | 에러 표시 부족 |
| 백테스트 | 100% | 정상 |
| 킬스위치/리스크 | 100% | 정상 |
| 테스트 | **0%** | 미구현 |

---

## 핵심 문제점

### P0: 모의 실행 시 수량 0주 / 가격 ₩0 (3중 버그)

대시보드에서 시그널 프리뷰 → "전체 모의 실행"을 눌러도 수량 0주, 가격 ₩0으로 표시되며 실제 체결이 안 됨.
원인이 3단계에 걸쳐 있음:

**① 전략이 quantity/price를 설정하지 않음**
- `TradeSignal` 기본값이 `quantity=0`, `price=0.0`
- 전략(DualMomentum 등)은 신호만 생성하고 수량/가격을 executor에 위임하는 설계
- 그런데 프리뷰 화면(`signal-preview.tsx`)이 이 값을 그대로 표시 → 0주/₩0
- 관련 파일: `src/strategies/base.py:30-31`, `web/components/paper/signal-preview.tsx:88-92`

**② paper_trading_service의 OrderExecutor 초기화 오류**
- `execute_signal()`에서 `OrderExecutor(broker, rm, dm, notifier)` 생성 시:
  - `simulation_mode=True` 누락 → 실거래 모드로 동작
  - `portfolio_tracker` 미전달 → 시뮬레이션 포트폴리오 미연동
- 관련 파일: `dashboard/services/paper_trading_service.py:228`

**③ RiskManager.calculate_position_size()가 0 반환**
- 새로 생성된 RiskManager의 `total_equity=0` → 수량 계산 결과 0
- `initial_capital` 기반 fallback 없음
- 관련 파일: `src/core/risk_manager.py:234-244`

### P0: 포지션 가격이 갱신되지 않음

- `PortfolioTracker.update_position_price()`가 존재하지만 **아무 곳에서도 호출되지 않음**
- 매수 후 entry_price = current_price 고정 → P&L이 항상 0%
- 관련 파일: `src/execution/executor.py` → `src/core/portfolio_tracker.py:196-208`

### P0: 전략 시그널 생성 실패 시 사일런트

- `prepare_signal_kwargs()`에서 데이터 부족 시 빈 dict 반환, 로그 없음
- 대시보드에서 "Run" 눌러도 왜 시그널이 없는지 알 수 없음
- 관련 파일: `src/strategies/stat_arb.py:176`, `dual_momentum.py:100,105`, `quant_factor.py:108`

### P1: 휴일/장 마감 시 데이터 수집 실패

- 휴일 캘린더 없음, 장 마감 체크 없음
- 휴일에 수집하면 빈 데이터 또는 전일 데이터 사일런트 사용
- 관련 파일: `src/execution/collector.py`

### P1: 페이퍼 트레이딩 잔고 제한 없음

- `paper_trades` 테이블에 기록만 하고 현금 잔고 추적 없음
- 무한 매수 가능 → 비현실적 시뮬레이션 결과

### P1: 시뮬레이션/실거래 모드 전환 검증 없음

- `simulation.enabled`와 `broker.live_trading` 설정이 독립적
- 둘 다 true면 실제 주문 나감 → 위험

### P2: 벤치마크 탭 포트폴리오 시계열 미연동

- `web/app/api/benchmark/route.ts:72` — `TODO: 실제 포트폴리오 시계열 연동`
- 벤치마크 대비 내 포트폴리오 수익률 비교 불가

### P2: DB 트랜잭션 안전성 없음

- 매매 기록/포지션/포트폴리오 업데이트가 원자적이지 않음
- 앱 크래시 시 부분 상태 남음

### P2: 대시보드 캐시 5분 → 실시간성 부족

- 시뮬레이션 실행 후 결과 확인까지 최대 5분 대기

---

## 구현 계획

### Phase 1: 시뮬레이션 필수 수정 (핵심 동작 보장)

| # | 작업 | 검증 방법 |
|---|------|-----------|
| 1 | `paper_trading_service.execute_signal()`에서 `simulation_mode=True` + `PortfolioTracker` 전달 | 모의 실행 시 KIS API 미호출, 시뮬레이션 포트폴리오에 기록 확인 |
| 2 | `RiskManager.calculate_position_size()`에 `initial_capital` fallback 추가 | `total_equity=0`일 때도 설정의 initial_capital 기반으로 수량 계산 |
| 3 | 시그널 프리뷰에서 예상 수량/가격 표시 (현재가 조회 + 포지션 사이즈 계산) | 프리뷰에 "약 N주 / 약 ₩X" 표시 |
| 4 | executor에서 시뮬레이션 포지션 현재가 업데이트 호출 | 매수 후 시간 경과 시 P&L 변동 확인 |
| 5 | `simulation.enabled=true`일 때 실주문 차단 검증 | 설정 불일치 시 경고 로그 + 주문 차단 |
| 6 | `prepare_signal_kwargs` 빈 반환 시 경고 로그 추가 | 데이터 부족 시 로그에 원인 표시 |
| 7 | `bot/run` 응답에 전략별 시그널 결과 상세 포함 | 대시보드에서 "시그널 0건 (데이터 부족)" 등 표시 |

### Phase 2: 페이퍼 트레이딩 & 데이터 신뢰성

| # | 작업 | 검증 방법 |
|---|------|-----------|
| 8 | `paper_sessions`에 initial_capital/cash 컬럼 추가, 매매 시 차감 | 잔고 초과 매수 시 거부 |
| 9 | 수집 시 장 운영일 확인, 장외 시간이면 경고 | 휴일 수집 시도 시 명확한 메시지 |
| 10 | 수집된 데이터의 날짜 확인, 오래된 데이터 경고 | 3일 이상 갭 시 경고 로그 |

### Phase 3: 대시보드 UX 개선

| # | 작업 | 검증 방법 |
|---|------|-----------|
| 11 | `bot/run` 후 포트폴리오 캐시 무효화 + 자동 리프레시 | Run 후 즉시 포지션 변경 반영 |
| 12 | API 에러 시 토스트/배너로 원인 표시 | KIS 연결 실패 등 에러 상황에서 명확한 메시지 |
| 13 | `sim_portfolio_history`에서 일별 수익률 추출, 벤치마크와 비교 | 벤치마크 차트에 내 포트폴리오 라인 표시 |

### Phase 4: 안정성 & 테스트

| # | 작업 | 검증 방법 |
|---|------|-----------|
| 14 | 매매 실행 경로에 BEGIN/COMMIT/ROLLBACK 적용 | 중간 실패 시 롤백 확인 |
| 15 | 시뮬레이션 매수→매도→P&L 계산 E2E 테스트 | pytest 통과 |
| 16 | 각 전략의 시그널 생성 로직 단위 테스트 | pytest 통과 |

---

## 권장 진행 순서

**Phase 1 → 2 → 3 → 4**

Phase 1만 완료해도 대시보드 시뮬레이션의 기본 동작이 보장된다.
