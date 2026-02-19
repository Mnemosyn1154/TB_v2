# Project Status

최종 업데이트: 2026-02-19

## 구현 단계 상태

| Phase | 설명 | 상태 |
|-------|------|------|
| 0 | 프로젝트 스캐폴딩 (Next.js, shadcn/ui, FastAPI 구조) | DONE |
| 1 | Python API 라우터 (portfolio, backtest, bot, signals, paper) | DONE |
| 2 | Portfolio 탭 (보유종목, 리스크 지표, KPI 카드) | DONE |
| 3 | Benchmark 탭 (Yahoo Finance, 전략 vs 시장 비교) | DONE |
| 4 | Strategy 설정 탭 (토글, 파라미터 편집, 유니버스 뷰어) | DONE |
| 5 | Backtest 탭 (에쿼티 커브, 드로다운, 히트맵, 거래 테이블) | DONE |
| 6 | Paper Trading 탭 (세션 관리, 시그널 실행, 거래 이력) | DONE |
| 7 | Control 탭 (모드 전환, 킬스위치, 실시간 로그) | DONE |
| 8 | 통합 & 폴리시 (공통 컴포넌트, API 캐싱, 반응형) | DONE |
| 9 | 배포 인프라 (Cloudflare Pages/Tunnel, systemd, GitHub Actions) | DONE |

상세: `docs/mainplan.md` 참조 (Phase 0 상태 테이블은 outdated — 실제로는 모두 완료).

## 작동하는 기능

- 전체 매매 사이클: CLI로 데이터 수집 → 시그널 생성 → 주문 실행
- Python API 7개 라우터 (portfolio, backtest, bot, signals, paper, benchmark, simulation)
- 웹 대시보드 6탭 전체 구현 및 백엔드 연동
- KIS API 통합 (실매매 + 모의투자)
- 백테스트 엔진 (3개 전략, yfinance 기반, inf/NaN 안전 직렬화)
- 백테스트 실행 로그 (전략별 사람이 읽을 수 있는 요약)
- 전략 인스턴스 CRUD (웹에서 전략 생성/삭제)
- 전략 파라미터 편집 (숫자/문자열 + pairs + universe_codes + sectors)
- 동적 전략 UI (settings.yaml 변경 자동 반영)
- 페이퍼 트레이딩 에러 핸들링 (세션별 오류 분리, 잔고 추적 + 초과 매수 차단)
- 벤치마크 데이터 DB 캐싱 (SQLite 우선, yfinance 보충) + 포트폴리오 시계열 연동
- 시뮬레이션 모드 (SQLite 기반 가상 포트폴리오, 기본 ON)
  - 실주문 차단 가드, DB 트랜잭션, 포지션 가격 갱신, 일별 스냅샷
  - RiskManager initial_capital fallback, 시그널 프리뷰 예상 수량/가격
- 대시보드 UX: 토스트 에러 알림, bot/run 후 캐시 자동 무효화
- 장 운영시간 체크 (KR/US), 데이터 신선도 경고
- 테스트: 49 tests (시뮬레이션 E2E + 전략 유닛)
- 다크 모드 (기본값)
- Cloudflare Pages + Tunnel 배포 파이프라인

## 미완성 / 제한사항

| 항목 | 상태 | 비고 |
|------|------|------|
| quant_factor 전략 | disabled | settings.yaml에서 `enabled: false` |
| sam_hynix 인스턴스 | disabled | 삼성전자/SK하이닉스 KR 페어, `enabled: false` |
| Settings API | Next.js 직접 처리 | Python API 라우터 없음, settings.yaml 직접 읽기/쓰기 |

## 활성 전략 (settings.yaml 기준)

| 전략 | config_key | 상태 | 주요 설정 |
|------|-----------|------|----------|
| stat_arb | `stat_arb` | ENABLED | 4 US 페어 (KO_PEP, XOM_CVX, V_MA, MSFT_GOOGL), coint_pvalue=0.1 |
| dual_momentum | `dual_momentum` | ENABLED | KR(069500)/US(SPY) ETF, 월 1일 리밸런싱 |
| sector_rotation | `sector_rotation` | ENABLED | US 7섹터 + KR 3섹터 ETF, top_n=3, 6개월 룩백 |
| quant_factor | `quant_factor` | DISABLED | 멀티팩터 스코어링, KR 25 + US 15 = 40종목 유니버스 |
| sam_hynix | `sam_hynix` | DISABLED | stat_arb 타입, 삼성전자/SK하이닉스 KR 페어 |

## 최근 주요 변경

### 2026-02-19: 시뮬레이션 이슈 수정 (Phase 1–4)

1. **Phase 1 — 시뮬레이션 필수 수정** (`ce32db9`): 3중 버그(수량 0/가격 0) 해결, 실주문 차단 가드, 포지션 가격 갱신, 전략 경고 로그
2. **Phase 2 — 페이퍼 트레이딩 & 데이터 신뢰성** (`95e4937`): 세션 잔고 추적, 장 운영시간 체크, 데이터 신선도 경고
3. **Phase 3 — 대시보드 UX 개선** (`3984203`): 캐시 무효화, 토스트 에러 알림, 벤치마크 포트폴리오 시계열 연동
4. **Phase 4 — 안정성 & 테스트** (`e637900`): DB 트랜잭션, 시뮬레이션 E2E 테스트 13건, 전략 유닛 테스트 36건
5. **전략 설정 확장**: stat_arb 4페어(KO_PEP, XOM_CVX, V_MA, MSFT_GOOGL), sector_rotation 신규, quant_factor 유니버스 40종목, sam_hynix KR 페어 인스턴스

상세: `docs/SIMULATION_ISSUES.md` 참조

### 2026-02-18: 기능 구현 완료

1. **벤치마크 DB 캐싱 (PR #10)**: 벤치마크 데이터를 Python API로 이전, SQLite 캐시 + yfinance 보충
2. **시뮬레이션 모드 (PR #11)**: `PortfolioTracker`(SQLite)로 가상 포트폴리오 영속 관리
3. **전략 파라미터 편집 확장**: pairs, universe_codes, 문자열 파라미터 편집 가능
4. **백테스트 안정화**: inf/NaN 안전 직렬화, null-safe KPI, 실행 로그
5. **전략 인스턴스 CRUD**: 웹 UI에서 전략 생성/삭제 가능
6. **동적 전략 UI**: settings.yaml에서 동적 로딩
7. **코드 리뷰 P0 수정**: 보안, 성능, 비동기 관련 5개 크리티컬 이슈 해결
