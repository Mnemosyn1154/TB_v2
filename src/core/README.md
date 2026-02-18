# src/core — 핵심 인프라 모듈

이 패키지는 외부 시스템(KIS API, SQLite DB, Yahoo Finance)과의 통신 및 시스템 공통 기능을 담당합니다.

---

## 모듈 목록

### config.py — 설정 로더

| 함수 | 설명 |
|------|------|
| `get_config()` | `settings.yaml` 싱글톤 로드 |
| `get_kis_credentials()` | KIS API 인증 정보 반환 (`.env` → `st.secrets` 폴백) |
| `get_telegram_credentials()` | 텔레그램 인증 정보 반환 |
| `load_env()` | `.env` 파일 로드 (Streamlit Cloud에서는 경고 생략) |
| `_get_env(key, default)` | `os.getenv()` → `st.secrets.get()` 순서로 환경변수 조회 |

**상수**: `ROOT_DIR`, `CONFIG_DIR`, `DATA_DIR`, `LOGS_DIR`

**환경변수 조회 순서** (`_get_env()`, `config.py:87-106`):
1. `os.getenv(key)` — 로컬 `.env` / OS 환경변수
2. `st.secrets.get(key)` — Streamlit Cloud Secrets (폴백)
3. TOML 파싱 대응: `str(value).strip()` 적용 (int/float → str 변환)

**의존**: `pyyaml`, `python-dotenv`, `streamlit` (선택적, 런타임)

---

### broker.py — KIS Open API 래퍼

**클래스**: `KISBroker`

- OAuth2 토큰 자동 발급/갱신
- Rate limiting (초당 요청 수 제한)
- 모의투자/실거래 자동 전환 (`live_trading` 설정)

**토큰 캐싱**:
- 파일: `data/kis_token_{live|paper}.json`
- KIS API의 1분당 1회 토큰 발급 제한을 회피
- 앱키 해시로 유효성 검증 (앱키 변경 시 자동 재발급)
- `_get_access_token()` → JSON 파일 캐시 확인 → 만료 시 API 재발급

**공개 메서드**:

| 메서드 | 시장 | 기능 | tr_id (실거래) | tr_id (모의) |
|--------|------|------|----------------|--------------|
| `get_kr_price(code)` | KR | 현재가 조회 | FHKST01010100 | 동일 |
| `get_kr_daily_prices(code)` | KR | 일봉 데이터 | FHKST01010400 | 동일 |
| `order_kr_buy(code, qty)` | KR | 매수 주문 | TTTC0802U | VTTC0802U |
| `order_kr_sell(code, qty)` | KR | 매도 주문 | TTTC0801U | VTTC0801U |
| `get_us_price(ticker)` | US | 현재가 조회 | HHDFS00000300 | 동일 |
| `get_us_daily_prices(ticker)` | US | 일봉 데이터 | HHDFS76240000 | 동일 |
| `order_us_buy(ticker, qty)` | US | 매수 주문 | JTTT1002U | VTTT1002U |
| `order_us_sell(ticker, qty)` | US | 매도 주문 | JTTT1006U | VTTT1006U |
| `get_kr_balance()` | KR | 국내 잔고 | TTTC8434R | VTTC8434R |
| `get_us_balance()` | US | 해외 잔고 | JTTT3012R | VTTS3012R |

**CANO 정규화** (Streamlit Cloud TOML 대응):
- 계좌번호: 하이픈 제거 → 앞 8자리 추출 (`raw_acno.replace("-", "")[:8]`)
- 상품코드: `.zfill(2)` 로 2자리 보장 (`"1"` → `"01"`)

**에러 로깅 강화**: `_get()` 에러 시 `rt_cd`, `msg_cd`, `msg1`, 전송된 `CANO`/`ACNT_PRDT_CD`/`tr_id` 출력

**의존**: `config.py` → `requests`, `loguru`

**수정 시 주의**: 새 API 추가 시 반드시 `_get()`/`_post()` 경유 (rate limiting 보장), `docs/DATA_DICTIONARY.md` 업데이트 필수

---

### data_manager.py — 데이터 수집 + SQLite

**클래스**: `DataManager`

- KISBroker를 통해 시세 수집
- KIS API 응답을 정규화된 DataFrame으로 변환
- SQLite에 OHLCV 데이터 저장/조회
- 매매 기록 저장

**공개 메서드**:

