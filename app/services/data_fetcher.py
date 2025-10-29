"""데이터 수집 및 가공 유틸리티."""

import copy
import functools
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests
import streamlit as st
from duckduckgo_search import DDGS
from pykrx import stock

try:
    from streamlit.runtime.scriptrunner import get_script_run_ctx
except Exception:  # pragma: no cover - streamlit runtime 모듈 미배포 환경 대비
    get_script_run_ctx = None

logger = logging.getLogger(__name__)

# pykrx 호출 실패 시 마지막 정상 데이터를 재사용하기 위한 임시 캐시
_LAST_SUCCESS_CACHE: Dict[str, Any] = {}
_LAST_ERRORS: Dict[str, str] = {}

# 대시보드에 표시할 주요 지수 코드
_ADDITIONAL_INDEX_TARGETS = {
    "KOSPI": "1001",
    "KOSDAQ": "2001",
    "KOSPI200": "1028",
}

# 주도 섹터 시황용 타깃
_SECTOR_CANDIDATES = [
    "KRX 반도체",
    "KRX 2차전지",
    "KRX 바이오",
    "KRX 자동차",
    "KRX 에너지화학",
]

# 글로벌 지표 및 환율 (야후 파이낸스 심볼)
_GLOBAL_SYMBOLS = {
    "S&P 500 Futures": "ES=F",
    "Nasdaq 100 Futures": "NQ=F",
    "WTI Crude Oil": "CL=F",
    "USD/KRW": "KRW=X",
}

_REQUEST_SESSION = requests.Session()
_REQUEST_SESSION.headers.update(
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
)

PERSISTENT_CACHE_DIR = Path(".cache")
PERSISTENT_CACHE_DIR.mkdir(exist_ok=True)
GLOBAL_SNAPSHOT_CACHE_FILE = PERSISTENT_CACHE_DIR / "global_snapshot.json"
GLOBAL_SNAPSHOT_CACHE_TTL = 60 * 15  # 15분


def _has_streamlit_runtime() -> bool:
    if get_script_run_ctx is None:
        return False
    try:
        return get_script_run_ctx() is not None
    except RuntimeError:
        return False


def cache_data_or_lru(*cache_args, **cache_kwargs):
    """
    Streamlit 런타임에서는 st.cache_data를, 그 외 환경(FastAPI 실행 등)에서는 lru_cache를 사용합니다.
    """

    def decorator(func):
        lru_cached = functools.lru_cache(maxsize=None)(func)
        streamlit_cached = {"fn": None}

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if _has_streamlit_runtime():
                if streamlit_cached["fn"] is None:
                    streamlit_cached["fn"] = st.cache_data(*cache_args, **cache_kwargs)(func)
                return streamlit_cached["fn"](*args, **kwargs)
            return lru_cached(*args, **kwargs)

        return wrapper

    return decorator


def _deep_copy(value: Any) -> Any:
    if isinstance(value, pd.DataFrame):
        return value.copy()
    if isinstance(value, (dict, list)):
        return copy.deepcopy(value)
    return value


def _remember_result(key: str, value: Any) -> Any:
    _LAST_SUCCESS_CACHE[key] = _deep_copy(value)
    return _deep_copy(value)


def _fallback_result(key: str, default: Any) -> Any:
    fallback = _LAST_SUCCESS_CACHE.get(key)
    if fallback is not None:
        return _deep_copy(fallback)
    return default


def _record_error(key: str, message: Optional[str]) -> None:
    if message:
        _LAST_ERRORS[key] = message
    else:
        _LAST_ERRORS.pop(key, None)


def get_last_data_error(key: str) -> Optional[str]:
    return _LAST_ERRORS.get(key)


def _build_global_snapshot_placeholder() -> List[Dict[str, Any]]:
    return [
        {
            "label": label,
            "price": None,
            "change": None,
            "change_pct": None,
            "source": "Yahoo Finance",
            "timestamp": None,
        }
        for label in _GLOBAL_SYMBOLS
    ]


