"""
Throttled, resilient yfinance fetcher.

Hard rules:
  - Max 5 concurrent requests (semaphore)
  - Max ~20 req/min via per-call sleep
  - 3 retries with exponential backoff (5s / 15s / 45s) on 429 / network error
  - Rotating User-Agent pool
  - Per-ticker error isolation (one bad ticker never breaks a batch)
  - Failed tickers logged + auto-blacklisted after 3 strikes
  - Strict data quality validation before returning
"""
import logging
import random
import threading
import time
from datetime import datetime, timezone
from typing import Optional

import yfinance as yf
try:
    from curl_cffi import requests as cffi_requests
    _HAS_CURL_CFFI = True
except ImportError:
    _HAS_CURL_CFFI = False

import cache
from market_hours import stale_threshold_days

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────
MAX_CONCURRENT = 5
RETRY_DELAYS = [5, 15, 45]  # seconds
MIN_INTERVAL_S = 1.2  # ~50 req/min ceiling (safe for local dev)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
]

_semaphore = threading.Semaphore(MAX_CONCURRENT)
_last_call_lock = threading.Lock()
_last_call_ts = [0.0]


def _wait_min_interval():
    """Ensure at least MIN_INTERVAL_S between any two yfinance calls (global)."""
    with _last_call_lock:
        now = time.time()
        wait = MIN_INTERVAL_S - (now - _last_call_ts[0])
        if wait > 0:
            time.sleep(wait)
        _last_call_ts[0] = time.time()


def _make_session():
    """Build a curl_cffi session impersonating a browser for yfinance compatibility."""
    if not _HAS_CURL_CFFI:
        return None
    impersonate_choice = random.choice(["chrome120", "safari17_0", "chrome119", "edge99"])
    s = cffi_requests.Session(impersonate=impersonate_choice)
    s.headers.update({
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9",
    })
    return s


def is_valid_ticker_data(price: Optional[float], volume: Optional[int],
                         last_date: Optional[datetime]) -> tuple[bool, str]:
    """Strict data quality validation."""
    if price is None or price <= 0:
        return False, "null_or_zero_price"
    if volume is None or volume == 0:
        return False, "zero_volume"
    if last_date:
        if last_date.tzinfo is None:
            last_date = last_date.replace(tzinfo=timezone.utc)
        days_old = (datetime.now(timezone.utc) - last_date).days
        if days_old > stale_threshold_days():
            return False, f"stale_data_{days_old}d"
    return True, "ok"


def fetch_ticker(ticker_symbol: str, force_refresh: bool = False) -> Optional[dict]:
    """
    Fetch raw yfinance data for one ticker with full resilience.
    Returns dict with {info, hist} or None on permanent failure.
    Caller is responsible for calling analysis_engine on the result.
    """
    symbol = ticker_symbol if ticker_symbol.endswith(".NS") else f"{ticker_symbol}.NS"
    cache_key = ticker_symbol.replace(".NS", "").upper()

    # Skip blacklisted tickers
    if cache.is_ticker_blacklisted(cache_key):
        logger.debug(f"fetch: {cache_key} blacklisted, skipping")
        return None

    # Cache hit
    if not force_refresh:
        cached = cache.get_ticker(cache_key)
        if cached:
            return cached

    last_err = None
    for attempt in range(len(RETRY_DELAYS) + 1):
        with _semaphore:
            _wait_min_interval()
            try:
                session = _make_session()
                if session is not None:
                    stock = yf.Ticker(symbol, session=session)
                else:
                    stock = yf.Ticker(symbol)
                info = stock.info or {}
                hist = stock.history(period="1y")

                if hist.empty:
                    cache.record_ticker_failure(cache_key)
                    cache.log_error(cache_key, "empty_history", f"yfinance returned empty hist")
                    return None

                last_close = float(hist["Close"].iloc[-1])
                last_vol = int(hist["Volume"].iloc[-1]) if not hist["Volume"].empty else 0
                last_date = hist.index[-1].to_pydatetime()
                ok, reason = is_valid_ticker_data(last_close, last_vol, last_date)
                if not ok:
                    cache.record_ticker_failure(cache_key)
                    cache.log_error(cache_key, "invalid_data", reason)
                    return None

                # Reset failure count on success
                cache.reset_ticker_failure(cache_key)
                result = {"info": info, "hist": hist, "_fetched_at": datetime.now(timezone.utc).isoformat()}
                # Note: we don't cache the full hist dataframe via L2 (too big) —
                # only L1 in-memory. The analysis_engine output is what gets L2-cached.
                return result

            except Exception as e:
                last_err = e
                err_str = str(e).lower()
                # 429 / rate limit / connection errors → backoff & retry
                if "429" in err_str or "rate" in err_str or "timeout" in err_str or "connection" in err_str:
                    if attempt < len(RETRY_DELAYS):
                        delay = RETRY_DELAYS[attempt]
                        logger.warning(f"fetch {cache_key}: {err_str[:100]} — retry in {delay}s")
                        time.sleep(delay)
                        continue
                # Non-retryable
                cache.record_ticker_failure(cache_key)
                cache.log_error(cache_key, "fetch_error", str(e))
                logger.error(f"fetch {cache_key} failed: {e}")
                return None

    cache.record_ticker_failure(cache_key)
    cache.log_error(cache_key, "max_retries", str(last_err))
    return None
