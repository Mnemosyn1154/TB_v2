"""
AlgoTrader KR — 데이터 피드 (yfinance)

백테스트 및 장기 히스토리 데이터 수집용.
KIS API는 ~1년치만 제공하므로, yfinance를 통해 10년+ 데이터를 확보합니다.

KR 종목 매핑:
    - 코스피: {code}.KS (예: 005930.KS = 삼성전자)
    - 코스닥: {code}.KQ

Depends on:
    - yfinance (Yahoo Finance API)
    - pandas (DataFrame 처리)

Used by:
    - src.backtest.runner (백테스트 데이터 수집)
"""
import pandas as pd
from loguru import logger

try:
    import yfinance as yf
    YF_AVAILABLE = True
except ImportError:
    YF_AVAILABLE = False
    logger.warning("yfinance 미설치 — pip install yfinance")


class DataFeed:
    """백테스트 및 분석용 데이터 피드 (yfinance 기반)"""

    def __init__(self):
        if not YF_AVAILABLE:
            raise ImportError("yfinance가 필요합니다: pip install yfinance")

    @staticmethod
    def _to_yf_symbol(code: str, market: str, suffix: str = "") -> str:
        """종목 코드를 yfinance 심볼로 변환"""
        if market == "KR":
            return f"{code}{suffix or '.KS'}"
        return code  # US 종목은 그대로

    def _fetch_raw(self, yf_symbol: str, start: str, end: str) -> pd.DataFrame:
        """yfinance에서 원시 데이터 가져오기"""
        try:
            ticker = yf.Ticker(yf_symbol)
            return ticker.history(start=start, end=end, auto_adjust=True)
        except Exception as e:
            logger.error(f"yfinance 데이터 가져오기 실패: {yf_symbol} — {e}")
            return pd.DataFrame()

    def fetch(self, symbol: str, start: str, end: str,
              market: str = "US") -> pd.DataFrame:
        """
        yfinance에서 OHLCV 일봉 데이터를 가져옵니다.

        KR 종목은 KOSPI(.KS)를 먼저 시도하고, 데이터가 없으면
        KOSDAQ(.KQ)으로 재시도합니다.

        Args:
            symbol: 종목 코드 (KR: "005930", US: "SPY")
            start: 시작일 "YYYY-MM-DD"
            end: 종료일 "YYYY-MM-DD"
            market: "KR" or "US"

        Returns:
            DataFrame (date, open, high, low, close, volume, code, market)
        """
        yf_symbol = self._to_yf_symbol(symbol, market)
        raw = self._fetch_raw(yf_symbol, start, end)

        # KR 종목: KOSPI 데이터가 없으면 KOSDAQ으로 재시도
        if raw.empty and market == "KR":
            yf_symbol_kq = self._to_yf_symbol(symbol, market, suffix=".KQ")
            logger.info(f"KOSPI 데이터 없음, KOSDAQ 재시도: {yf_symbol_kq}")
            raw = self._fetch_raw(yf_symbol_kq, start, end)
            if not raw.empty:
                yf_symbol = yf_symbol_kq

        if raw.empty:
            logger.warning(f"yfinance 데이터 없음: {yf_symbol} ({start} ~ {end})")
            return pd.DataFrame()

        df = pd.DataFrame({
            "date": raw.index,
            "open": raw["Open"].values,
            "high": raw["High"].values,
            "low": raw["Low"].values,
            "close": raw["Close"].values,
            "volume": raw["Volume"].values.astype(int),
        })
        df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
        df["code"] = symbol
        df["market"] = market
        df = df.sort_values("date").reset_index(drop=True)

        logger.info(f"yfinance 데이터 수집: {yf_symbol} — {len(df)}건 ({start} ~ {end})")
        return df

    def fetch_multiple(self, symbols: dict[str, str], start: str,
                       end: str) -> dict[str, pd.DataFrame]:
        """
        여러 종목 데이터를 한번에 가져옵니다.

        Args:
            symbols: {종목코드: 시장} 예: {"005930": "KR", "MSFT": "US"}
            start: 시작일
            end: 종료일

        Returns:
            {종목코드: DataFrame}
        """
        result = {}
        for symbol, market in symbols.items():
            df = self.fetch(symbol, start, end, market)
            if not df.empty:
                result[symbol] = df
        return result