def _request_with_retry(url: str, params: Dict[str, Any], retries: int = 3, backoff: float = 1.5) -> Dict[str, Any]:
    last_exc: Optional[Exception] = None
    for attempt in range(retries):
        try:
            response = _REQUEST_SESSION.get(url, params=params, timeout=8)
            if response.status_code == 429 and attempt < retries - 1:
                sleep_for = backoff**attempt
                logger.info(
                    "Yahoo Finance rate limited request; retrying",
                    extra={
                        "attempt": attempt + 1,
                        "retries": retries,
                        "sleep_for": sleep_for,
                    },
                )
                time.sleep(sleep_for)
                continue
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            last_exc = exc
            if attempt < retries - 1:
                sleep_for = backoff ** attempt
                time.sleep(sleep_for)
            else:
                raise
    raise last_exc  # pragma: no cover


def _load_persistent_snapshot() -> Optional[List[Dict[str, Any]]]:
    if not GLOBAL_SNAPSHOT_CACHE_FILE.exists():
        return None
    try:
        raw = json.loads(GLOBAL_SNAPSHOT_CACHE_FILE.read_text(encoding="utf-8"))
        timestamp = raw.get("timestamp")
        if timestamp and time.time() - float(timestamp) > GLOBAL_SNAPSHOT_CACHE_TTL:
            return None
        return raw.get("data")
    except Exception:
        return None


def _save_persistent_snapshot(data: List[Dict[str, Any]]) -> None:
    payload = {"timestamp": time.time(), "data": data}
    GLOBAL_SNAPSHOT_CACHE_FILE.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _get_index_frame(start_date: str, end_date: str, ticker: str, label: str) -> pd.DataFrame:
    frame = stock.get_index_ohlcv_by_date(start_date, end_date, ticker)
    return frame["종가"].to_frame(label)


def _find_index_ticker(target_name: str, date: str) -> Optional[str]:
    try:
        for market in ("KOSPI", "KOSDAQ", "KRX", "테마"):
            tickers = stock.get_index_ticker_list(date, market=market)
            for ticker in tickers:
                if stock.get_index_ticker_name(ticker) == target_name:
                    return ticker
    except Exception as exc:
        logger.warning(
            "Failed to resolve index ticker",
            extra={"target": target_name, "error": str(exc)},
        )
    return None


def _load_sector_snapshot(
    sector_name: str, start_date: str, end_date: str, reference_day: str
) -> Optional[Dict[str, Any]]:
    ticker = _find_index_ticker(sector_name, reference_day)
    if not ticker:
        return None
    sector_df = stock.get_index_ohlcv_by_date(start_date, end_date, ticker)
    if sector_df.empty:
        return None
    latest = sector_df.iloc[-1]["종가"]
    previous = sector_df.iloc[-2]["종가"] if len(sector_df) > 1 else latest
    diff = latest - previous
    change_pct = (diff / previous * 100) if previous else 0
    return {
        "섹터": sector_name,
        "현재가": latest,
        "전일대비": diff,
        "등락률(%)": change_pct,
    }


@cache_data_or_lru(ttl=900, show_spinner=False)
def get_market_indices() -> pd.DataFrame:
    """
    최근 한 달간의 주요 지수 종가를 반환합니다.
    """
    key = "market_indices"
    today = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
    try:
        frames = []
        for label, ticker in _ADDITIONAL_INDEX_TARGETS.items():
            try:
                frame = _get_index_frame(start_date, today, ticker, label)
                frames.append(frame)
            except Exception as inner_exc:
                logger.warning(
                    "Failed to load index component",
                    extra={"label": label, "ticker": ticker, "error": str(inner_exc)},
                )

        if not frames:
            raise RuntimeError("No index data available")

        indices_df = pd.concat(frames, axis=1)
        indices_df.index = indices_df.index.strftime("%Y-%m-%d")
        result = _remember_result(key, indices_df)
        _record_error(key, None)
        return result
    except Exception as exc:
        logger.warning("get_market_indices failed", exc_info=exc)
        _record_error(key, str(exc))
        return _fallback_result(key, pd.DataFrame())


