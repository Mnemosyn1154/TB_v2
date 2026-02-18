# dashboard — 웹 대시보드 (Streamlit)

Streamlit 기반 웹 UI. 백테스트, 포트폴리오, 전략 설정, 봇 제어, 모의 거래를 제공합니다.

---

## 실행 방법

```bash
streamlit run dashboard/app.py
```

---

## 구조

```
dashboard/
├── app.py                        # Streamlit 진입점 + 사이드바 라우팅
├── views/                        # 페이지 (각각 render() 함수 제공)
│   ├── p1_backtest.py            # 백테스트 실행 + 결과 시각화
│   ├── p2_portfolio.py           # KIS API 잔고 + 리스크 상태
│   ├── p3_settings.py            # settings.yaml 편집 UI
│   ├── p4_control.py             # 데이터 수집, 전략 실행, Kill Switch
│   └── p5_paper_trading.py       # 모의 거래 (시그널 미리보기 + 실행)
├── services/                     # 비즈니스 로직 (views → services → src.*)
│   ├── backtest_service.py       # BacktestRunner 래퍼
│   ├── bot_service.py            # 데이터 수집, 전략 실행, Kill Switch
│   ├── config_service.py         # settings.yaml 읽기/쓰기
│   ├── portfolio_service.py      # KIS API 잔고 조회
│   └── paper_trading_service.py  # 모의 거래 세션 + 주문
└── components/                   # 재사용 UI 컴포넌트
    ├── charts.py                 # Plotly 차트 (에퀴티, 드로다운, 히트맵, 손익분포)
    ├── metrics.py                # KPI 메트릭 카드 (백테스트, 포트폴리오)
    └── trade_table.py            # 거래 내역 테이블 포맷터
```

---

## 페이지 상세

### p1_backtest — 백테스트

- 전략 선택 (stat_arb / dual_momentum / quant_factor)
- 기간, 자본금, 수수료/슬리피지 설정
- 실행 → 에퀴티 커브, 드로다운, 월별 수익률, 거래 내역 표시
- `backtest_service.py` → `BacktestRunner` (DB 우선 → yfinance 폴백)

### p2_portfolio — 포트폴리오

- KIS API 국내/해외 잔고 실시간 조회
- 리스크 KPI 카드 (총자산, 현금, 드로다운, Kill Switch)
- **자격증명 사전 검증**: API 호출 전 `app_key`, `app_secret`, `account_no` 유무 확인
- `portfolio_service.py` → `KISBroker.get_kr_balance()` / `get_us_balance()`

### p3_settings — 전략 설정

6개 탭으로 구성:

| 탭 | 기능 |
|----|------|
| **StatArb** | 페어 CRUD (인라인 편집, 2단계 삭제 확인), US 페어 거래소 선택 (NAS/NYS) |
| **DualMomentum** | ETF 코드 편집, US ETF 거래소 선택 |
| **QuantFactor** | 유니버스 종목 필터링/추가/삭제, US 종목 거래소 선택 |
| **리스크 관리** | 포지션 비중, 손절, MDD, 현금비중 슬라이더 |
| **백테스트** | 자본금, 시장별 수수료 (`commission_rate_kr/us`, `tax_rate_kr`), 슬리피지 |
| **API / 알림** | 모의투자↔실거래 전환 (2단계 확인), rate_limit, 텔레그램 이벤트별 알림 |

- **입력 검증 함수** (저장 전 실행):
  - `_validate_pair()` — StatArb 페어 필드/형식 검증
  - `_validate_universe_stock()` — QuantFactor 유니버스 종목 검증
  - `_validate_config_before_save()` — 전체 설정 빈값 검사
- `config_service.py` → 원자적 YAML 읽기/쓰기

### p4_control — 봇 제어

- 데이터 수집 버튼 (`collect_data()`)
- 전략 1회 실행 버튼 (`run_once()`)
- Kill Switch 토글 (파일 영속화: `data/kill_switch.json`)
- 실행 로그 실시간 표시
- `bot_service.py` → `STRATEGY_REGISTRY` 기반 전략 인스턴스 생성

### p5_paper_trading — 모의 거래

- 시그널 미리보기 (Dry-Run): 전략 시그널만 생성, 주문 안 함
- 개별/일괄 시그널 실행: KIS 모의투자 서버로 실제 주문 전송
- 세션 관리 (생성/종료/이력)
- `paper_trading_service.py` → 세션 DB (`paper_sessions`, `paper_trades`)

---

## 의존 관계

```
dashboard/views/ → dashboard/services/ → src.*
                 → dashboard/components/ (UI만)
```

> dashboard는 `src`에 의존하지만, `src`는 dashboard에 의존하지 않습니다.

---

## 새 페이지 추가

1. `dashboard/views/p6_new_page.py` — `render()` 함수 작성
2. `dashboard/app.py` — 사이드바 메뉴 + 라우팅 추가
3. (선택) `dashboard/services/new_service.py` — 비즈니스 로직 분리