| 메서드 | 기능 |
|--------|------|
| `fetch_kr_daily(code)` | KR 일봉 → DataFrame |
| `fetch_us_daily(ticker)` | US 일봉 → DataFrame |
| `save_daily_prices(df)` | DataFrame → SQLite (중복 무시) |
| `load_daily_prices(code, market)` | SQLite → DataFrame |
| `save_trade(...)` | 매매 기록 DB 저장 |

**의존**: `config.py`, `broker.py` → `sqlalchemy`, `pandas`

---

### risk_manager.py — 리스크 관리

**클래스**: `RiskManager`, `Position`, `RiskState`

**리스크 체크 항목** (`can_open_position()`):
1. Kill Switch 활성화 여부
2. 일일 손실 한도 (`daily_loss_limit_pct`)
3. 최대 드로다운 (`max_drawdown_pct`)
4. 최대 포지션 수 (`max_positions`)
5. 개별 종목 비중 (`max_position_pct`)
6. 최소 현금 비중 (`min_cash_pct`)

**Kill Switch 영속화**:
- 파일: `data/kill_switch.json`
- Kill Switch 활성화 시 JSON 파일에 상태 저장
- 프로세스 재시작 후에도 Kill Switch 상태 유지
- 대시보드 봇 제어 (`p4_control.py`)에서 토글 가능

**의존**: `config.py` → `loguru`

**수정 시 주의**: 리스크 체크 순서가 중요 — Kill Switch를 항상 첫 번째로 유지

---

### data_feed.py — yfinance 데이터 피드

정의: `src/core/data_feed.py:29-104`

**클래스**: `DataFeed`

KIS API는 ~1년치만 제공하므로, yfinance를 통해 10년+ 장기 데이터를 확보합니다.
선택 의존성 — `yfinance` 미설치 시 graceful degradation.

| 메서드 | 역할 |
|--------|------|
| `fetch(symbol, start, end, market)` | 단일 종목 OHLCV 일봉 → DataFrame |
| `fetch_multiple(symbols, start, end)` | 복수 종목 일괄 수집 → `{code: DataFrame}` |

**KR 종목 yfinance 심볼 매핑**:
- 코스피: `{code}.KS` (예: `005930.KS` = 삼성전자)
- 코스닥: `{code}.KQ`
- US 종목: 그대로 사용 (예: `MSFT`, `SPY`)

**사용처**:
- `src/backtest/runner.py`: 백테스트 데이터 폴백
- `src/execution/collector.py`: 수집 시 KIS API 실패 폴백

**의존**: `yfinance` (선택), `pandas`, `loguru`

---

### exchange.py — 미국 종목 거래소 매핑

정의: `src/core/exchange.py`

미국 종목의 거래소 코드를 `settings.yaml` 전략 설정에서 조회합니다.
하드코딩된 거래소 목록(`nasdaq_tickers` 집합)을 대체합니다.

| 함수 | 역할 |
|------|------|
| `get_us_exchange(ticker, purpose)` | 미국 종목 거래소 코드 반환 |

**purpose 파라미터**:
- `"query"` → 조회용 코드: `NAS`, `NYS`, `AMS`
- `"order"` → 주문용 코드: `NASD`, `NYSE`, `AMEX`

**조회 우선순위** (`_lookup_from_config()`):
1. StatArb `pairs[]` → `exchange_a`, `exchange_b`, `exchange_hedge`
2. DualMomentum → `us_etf_exchange`, `safe_us_etf_exchange`
3. QuantFactor `universe_codes[]` → `exchange`
4. 폴백: `"NYS"` (경고 로그 출력)

**코드 변환 맵** (`_QUERY_TO_ORDER`): `NAS→NASD`, `NYS→NYSE`, `AMS→AMEX`

**사용처**: `collector.py` (데이터 수집), `executor.py` (주문 실행)

**의존**: `config.py` → `loguru`

---

## 의존 관계

```
config.py ← broker.py ← data_manager.py
config.py ← risk_manager.py
config.py ← exchange.py
yfinance  ← data_feed.py
```

> `risk_manager.py`는 `broker.py`에 의존하지 않습니다.
> 가격 업데이트는 외부에서 `update_prices()`로 주입합니다.

> `data_feed.py`는 `broker.py`에 의존하지 않습니다.
> KIS API 독립적으로 yfinance에서 데이터를 수집합니다.
