# src/backtest — 백테스팅 엔진

과거 데이터에 대해 전략을 시뮬레이션하고 성과를 분석합니다.

---

## 모듈 목록

### engine.py — 백테스트 시뮬레이터

**클래스**: `BacktestEngine`, `BacktestResult`, `Trade`

| 메서드 | 역할 |
|--------|------|
| `run(price_data, start_date, end_date)` | 백테스트 실행 → `BacktestResult` 반환 |

**시뮬레이션 흐름** (일별):
```
가격 업데이트 → 손절 체크 → generate_signals() → 리스크 검증 → 가상 체결 → 에퀴티 기록
```

**특징**:
- 수수료 + 슬리피지 모델링
- Look-ahead bias 방지 (현재 날짜까지만 데이터 사용)
- RiskManager 통합 (동일한 리스크 체크 적용)
- 기존 전략 코드 재사용 (`generate_signals()` 그대로 호출)

**의존**: `BaseStrategy`, `RiskManager`, `config`

---

### analyzer.py — 성과 분석기

**클래스**: `PerformanceAnalyzer`

| 메서드 | 역할 |
|--------|------|
| `summary()` | 핵심 지표 dict 반환 |
| `print_report()` | 콘솔 리포트 출력 |

**핵심 지표**:
- 총 수익률, CAGR, 연 변동성
- 샤프 비율, 소르티노 비율
- MDD (일자 + 복구일)
- 승률, 손익비, 평균 보유일
- 월별 수익률 테이블

**의존**: `BacktestResult`

---

### runner.py — 통합 백테스트 실행기

정의: `src/backtest/runner.py:45-384`

**클래스**: `BacktestRunner`

CLI (`main.py backtest`, `main.py backtest-yf`)와 대시보드 (`dashboard/services/backtest_service.py`)에서 공통으로 사용하는 오케스트레이터.

| 메서드 | 역할 |
|--------|------|
| `run(strategy_name, start_date, end_date, ...)` | 단일 전략 백테스트 → `(BacktestResult, metrics)` |
| `run_all(start_date, end_date, ...)` | 모든 활성 전략 백테스트 |
| `run_per_pair(strategy_name, start_date, end_date, ...)` | 페어별 개별 백테스트 → `{pair: (result, metrics)}` |
| `print_pair_comparison(results, ...)` | 페어별 비교 테이블 출력 |
| `report(result, charts, csv)` | 콘솔 리포트 + 차트 + CSV 출력 |

**데이터 로드 전략**:

```
1. DB에서 전략 required_codes() 종목 데이터 로드
2. DB 데이터가 start_date 이전 LOOKBACK_EXTRA(400일) 충분한지 확인
3. 충분 → DB 데이터 사용 (data_source: "DB")
4. 부족 → yfinance 폴백 (data_source: "yfinance")
5. yfinance도 실패 → DB 데이터라도 사용 (거래 0건 가능 경고)
```

**핵심 상수**:
- `LOOKBACK_EXTRA = 400`: 전략 룩백 기간 버퍼 (캘린더일). `start_date` 이전 이 기간만큼의 데이터가 DB에 있어야 DB 소스를 사용.

**전략 생성**: `_create_strategy(name)` — `STRATEGY_REGISTRY`에서 인스턴스 자동 생성. 새 전략 추가 시 runner 수정 불필요.

**의존**: `BacktestEngine`, `PerformanceAnalyzer`, `BacktestReporter`, `DataFeed` (선택), `STRATEGY_REGISTRY`

---

### report.py — 리포트 생성기

정의: `src/backtest/report.py:35-185`

**클래스**: `BacktestReporter`

| 메서드 | 역할 | 출력 |
|--------|------|------|
| `plot_equity_curve(result, save_path)` | 자산 곡선 + 드로다운 차트 | PNG 파일 |
| `plot_monthly_returns(result, save_path)` | 월별 수익률 히트맵 | PNG 파일 |
| `export_trades_csv(result, path)` | 거래 내역 CSV 내보내기 | CSV 파일 |

**특징**:
- matplotlib 선택 의존 (`MPL_AVAILABLE` 플래그로 graceful degradation)
- 기본 저장 경로: `backtest_{strategy_name}_{type}.{ext}`
- 비대화형 백엔드 (`Agg`) — 서버/CLI 환경에서 사용 가능

**의존**: `BacktestResult`, `matplotlib` (선택), `pandas`

---

### DB 유틸리티

`runner.py` 하단에 정의된 헬퍼 함수:

| 함수 | 역할 |
|------|------|
| `_get_db_engine()` | SQLite 엔진 (`data/trading_bot.db`) |
| `_load_prices_from_db(code, market)` | 종목별 가격 데이터 로드 → DataFrame |

> `dashboard/services/backtest_service.py`에서도 이 함수들을 import하여 사용합니다.

---

## 사용 예시

### CLI

```bash
# DB 데이터 기반 백테스트 (모든 전략)
python3 main.py backtest

# DB 데이터 기반 백테스트 (특정 전략)
python3 main.py backtest --strategy stat_arb

# yfinance 기반 백테스트 (API 키 불필요)
python3 main.py backtest-yf -s dual_momentum --start 2020-01-01 --end 2024-12-31

# yfinance 기반 + 자본금/수수료 지정
python3 main.py backtest-yf -s stat_arb --start 2020-01-01 --end 2024-12-31 \
    --capital 50000000 --commission 0.0003 --slippage 0.002
```

### Python

```python
from src.backtest.runner import BacktestRunner

runner = BacktestRunner()

# 단일 전략 백테스트
result, metrics = runner.run("dual_momentum", "2020-01-01", "2024-12-31")

# 리포트 출력 (콘솔 + 차트 + CSV)
runner.report(result, charts=True, csv=True)

# 모든 활성 전략 백테스트
all_results = runner.run_all("2020-01-01", "2024-12-31")
```

```python
# 엔진 직접 사용 (저수준 API)
from src.backtest.engine import BacktestEngine
from src.backtest.analyzer import PerformanceAnalyzer
from src.strategies.stat_arb import StatArbStrategy

engine = BacktestEngine(StatArbStrategy(), initial_capital=10_000_000)
result = engine.run(price_data)  # {종목코드: DataFrame}
PerformanceAnalyzer(result).print_report()
```
