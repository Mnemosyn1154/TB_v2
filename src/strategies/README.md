# src/strategies — 매매 전략 모듈

이 패키지는 시장 데이터를 분석하여 매매 신호(`TradeSignal`)를 생성하는 전략들을 포함합니다.

---

## 핵심 원칙

> **전략은 순수 분석 함수입니다.**
> - 가격 데이터를 입력받아 `TradeSignal` 리스트를 출력
> - broker, data_manager에 직접 접근 금지
> - 주문 실행이나 I/O 수행 금지

---

## STRATEGY_REGISTRY (플러그인 등록)

`src/strategies/__init__.py`의 `STRATEGY_REGISTRY`에 전략을 등록하면
`main.py`, `collector.py`, `BacktestRunner`가 자동으로 인식합니다.

```python
STRATEGY_REGISTRY: dict[str, type[BaseStrategy]] = {
    "stat_arb": StatArbStrategy,
    "dual_momentum": DualMomentumStrategy,
    "quant_factor": QuantFactorStrategy,
    "sector_rotation": SectorRotationStrategy,
    "volatility_breakout": VolatilityBreakoutStrategy,
    "bollinger_band": BollingerBandStrategy,
}
```

> 새 전략 추가 시 `main.py`, `collector.py`, `engine.py` 수정 불필요.
> STRATEGY_REGISTRY에 1줄 + `settings.yaml` 설정만 추가하면 됩니다.

---

## BaseStrategy 인터페이스

정의: `src/strategies/base.py:44-159`

```python
class BaseStrategy(ABC):
    name: str               # 전략 고유 이름
    enabled: bool           # 활성화 상태

    # ── 필수 abstract 메서드 (5개) ──

    @abstractmethod
    def get_config_key(self) -> str:
        """settings.yaml의 strategies: 하위 키 이름 (예: 'stat_arb')"""

    @abstractmethod
    def required_codes(self) -> list[dict[str, str]]:
        """수집/로드할 종목 목록 [{"code": "005930", "market": "KR"}, ...]"""

    @abstractmethod
    def prepare_signal_kwargs(self, price_data: dict[str, pd.Series]) -> dict:
        """원시 가격 데이터 → generate_signals() kwargs 변환. 빈 dict 반환 시 스킵."""

    @abstractmethod
    def generate_signals(self, **kwargs) -> list[TradeSignal]:
        """매매 신호 생성 (핵심 로직)"""

    @abstractmethod
    def get_status(self) -> dict[str, Any]:
        """현재 전략 상태 반환 (직렬화 가능한 dict)"""

    # ── 선택적 오버라이드 (4개) ──

    def should_skip_date(self, date: str, equity_history: list[dict]) -> bool:
        """백테스트 날짜 스킵 여부 (월별 리밸런싱 등). 기본: False"""

    def get_pair_names(self) -> list[str]:
        """페어 기반 전략의 페어 이름 목록. 기본: []"""

    def filter_pairs(self, pair_names: list[str]) -> None:
        """특정 페어만 사용하도록 필터링. 기본: 동작 없음"""

    def on_trade_executed(self, signal: TradeSignal, success: bool) -> None:
        """체결 콜백 — 내부 상태 동기화. 기본: 동작 없음"""
```

---

## TradeSignal 규격

```python
@dataclass
class TradeSignal:
    strategy: str     # 전략 이름 (예: "StatArb")
    code: str         # 종목코드 (예: "MSFT", "005930")
    market: str       # "KR" 또는 "US"
    signal: Signal    # BUY / SELL / HOLD / CLOSE
    quantity: int     # 0이면 RiskManager가 계산
    price: float      # 0이면 현재가 사용
    reason: str       # 로깅/알림에 표시되는 사유
    metadata: dict    # 전략별 추가 정보 (z_score, beta 등)
```

---

## 구현된 전략

### stat_arb.py — 통계적 차익거래

