# src/execution — 실행 엔진

이 패키지는 **데이터 수집**과 **주문 실행**을 담당합니다.
전략(`strategies`)과 인프라(`core`)를 연결하는 중간 계층입니다.

---

## 모듈 목록

### collector.py — 데이터 수집 오케스트레이터

**클래스**: `DataCollector`

| 메서드 | 역할 |
|--------|------|
| `collect_all()` | 모든 활성 전략의 `required_codes()`를 합산하여 일괄 수집 |

**데이터 수집 흐름**:
```
활성 전략들의 required_codes() 합산 → 중복 제거
        |
        v
종목별 KIS API 수집 시도
        |
    성공 → DataManager.save_daily_prices() → SQLite
    실패 → yfinance fallback (DataFeed.fetch()) → SQLite
```

**핵심 동작**:
- 전략별 `required_codes()`가 필요 종목을 자동 제공
- KIS API 수집 실패 시 yfinance fallback (DataFeed, 선택적)
- 새 전략 추가 시 collector 수정 불필요 — `required_codes()`만 구현하면 자동 수집
- US 종목 거래소 매핑: `src/core/exchange.py`의 `get_us_exchange()` 사용 (설정 기반, 하드코딩 제거됨)

**의존**: `KISBroker` (API 호출), `DataManager` (DB 저장), `DataFeed` (yfinance fallback, 선택적), `exchange.py` (US 거래소)

---

### executor.py — 주문 실행 엔진

**클래스**: `OrderExecutor`

| 메서드 | 역할 |
|--------|------|
| `execute_signals(signals)` | TradeSignal 리스트를 순차 실행 |
| `get_current_price(code, market)` | 현재가 조회 (KR/US) |

**실행 흐름**:
```
TradeSignal → 가격 결정 → 수량 결정 → 리스크 검증 → 주문 → 포지션 등록 → 기록 → 알림
```

**거래소 매핑**: `get_us_exchange(code, "query")` / `get_us_exchange(code, "order")` — `exchange.py` 사용 (하드코딩 제거됨)

**의존**: `KISBroker`, `RiskManager`, `DataManager`, `TelegramNotifier`, `exchange.py`

---

## 의존 관계

```
main.py → DataCollector → {KISBroker, DataManager, DataFeed(선택적), exchange.py}
main.py → OrderExecutor → {KISBroker, RiskManager, DataManager, TelegramNotifier, exchange.py}
```

> `execution` 계층은 `strategies`에 의존하지 않습니다.
> 전략의 출력물인 `TradeSignal`만 받아 처리합니다.
> 전략이 제공하는 `required_codes()`를 통해 수집 대상을 결정합니다.