def _load_top_100_market_cap_stocks() -> pd.DataFrame:
    latest_day = stock.get_nearest_business_day_in_a_week()
    df_cap = stock.get_market_cap_by_ticker(latest_day)
    df_change = stock.get_market_price_change_by_ticker(latest_day, latest_day)

    if df_cap.empty or df_change.empty:
        raise RuntimeError("Empty market cap or price change data")

    df_merged = pd.merge(
        df_cap,
        df_change[["종목명", "등락률"]],
        left_index=True,
        right_index=True,
        how="left",
    )

    df_top100 = df_merged.sort_values(by="시가총액", ascending=False).head(100)
    df_final = df_top100[["종목명", "종가", "등락률", "시가총액"]]

    df_final = df_final.rename(columns={"종목명": "이름", "종가": "현재가"})
    df_final = df_final.reset_index().rename(columns={"티커": "종목코드"})
    df_final.index = df_final.index + 1
    return df_final


@cache_data_or_lru(ttl=900, show_spinner=False)
def get_top_100_market_cap_stocks() -> pd.DataFrame:
    """
    시가총액 상위 100개 종목 정보를 반환합니다.
    """
    key = "top_100"
    try:
        df_final = _load_top_100_market_cap_stocks()
        result = _remember_result(key, df_final)
        _record_error(key, None)
        return result
    except Exception as exc:
        logger.warning("get_top_100_market_cap_stocks failed", exc_info=exc)
        _record_error(key, str(exc))
        return _fallback_result(key, pd.DataFrame())


@cache_data_or_lru(show_spinner=False, ttl=60 * 60 * 6)
def get_stock_name_ticker_map() -> Dict[str, str]:
    """
    종목명-티커 매핑을 캐싱하여 반환합니다.
    """
    key = "name_ticker_map"
    try:
        tickers_kospi = stock.get_market_ticker_list(market="KOSPI")
        tickers_kosdaq = stock.get_market_ticker_list(market="KOSDAQ")
        all_tickers = tickers_kospi + tickers_kosdaq
        name_ticker_map = {stock.get_market_ticker_name(ticker): ticker for ticker in all_tickers}
        result = _remember_result(key, name_ticker_map)
        _record_error(key, None)
        return result
    except Exception as exc:
        logger.warning("get_stock_name_ticker_map failed", exc_info=exc)
        _record_error(key, str(exc))
        return _fallback_result(key, {})


