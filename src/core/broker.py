from __future__ import annotations

"""
AlgoTrader KR — KIS Open API 브로커 연동

한국투자증권 KIS Open API와 통신하는 래퍼 클래스.
인증(OAuth2), Rate Limiting, 국내/해외 시세 조회 및 주문을 처리합니다.

API 문서: https://apiportal.koreainvestment.com/apiservice

Depends on:
    - src.core.config (API 키, URL 설정)
    - requests (HTTP 통신)

Used by:
    - src.core.data_manager (시세 데이터 수집)
    - src.execution.executor (주문 실행)
    - src.execution.collector (데이터 수집 오케스트레이션)

Modification Guide:
    - 새 API 추가: _get()/_post() 경유, tr_id는 실거래/모의 분기 필수
    - 응답 처리: API 원본 필드를 정규화된 dict로 변환하여 반환
    - 필드 매핑: docs/DATA_DICTIONARY.md에 반드시 문서화
"""
import os
import time
import json
import hashlib
from datetime import datetime, timedelta
from typing import Any

import requests
from loguru import logger

from src.core.config import get_config, get_kis_credentials


class KISBroker:
    """한국투자증권 KIS Open API 래퍼"""

    def __init__(self):
        config = get_config()
        creds = get_kis_credentials()

        self.app_key = creds["app_key"]
        self.app_secret = creds["app_secret"]
        # 계좌번호: 하이픈 제거 후 앞 8자리만 사용 (CANO 형식)
        raw_acno = creds["account_no"].replace("-", "")
        self.account_no = raw_acno[:8] if len(raw_acno) >= 8 else raw_acno
        # ACNT_PRDT_CD는 반드시 2자리 (TOML에서 int 1로 파싱될 수 있음 → "01"로 보정)
        raw_product = creds["account_product"]
        self.account_product = raw_product.zfill(2)

        if not self.account_no or len(self.account_no) != 8 or not self.account_no.isdigit():
            logger.warning(f"KIS 계좌번호 형식 확인 필요: '{creds['account_no']}' → CANO은 8자리 숫자여야 합니다")

        kis_config = config["kis"]
        self.live_trading = kis_config["live_trading"]
        self.base_url = kis_config["base_url"] if self.live_trading else kis_config["paper_url"]
        self.rate_limit = kis_config["rate_limit"]

        # 인증 토큰
        self._access_token: str | None = None
        self._token_expires: datetime | None = None

        # Rate limiting
        self._last_request_time: float = 0
        self._request_interval: float = 1.0 / self.rate_limit

        mode = "실거래" if self.live_trading else "모의투자"
        logger.info(f"KIS Broker 초기화 [{mode}] → {self.base_url}")
        logger.info(f"KIS 계좌: CANO='{self.account_no}' (len={len(self.account_no)}), ACNT_PRDT_CD='{self.account_product}'")

    # ──────────────────────────────────────────────
    # 인증
    # ──────────────────────────────────────────────

    def _get_access_token(self) -> str:
        """OAuth2 Access Token 발급/갱신 (파일 캐싱으로 1분 제한 회피)"""
        if self._access_token and self._token_expires and datetime.now() < self._token_expires:
            return self._access_token

        # 파일 캐시에서 토큰 복원 시도 (KIS는 토큰 발급 1분당 1회 제한)
        token_data = self._load_cached_token()
        if token_data:
            self._access_token = token_data["access_token"]
            self._token_expires = datetime.fromisoformat(token_data["expires_at"])
            if datetime.now() < self._token_expires:
                logger.debug("캐시된 KIS Access Token 사용")
                return self._access_token

        url = f"{self.base_url}/oauth2/tokenP"
        body = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
        }

        resp = requests.post(url, json=body, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        self._access_token = data["access_token"]
        # 토큰 만료 시간 (보통 24시간, 안전 마진 1시간)
        self._token_expires = datetime.now() + timedelta(hours=23)

        # 파일 캐시에 저장
        self._save_cached_token(self._access_token, self._token_expires)

        logger.info("KIS Access Token 발급 완료")
        return self._access_token

    def _get_token_cache_path(self) -> str:
        """토큰 캐시 파일 경로 (모의투자/실거래 구분)"""
        from src.core.config import DATA_DIR
        mode = "live" if self.live_trading else "paper"
        return str(DATA_DIR / f"kis_token_{mode}.json")

    def _load_cached_token(self) -> dict | None:
        """파일에서 캐시된 토큰 로드"""
        cache_path = self._get_token_cache_path()
        try:
            with open(cache_path, "r") as f:
                data = json.load(f)
            # 앱키가 동일한 경우에만 캐시 사용
            if data.get("app_key_hash") == hashlib.sha256(self.app_key.encode()).hexdigest():
                return data
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            pass
        return None

    def _save_cached_token(self, token: str, expires: datetime) -> None:
        """토큰을 파일에 캐시"""
        from src.core.config import DATA_DIR
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        cache_path = self._get_token_cache_path()
        data = {
            "access_token": token,
            "expires_at": expires.isoformat(),
            "app_key_hash": hashlib.sha256(self.app_key.encode()).hexdigest(),
        }
        try:
            with open(cache_path, "w") as f:
                json.dump(data, f)
        except Exception as e:
            logger.warning(f"토큰 캐시 저장 실패: {e}")

    def _force_refresh_token(self) -> str:
        """토큰 강제 갱신 (메모리 + 파일 캐시 무효화 후 재발급)"""
        self._access_token = None
        self._token_expires = None
        cache_path = self._get_token_cache_path()
        try:
            os.remove(cache_path)
        except FileNotFoundError:
            pass
        logger.info("KIS Access Token 강제 갱신 시도")
        return self._get_access_token()

    def _get_hashkey(self, body: dict) -> str:
        """주문 시 hashkey 생성"""
        url = f"{self.base_url}/uapi/hashkey"
        headers = {
            "Content-Type": "application/json",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
        }
        resp = requests.post(url, headers=headers, json=body, timeout=10)
        resp.raise_for_status()
        return resp.json()["HASH"]

    def _headers(self, tr_id: str, hashkey: str | None = None) -> dict[str, str]:
        """API 요청 공통 헤더"""
        token = self._get_access_token()
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id,
        }
        if hashkey:
            headers["hashkey"] = hashkey
        return headers

    def _rate_limit_wait(self) -> None:
        """초당 요청 수 제한"""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self._request_interval:
            time.sleep(self._request_interval - elapsed)
        self._last_request_time = time.time()

    # ──────────────────────────────────────────────
    # REST API 공통 메서드
    # ──────────────────────────────────────────────

    # 토큰 갱신 후 재시도할 KIS API 오류 키워드
    _RETRYABLE_KEYWORDS = ("INVALID_CHECK_ACNO", "INVALID TOKEN", "TOKEN ERROR")

    def _get(self, path: str, tr_id: str, params: dict | None = None) -> dict:
        """GET 요청 (간헐적 인증/계좌 오류 시 토큰 갱신 후 1회 재시도)"""
        data = self._do_get(path, tr_id, params)

        if data.get("rt_cd") != "0":
            msg1 = data.get("msg1", "")
            # 간헐적 계좌/토큰 오류 → 토큰 강제 갱신 후 1회 재시도
            if any(kw in msg1 for kw in self._RETRYABLE_KEYWORDS):
                logger.warning(
                    f"KIS API 간헐적 오류 감지 → 토큰 갱신 후 재시도: {msg1} "
                    f"[tr_id={tr_id}]"
                )
                time.sleep(0.5)
                self._force_refresh_token()
                data = self._do_get(path, tr_id, params)

        if data.get("rt_cd") != "0":
            sent_cano = params.get("CANO", "N/A") if params else "N/A"
            sent_prdt = params.get("ACNT_PRDT_CD", "N/A") if params else "N/A"
            logger.error(
                f"KIS API 오류: {data.get('msg1', 'Unknown error')} "
                f"[tr_id={tr_id}, CANO={sent_cano}, ACNT_PRDT_CD={sent_prdt}]"
            )
            logger.error(f"KIS API 응답 전문: rt_cd={data.get('rt_cd')}, msg_cd={data.get('msg_cd')}, msg1={data.get('msg1')}")
            logger.error(f"KIS API 요청 URL: {self.base_url}{path}, params keys: {list(params.keys()) if params else []}")
            raise RuntimeError(f"KIS API Error: {data.get('msg1')}")

        return data

    def _do_get(self, path: str, tr_id: str, params: dict | None = None) -> dict:
        """실제 GET HTTP 요청 수행"""
        self._rate_limit_wait()
        url = f"{self.base_url}{path}"
        headers = self._headers(tr_id)

        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, tr_id: str, body: dict) -> dict:
        """POST 요청"""
        self._rate_limit_wait()
        url = f"{self.base_url}{path}"
        hashkey = self._get_hashkey(body)
        headers = self._headers(tr_id, hashkey=hashkey)

        resp = requests.post(url, headers=headers, json=body, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if data.get("rt_cd") != "0":
            logger.error(f"KIS API 오류: {data.get('msg1', 'Unknown error')}")
            raise RuntimeError(f"KIS API Error: {data.get('msg1')}")

        return data

    # ──────────────────────────────────────────────
    # 연결 검증
    # ──────────────────────────────────────────────

    def verify_connection(self) -> dict[str, Any]:
        """KIS API 연결 상태 검증 (read-only, 삼성전자 시세 조회)

        Returns:
            connected: bool
            mode: "live" | "paper"
            account: str (마스킹된 계좌번호)
            error: str | None
        """
        mode = "live" if self.live_trading else "paper"
        masked = self.account_no[:4] + "****" if len(self.account_no) >= 4 else self.account_no

        if not self.app_key or not self.app_secret:
            return {"connected": False, "mode": mode, "account": masked,
                    "error": "KIS API 키가 설정되지 않았습니다"}
        if not self.account_no:
            return {"connected": False, "mode": mode, "account": masked,
                    "error": "KIS 계좌번호가 설정되지 않았습니다"}
        try:
            self.get_kr_price("005930")  # 삼성전자 시세 조회
            return {"connected": True, "mode": mode, "account": masked, "error": None}
        except Exception as e:
            err = str(e)
            if "403" in err or "Forbidden" in err:
                err = "인증 실패 (403) — API 키/시크릿이 유효하지 않습니다"
            elif "401" in err or "Unauthorized" in err:
                err = "토큰 만료 (401) — data/kis_token_*.json 삭제 후 재시도하세요"
            return {"connected": False, "mode": mode, "account": masked, "error": err}

    # ──────────────────────────────────────────────
    # 국내 주식
    # ──────────────────────────────────────────────

    def get_kr_price(self, stock_code: str) -> dict[str, Any]:
        """국내 주식 현재가 조회"""
        tr_id = "FHKST01010100"
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": stock_code,
        }
        data = self._get("/uapi/domestic-stock/v1/quotations/inquire-price", tr_id, params)
        output = data.get("output", {})
        return {
            "code": stock_code,
            "name": output.get("stck_prpr", ""),
            "price": int(output.get("stck_prpr", 0)),
            "change": int(output.get("prdy_vrss", 0)),
            "change_pct": float(output.get("prdy_ctrt", 0)),
            "volume": int(output.get("acml_vol", 0)),
            "market": "KR",
        }

    def get_kr_daily_prices(self, stock_code: str, period: str = "D",
                            start_date: str = "", end_date: str = "") -> list[dict]:
        """국내 주식 일봉 데이터 조회"""
        tr_id = "FHKST01010400"
        if not end_date:
            end_date = datetime.now().strftime("%Y%m%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")

        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": stock_code,
            "FID_INPUT_DATE_1": start_date,
            "FID_INPUT_DATE_2": end_date,
            "FID_PERIOD_DIV_CODE": period,
            "FID_ORG_ADJ_PRC": "0",
        }
        data = self._get("/uapi/domestic-stock/v1/quotations/inquire-daily-price", tr_id, params)
        return data.get("output", [])

    def order_kr_buy(self, stock_code: str, quantity: int, price: int = 0) -> dict:
        """국내 주식 매수 주문 (price=0이면 시장가)"""
        tr_id = "TTTC0802U" if self.live_trading else "VTTC0802U"
        order_type = "01" if price > 0 else "06"  # 지정가 / 시장가
        body = {
            "CANO": self.account_no,
            "ACNT_PRDT_CD": self.account_product,
            "PDNO": stock_code,
            "ORD_DVSN": order_type,
            "ORD_QTY": str(quantity),
            "ORD_UNPR": str(price),
        }
        logger.info(f"📈 KR 매수 주문: {stock_code} x {quantity} @ {'시장가' if price == 0 else price}")
        return self._post("/uapi/domestic-stock/v1/trading/order-cash", tr_id, body)

    def order_kr_sell(self, stock_code: str, quantity: int, price: int = 0) -> dict:
        """국내 주식 매도 주문"""
        tr_id = "TTTC0801U" if self.live_trading else "VTTC0801U"
        order_type = "01" if price > 0 else "06"
        body = {
            "CANO": self.account_no,
            "ACNT_PRDT_CD": self.account_product,
            "PDNO": stock_code,
            "ORD_DVSN": order_type,
            "ORD_QTY": str(quantity),
            "ORD_UNPR": str(price),
        }
        logger.info(f"📉 KR 매도 주문: {stock_code} x {quantity} @ {'시장가' if price == 0 else price}")
        return self._post("/uapi/domestic-stock/v1/trading/order-cash", tr_id, body)

    # ──────────────────────────────────────────────
    # 해외 (미국) 주식
    # ──────────────────────────────────────────────

    def get_us_price(self, ticker: str, exchange: str = "NAS") -> dict[str, Any]:
        """미국 주식 현재가 조회
        exchange: NAS(나스닥), NYS(뉴욕), AMS(아멕스)
        """
        tr_id = "HHDFS00000300"
        params = {
            "AUTH": "",
            "EXCD": exchange,
            "SYMB": ticker,
        }
        data = self._get("/uapi/overseas-price/v1/quotations/price", tr_id, params)
        output = data.get("output", {})
        return {
            "code": ticker,
            "price": float(output.get("last", 0)),
            "change": float(output.get("diff", 0)),
            "change_pct": float(output.get("rate", 0)),
            "volume": int(output.get("tvol", 0)),
            "market": "US",
            "exchange": exchange,
        }

    def get_us_daily_prices(self, ticker: str, exchange: str = "NAS",
                            period: str = "D", count: int = 120) -> list[dict]:
        """미국 주식 일봉 데이터 조회"""
        tr_id = "HHDFS76240000"
        params = {
            "AUTH": "",
            "EXCD": exchange,
            "SYMB": ticker,
            "GUBN": "0",  # 0: 일, 1: 주, 2: 월
            "BYMD": "",
            "MODP": "1",  # 수정주가 반영
        }
        data = self._get("/uapi/overseas-price/v1/quotations/dailyprice", tr_id, params)
        return data.get("output2", [])[:count]

    def order_us_buy(self, ticker: str, quantity: int, price: float = 0,
                     exchange: str = "NASD") -> dict:
        """미국 주식 매수 주문
        exchange: NASD(나스닥), NYSE(뉴욕), AMEX(아멕스)
        """
        tr_id = "JTTT1002U" if self.live_trading else "VTTT1002U"
        order_type = "00" if price > 0 else "31"  # 지정가 / 시장가(MOC)
        body = {
            "CANO": self.account_no,
            "ACNT_PRDT_CD": self.account_product,
            "OVRS_EXCG_CD": exchange,
            "PDNO": ticker,
            "ORD_QTY": str(quantity),
            "OVRS_ORD_UNPR": str(price),
            "ORD_SVR_DVSN_CD": "0",
            "ORD_DVSN": order_type,
        }
        logger.info(f"📈 US 매수 주문: {ticker} x {quantity} @ {'시장가' if price == 0 else price}")
        return self._post("/uapi/overseas-stock/v1/trading/order", tr_id, body)

    def order_us_sell(self, ticker: str, quantity: int, price: float = 0,
                      exchange: str = "NASD") -> dict:
        """미국 주식 매도 주문"""
        tr_id = "JTTT1006U" if self.live_trading else "VTTT1006U"
        order_type = "00" if price > 0 else "31"
        body = {
            "CANO": self.account_no,
            "ACNT_PRDT_CD": self.account_product,
            "OVRS_EXCG_CD": exchange,
            "PDNO": ticker,
            "ORD_QTY": str(quantity),
            "OVRS_ORD_UNPR": str(price),
            "ORD_SVR_DVSN_CD": "0",
            "ORD_DVSN": order_type,
        }
        logger.info(f"📉 US 매도 주문: {ticker} x {quantity} @ {'시장가' if price == 0 else price}")
        return self._post("/uapi/overseas-stock/v1/trading/order", tr_id, body)

    # ──────────────────────────────────────────────
    # 계좌 조회
    # ──────────────────────────────────────────────

    def get_kr_balance(self) -> dict:
        """국내 주식 잔고 조회"""
        tr_id = "TTTC8434R" if self.live_trading else "VTTC8434R"
        params = {
            "CANO": self.account_no,
            "ACNT_PRDT_CD": self.account_product,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "01",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        }
        data = self._get("/uapi/domestic-stock/v1/trading/inquire-balance", tr_id, params)
        positions = data.get("output1", [])
        summary = data.get("output2", [{}])[0] if data.get("output2") else {}

        return {
            "positions": [
                {
                    "code": p["pdno"],
                    "name": p["prdt_name"],
                    "quantity": int(p["hldg_qty"]),
                    "avg_price": float(p["pchs_avg_pric"]),
                    "current_price": int(p["prpr"]),
                    "profit_pct": float(p["evlu_pfls_rt"]),
                    "profit_amt": int(p["evlu_pfls_amt"]),
                    "market": "KR",
                }
                for p in positions
                if int(p.get("hldg_qty", 0)) > 0
            ],
            "total_equity": int(summary.get("scts_evlu_amt", 0)),
            "cash": int(summary.get("dnca_tot_amt", 0)),
            "total_value": int(summary.get("tot_evlu_amt", 0)),
        }

    def get_us_balance(self) -> dict:
        """해외 주식 잔고 조회"""
        tr_id = "JTTT3012R" if self.live_trading else "VTTS3012R"
        params = {
            "CANO": self.account_no,
            "ACNT_PRDT_CD": self.account_product,
            "OVRS_EXCG_CD": "NASD",
            "TR_CRCY_CD": "USD",
            "CTX_AREA_FK200": "",
            "CTX_AREA_NK200": "",
        }
        data = self._get("/uapi/overseas-stock/v1/trading/inquire-balance", tr_id, params)
        positions = data.get("output1", [])

        return {
            "positions": [
                {
                    "code": p.get("ovrs_pdno", ""),
                    "name": p.get("ovrs_item_name", ""),
                    "quantity": int(p.get("ovrs_cblc_qty", 0)),
                    "avg_price": float(p.get("pchs_avg_pric", 0)),
                    "current_price": float(p.get("now_pric2", 0)),
                    "profit_pct": float(p.get("evlu_pfls_rt", 0)),
                    "profit_amt": float(p.get("frcr_evlu_pfls_amt", 0)),
                    "market": "US",
                }
                for p in positions
                if int(p.get("ovrs_cblc_qty", 0)) > 0
            ],
        }
