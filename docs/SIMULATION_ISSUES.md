# 시뮬레이션 모드 이슈 & 구현 계획

> 작성일: 2026-02-18 (updated: 2026-02-19)
> 목적: 대시보드만으로 퀀트 전략 시뮬레이션 실행 시 발생하는 문제점 정리 및 수정 계획
> **상태: Phase 1–4 모두 완료 (2026-02-19)**

---

## 현재 상태 요약

| 영역 | 구현도 | 실사용 가능? |
|------|--------|-------------|
| 전략 실행 (3개) | 100% | ✅ 경고 로그 추가됨 |
| 데이터 수집 | 95% | ✅ 장 운영일/데이터 신선도 체크 추가 |
| 시뮬레이션 모드 | 100% | ✅ 포지션 가격 갱신, 트랜잭션 적용 |
| 페이퍼 트레이딩 | 100% | ✅ 잔고 추적 + 초과 매수 차단 |
| 대시보드 UI | 100% | ✅ 토스트 에러, 캐시 무효화, 벤치마크 연동 |
| 백테스트 | 100% | 정상 |
| 킬스위치/리스크 | 100% | 정상 |
| 테스트 | **100%** | ✅ 49 tests (E2E + 전략 유닛) |

---

## 핵심 문제점 (모두 해결됨)

### ~~P0: 모의 실행 시 수량 0주 / 가격 ₩0 (3중 버그)~~ ✅ Phase 1

- ① 시그널 프리뷰에 `~N주 / ~₩X` 예상 수량/가격 표시 (`signal-preview.tsx`)
- ② `paper_trading_service.execute_signal()`에서 `simulation_mode=True` + `PortfolioTracker` 전달
- ③ `RiskManager.calculate_position_size()`에 `initial_capital` fallback 추가
- 커밋: `ce32db9`

### ~~P0: 포지션 가격이 갱신되지 않음~~ ✅ Phase 1

- `executor._update_sim_prices()` 추가 — 매매 실행 전 시뮬레이션 포지션 현재가 갱신
- 커밋: `ce32db9`

### ~~P0: 전략 시그널 생성 실패 시 사일런트~~ ✅ Phase 1

- 3개 전략 모두 `prepare_signal_kwargs()`에서 데이터 부족/누락 시 경고 로그 추가
- `bot/run` 응답에 전략별 시그널 수 상세 포함
- 커밋: `ce32db9`

### ~~P1: 휴일/장 마감 시 데이터 수집 실패~~ ✅ Phase 2

- `collector._check_market_hours()` — KR(KST 09:00-15:30)/US(EST 09:30-16:00) 장 운영 시간 확인
- `collector._check_data_freshness()` — 3일 이상 데이터 갭 시 경고
- 커밋: `95e4937`

### ~~P1: 페이퍼 트레이딩 잔고 제한 없음~~ ✅ Phase 2

- `paper_sessions`에 `initial_capital`/`cash` 컬럼 추가 (마이그레이션 포함)
- 매매 시 현금 차감, 잔고 초과 매수 차단
- 커밋: `95e4937`

### ~~P1: 시뮬레이션/실거래 모드 전환 검증 없음~~ ✅ Phase 1

- `executor._execute_buy()`/`_execute_sell()`에 `simulation.enabled=true` 시 실주문 차단 가드 추가
- 커밋: `ce32db9`

### ~~P2: 벤치마크 탭 포트폴리오 시계열 미연동~~ ✅ Phase 3

- `sim_portfolio_snapshots` 테이블 + `save_snapshot()`/`get_snapshots()` 메서드
- `/py/benchmark/portfolio-series` API 엔드포인트
- `benchmark/route.ts`에서 실제 포트폴리오 시계열 연동 (forward-fill)
- 커밋: `3984203`

### ~~P2: DB 트랜잭션 안전성 없음~~ ✅ Phase 4

- `execute_buy()`/`execute_sell()` — `engine.begin()` 단일 트랜잭션으로 원자적 실행
- 커밋: `e637900`

### ~~P2: 대시보드 캐시 5분 → 실시간성 부족~~ ✅ Phase 3

- `invalidateCache()` 함수 추가, `bot/run` 후 포트폴리오/벤치마크 캐시 즉시 무효화
- API 에러 시 토스트 알림 (`toast-provider.tsx`)
- 커밋: `3984203`

---

## 구현 이력

### Phase 1: 시뮬레이션 필수 수정 ✅ `ce32db9`

| # | 작업 | 상태 |
|---|------|------|
| 1 | `paper_trading_service.execute_signal()`에서 `simulation_mode=True` + `PortfolioTracker` 전달 | ✅ |
| 2 | `RiskManager.calculate_position_size()`에 `initial_capital` fallback 추가 | ✅ |
| 3 | 시그널 프리뷰에서 예상 수량/가격 표시 (`~N주 / ~₩X`) | ✅ |
| 4 | executor에서 시뮬레이션 포지션 현재가 업데이트 (`_update_sim_prices`) | ✅ |
| 5 | `simulation.enabled=true`일 때 실주문 차단 가드 | ✅ |
| 6 | `prepare_signal_kwargs` 빈 반환 시 경고 로그 추가 (3개 전략) | ✅ |
| 7 | `bot/run` 응답에 전략별 시그널 결과 상세 포함 | ✅ |

### Phase 2: 페이퍼 트레이딩 & 데이터 신뢰성 ✅ `95e4937`

| # | 작업 | 상태 |
|---|------|------|
| 8 | `paper_sessions`에 `initial_capital`/`cash` 컬럼 추가, 매매 시 차감 | ✅ |
| 9 | 수집 시 장 운영시간 확인 (`_check_market_hours`) | ✅ |
| 10 | 수집된 데이터 날짜 확인, 3일+ 갭 시 경고 (`_check_data_freshness`) | ✅ |

### Phase 3: 대시보드 UX 개선 ✅ `3984203`

| # | 작업 | 상태 |
|---|------|------|
| 11 | `bot/run` 후 포트폴리오/벤치마크 캐시 무효화 (`invalidateCache`) | ✅ |
| 12 | API 에러 시 토스트 알림 (`toast-provider.tsx`, `useApi` 연동) | ✅ |
| 13 | 시뮬레이션 스냅샷 기반 벤치마크 포트폴리오 시계열 연동 | ✅ |

### Phase 4: 안정성 & 테스트 ✅ `e637900`

| # | 작업 | 상태 |
|---|------|------|
| 14 | `execute_buy`/`execute_sell` DB 트랜잭션 (`engine.begin()`) 적용 | ✅ |
| 15 | 시뮬레이션 E2E 테스트 — 13 tests (`tests/test_simulation_e2e.py`) | ✅ |
| 16 | 전략 유닛 테스트 — 36 tests (`tests/test_strategies.py`) | ✅ |

**총 49 tests, 전체 통과 (0.84s)**