**알고리즘**:
1. Engle-Granger 공적분 검정 (`p < 0.05`)
2. OLS 회귀로 헤지 비율 beta 계산
3. 스프레드 = A - beta * B
4. 롤링 Z-Score 계산
5. Z > entry → B 롱 + 인버스 ETF, Z < -entry → A 롱 + 인버스 ETF
6. |Z| < exit → 청산, |Z| > stop → 손절

**페어**: `settings.yaml` → `strategies.stat_arb.pairs[]`

| 파라미터 | 설정키 | 기본값 | 설명 |
|----------|--------|--------|------|
| 룩백 윈도우 | `lookback_window` | 60 | 롤링 통계 일수 |
| 진입 Z | `entry_z_score` | 2.0 | 포지션 진입 기준 |
| 청산 Z | `exit_z_score` | 0.5 | 평균회귀 청산 기준 |
| 손절 Z | `stop_loss_z_score` | 3.5 | 손절 기준 |
| beta 재계산 | `recalc_beta_days` | 30 | beta 재산출 주기 |
| 공적분 p-value | `coint_pvalue` | 0.05 | Engle-Granger 유의수준 |

**핵심 클래스**: `PairConfig` (페어 설정 + `exchange_a/b/hedge` 필드), `PairState` (페어 상태), `StatArbStrategy`

**입력 형식**: `generate_signals(pair_data={"MSFT_GOOGL": {"prices_a": Series, "prices_b": Series}})`

---

### dual_momentum.py — 듀얼 모멘텀

**알고리즘**:
1. KR ETF vs US ETF 12개월 수익률 비교 (상대 모멘텀)
2. 승자 수익률 > 무위험수익률? (절대 모멘텀)
3. YES → 승자 ETF 매수, NO → 안전자산(채권 ETF) 매수

**배분 결과**: `"KR"` / `"US"` / `"SAFE"`

| 파라미터 | 설정키 | 기본값 |
|----------|--------|--------|
| 룩백 | `lookback_months` | 12 |
| 리밸런싱 | `rebalance_day` | 1 (매월 첫 거래일) |
| 무위험수익률 | `risk_free_rate` | 0.04 (연 4%) |
| US ETF 거래소 | `us_etf_exchange` | "NYS" |
| Safe US ETF 거래소 | `safe_us_etf_exchange` | "NYS" |

**입력 형식**: `generate_signals(kr_prices=Series, us_prices=Series)`

---

### quant_factor.py — 퀀트 팩터 (멀티팩터 스코어링)

**상태**: `enabled: false` (Phase 3에서 활성화 예정)

**알고리즘**:
1. 유니버스 전 종목 일봉 데이터 수집
2. 팩터 계산: Value(30%) + Quality(30%) + Momentum(40%)
3. Z-Score 정규화 → 가중 복합 스코어 산출
4. 상위 `top_n` 종목 매수, 보유 중 탈락 종목 청산
5. `rebalance_months` 주기로 리밸런싱

**팩터 정의**:

| 팩터 | 가중치 | 계산 | 의미 |
|------|--------|------|------|
| Value | 30% | `1 - (현재가 / 12개월 고점)` | 저평가 종목 선호 |
| Quality | 30% | `1 / 일별수익률_표준편차` | 안정적 종목 선호 |
| Momentum | 40% | `(현재가 / N개월전) - 1` | 상승 추세 선호 |

| 파라미터 | 설정키 | 기본값 | 설명 |
|----------|--------|--------|------|
| 상위 종목 수 | `top_n` | 20 | 보유 종목 수 |
| 리밸런싱 | `rebalance_months` | 1 | 주기 (월) |
| Value 룩백 | `lookback_days` | 252 | 거래일 |
| Momentum 룩백 | `momentum_days` | 126 | ~6개월 |
| 변동성 윈도우 | `volatility_days` | 60 | Quality 계산 |
| 최소 데이터 | `min_data_days` | 60 | 스코어링 제외 기준 |

