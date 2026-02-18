# Project Status

최종 업데이트: 2026-02-18

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
- Python API 5개 라우터 (portfolio, backtest, bot, signals, paper)
- 웹 대시보드 6탭 전체 구현 및 백엔드 연동
- KIS API 통합 (실매매 + 모의투자)
- 백테스트 엔진 (3개 전략, yfinance 기반, inf/NaN 안전 직렬화)
- 백테스트 실행 로그 (전략별 사람이 읽을 수 있는 요약)
- 전략 인스턴스 CRUD (웹에서 전략 생성/삭제)
- 전략 파라미터 편집 (숫자/문자열 + pairs + universe_codes)
- 동적 전략 UI (settings.yaml 변경 자동 반영)
- 페이퍼 트레이딩 에러 핸들링 (세션별 오류 분리)
- 다크 모드 (기본값)
- Cloudflare Pages + Tunnel 배포 파이프라인

## 미완성 / 제한사항

| 항목 | 상태 | 비고 |
|------|------|------|
| quant_factor 전략 | disabled | settings.yaml에서 `enabled: false` |
| 테스트 | 미구현 | 테스트 플랜만 작성됨 (docs/TEST_PLAN.md) |
| Settings API | Next.js 직접 처리 | Python API 라우터 없음, settings.yaml 직접 읽기/쓰기 |

## 활성 전략 (settings.yaml 기준)

| 전략 | 상태 | 주요 설정 |
|------|------|----------|
| stat_arb | ENABLED | MSFT_GOOGL US 페어 (인스턴스 분리 가능) |
| dual_momentum | ENABLED | KR/US ETF 페어, 월 1일 리밸런싱 |
| quant_factor | DISABLED | 멀티팩터 스코어링, 20+ 종목 유니버스 |

## 최근 주요 변경 (2026-02-18)

1. **전략 파라미터 편집 확장**: pairs, universe_codes, 문자열 파라미터(ETF 코드 등) 편집 가능
2. **백테스트 안정화**: inf/NaN 안전 직렬화 (`_SafeEncoder`), null-safe KPI 표시
3. **백테스트 실행 로그**: 전략별 사람이 읽을 수 있는 요약 메시지 (공적분 결과, 모멘텀 비교 등)
4. **거래 내역 개선**: 총 매매금액(amount) 컬럼 추가
5. **페이퍼 트레이딩**: 세션별 에러 핸들링 개선 (PR #9)
6. **전략 인스턴스 CRUD**: 웹 UI에서 전략 생성/삭제 가능
7. **동적 전략 UI**: 하드코딩 전략명 제거, settings.yaml에서 동적 로딩
8. **다크 모드 가시성**: OKLCH lightness 조정으로 대비 개선
9. **코드 리뷰 P0 수정**: 보안, 성능, 비동기 관련 5개 크리티컬 이슈 해결