def get_stock_info_by_name(stock_name: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    종목명을 기준으로 1년간의 일별 OHLCV 데이터를 반환합니다.
    """
    name_ticker_map = get_stock_name_ticker_map()
    ticker = name_ticker_map.get(stock_name)

    if ticker is None:
        return None, None

    key = f"stock_info::{ticker}"
    try:
        today = datetime.now()
        start_date = (today - timedelta(days=365)).strftime("%Y%m%d")
        today_str = today.strftime("%Y%m%d")

        df = stock.get_market_ohlcv_by_date(start_date, today_str, ticker)
        df.index = df.index.strftime("%Y-%m-%d")

        return _remember_result(key, df), ticker
    except Exception as exc:
        logger.warning(
            "get_stock_info_by_name failed",
            extra={"stock_name": stock_name, "ticker": ticker, "error": str(exc)},
        )
        fallback = _fallback_result(key, None)
        if fallback is not None:
            return fallback, ticker
        return None, ticker


def search_stocks_by_keyword(keyword: str) -> List[str]:
    """
    키워드를 포함하는 종목명 리스트를 반환합니다.
    """
    name_ticker_map = get_stock_name_ticker_map()
    keyword_lower = keyword.lower()
    return [name for name in name_ticker_map.keys() if keyword_lower in name.lower()]


@cache_data_or_lru(ttl=900, show_spinner=False)
def get_financial_ratios(ticker: str) -> Dict[str, Any]:
    """
    최신 재무 지표를 반환합니다.
    """
    key = f"ratios::{ticker}"
    try:
        latest_day = stock.get_nearest_business_day_in_a_week()
        df = stock.get_market_fundamental_by_ticker(latest_day)
        ratios = df.loc[ticker].to_dict()
        result = _remember_result(key, ratios)
        _record_error(key, None)
        return result
    except Exception as exc:
        logger.warning(
            "get_financial_ratios failed", extra={"ticker": ticker, "error": str(exc)}
        )
        _record_error(key, str(exc))
        return _fallback_result(key, {})


def search_news(stock_name: str) -> List[Dict[str, str]]:
    """
    DuckDuckGo Search를 이용해 최신 뉴스를 검색합니다.
    """
    try:
        with DDGS() as ddgs:
            results = list(
                ddgs.news(
                    keywords=f"{stock_name} 주가",
                    region="kr-kr",
                    safesearch="off",
                    timelimit="m",
                    max_results=5,
                )
            )

        if not results:
            return []

        return [
            {
                "title": (r.get("title") or "").strip(),
                "snippet": (r.get("body") or "").strip(),
                "link": r.get("link", ""),
            }
            for r in results
        ]
    except Exception as exc:
        logger.warning(
            "search_news failed", extra={"stock_name": stock_name, "error": str(exc)}
        )
        return []


@cache_data_or_lru(ttl=900, show_spinner=False)
def get_sector_performance(top_n: int = 5) -> pd.DataFrame:
    """
    주도 섹터의 하루 등락률을 계산해 반환합니다.
    """
    key = f"sector_performance::{top_n}"
    try:
        reference_day = stock.get_nearest_business_day_in_a_week()
        start_date = (datetime.now() - timedelta(days=10)).strftime("%Y%m%d")
        end_date = reference_day

        rows: List[Dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=min(4, len(_SECTOR_CANDIDATES))) as executor:
            futures = {
                executor.submit(
                    _load_sector_snapshot, sector_name, start_date, end_date, reference_day
                ): sector_name
                for sector_name in _SECTOR_CANDIDATES
            }
            for future in as_completed(futures):
                sector_name = futures[future]
                try:
                    snapshot = future.result()
                    if snapshot:
                        rows.append(snapshot)
                except Exception as inner_exc:
                    logger.warning(
                        "Failed to load sector data",
                        extra={"sector": sector_name, "error": str(inner_exc)},
                    )

        if not rows:
            raise RuntimeError("No sector data retrieved")

        df = pd.DataFrame(rows)
        df.sort_values("등락률(%)", ascending=False, inplace=True)
        df.reset_index(drop=True, inplace=True)
        result = _remember_result(key, df.head(top_n))
        _record_error(key, None)
        return result
    except Exception as exc:
        logger.warning("get_sector_performance failed", exc_info=exc)
        _record_error(key, str(exc))
        return _fallback_result(key, pd.DataFrame())


@cache_data_or_lru(ttl=600, show_spinner=False)
def get_global_market_snapshot() -> List[Dict[str, Any]]:
    """
    글로벌 선물/환율 스냅샷을 반환합니다.
    """
    key = "global_market_snapshot"
    try:
        payload = _request_with_retry(
            "https://query1.finance.yahoo.com/v7/finance/quote",
            params={"symbols": ",".join(_GLOBAL_SYMBOLS.values())},
        )
        results = payload.get("quoteResponse", {}).get("result", [])

        snapshot: List[Dict[str, Any]] = []
        for label, symbol in _GLOBAL_SYMBOLS.items():
            quote = next((item for item in results if item.get("symbol") == symbol), {})
            if not quote:
                continue
            price = quote.get("regularMarketPrice")
            change = quote.get("regularMarketChange")
            change_pct = quote.get("regularMarketChangePercent")
            snapshot.append(
                {
                    "label": label,
                    "price": price,
                    "change": change,
                    "change_pct": change_pct,
                    "source": "Yahoo Finance",
                    "timestamp": quote.get("regularMarketTime"),
                }
            )

        if not snapshot:
            raise RuntimeError("Empty snapshot response")

        _save_persistent_snapshot(snapshot)
        result = _remember_result(key, snapshot)
        _record_error(key, None)
        return result
    except Exception as exc:
        logger.warning("get_global_market_snapshot failed", exc_info=exc)
        _record_error(key, str(exc))
        fallback = _fallback_result(key, None)
        if fallback:
            return fallback
        persistent = _load_persistent_snapshot()
        if persistent:
            return persistent
        return _build_global_snapshot_placeholder()


__all__ = [
    "get_market_indices",
    "get_top_100_market_cap_stocks",
    "get_stock_name_ticker_map",
    "get_stock_info_by_name",
    "search_stocks_by_keyword",
    "get_financial_ratios",
    "search_news",
    "get_sector_performance",
    "get_global_market_snapshot",
    "get_last_data_error",
]