**유니버스**: KOSPI200 상위 25종목 + S&P500 상위 15종목 (`settings.yaml` → `quant_factor.universe_codes`)

> US 유니버스 종목은 `exchange` 필드 필수: `{ code: "AAPL", market: "US", exchange: "NAS" }`

**입력 형식**: `generate_signals(price_data={"005930": Series, "MSFT": Series, ...})`

---

### volatility_breakout.py — 변동성 돌파 (래리 윌리엄스)

**상태**: `enabled: false`

**알고리즘**:
1. 전일 OHLC 추출 → 목표가 = 오늘 시가 + 전일 (고가 - 저가) × k
2. 장중 현재가가 목표가 이상이면 매수 (종목당 1회)
3. 장 마감 직전 전량 청산 (일중 전략)
4. 백테스트: 당일 고가 ≥ 목표가이면 목표가에 매수 근사, 익일 종가 청산

**특이사항**:
- `needs_ohlc = True` — OHLC DataFrame을 수신 (다른 전략은 종가 Series만 사용)
- 백테스트 엔진에서 bisect 기반 OHLC 날짜 캐시로 look-ahead bias 방지
- `on_trade_executed()` 콜백으로 `current_holdings`/`today_entered` 상태 동기화

| 파라미터 | 설정키 | 기본값 | 설명 |
|----------|--------|--------|------|
| k 값 | `k` | 0.5 | 변동성 돌파 계수 |
| 시장 | `market` | "KR" | 기본 시장 |
| 종목당 최대 보유 | `max_hold_per_stock` | 1 | 동일 종목 중복 진입 방지 |
| 장마감 청산 | `close_at_market_end` | true | 장 종료 시 전량 청산 |
| KR 청산 시각 | `kr_close_time` | "15:15" | 한국 시장 청산 시각 |
| US 청산 시각 | `us_close_time` | "15:45" | 미국 시장 청산 시각 |

**유니버스**: KR 블루칩 5종목 — 삼성전자, SK하이닉스, 현대차, NAVER, 셀트리온

**입력 형식**: `generate_signals(ohlc_data={"005930": DataFrame}, current_prices={"005930": 54000})`

---

### bollinger_band.py — 볼린저 밴드 평균회귀

**상태**: `enabled: true`

**알고리즘**:
1. SMA(N) 계산 (N일 이동평균)
2. 상단 밴드 = SMA + K × σ(N), 하단 밴드 = SMA - K × σ(N)
3. 종가 < 하단 밴드 → BUY (과매도 → 반등 기대)
4. 종가 > 상단 밴드 → CLOSE (과매수 → 차익 실현)
5. %B, Bandwidth를 metadata에 포함

**특이사항**:
- `on_trade_executed()` 콜백으로 `current_holdings` 상태 동기화
- 종목당 최대 보유 1개 (`max_hold_per_stock`)

| 파라미터 | 설정키 | 기본값 | 설명 |
|----------|--------|--------|------|
| SMA 기간 | `window` | 20 | 이동평균 윈도우 |
| 표준편차 배수 | `num_std` | 2.0 | 밴드 폭 계수 |
| 시장 | `market` | "KR" | 기본 시장 |
| 종목당 최대 보유 | `max_hold_per_stock` | 1 | 동일 종목 중복 진입 방지 |

**유니버스**: KR 블루칩 3종목 — 삼성전자, SK하이닉스, NAVER

**입력 형식**: `generate_signals(price_data={"005930": Series, "000660": Series, ...})`

---

## 새 전략 추가 절차

상세 가이드: [`docs/STRATEGY_GUIDE.md`](../../docs/STRATEGY_GUIDE.md)

### 요약 (3단계)

1. `src/strategies/새전략.py` — `BaseStrategy` 상속 (5개 필수 메서드 구현)
2. `src/strategies/__init__.py` — `STRATEGY_REGISTRY`에 1줄 추가
3. `config/settings.yaml` — 전략 설정 추가 (`enabled: true`)
