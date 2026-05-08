"""
Live NSE/BSE data fetcher.

Pulls real-time market data directly from NSE India and BSE India APIs
during trading hours (9:15 AM - 3:30 PM IST).

NSE endpoints used:
  - /api/equity-stockIndices?index=NIFTY%2050        → bulk quotes for index constituents
  - /api/live-analysis-variations?index=gainers       → top gainers
  - /api/live-analysis-variations?index=losers         → top losers
  - /api/market-data-pre-open?key=NIFTY              → pre-open session data

BSE endpoint:
  - /api/getScripHeaderData.aspx?Ession_id=...&scripcode=... → per-stock live data

NSE requires session cookies from the main page before API calls work.
This module handles that transparently.
"""
import logging
import time
import random
import threading
from datetime import datetime
from typing import Optional, Dict, List

import requests
import pytz

logger = logging.getLogger(__name__)

IST = pytz.timezone("Asia/Kolkata")

# ── NSE session management ───────────────────────────────────────
_nse_session = None
_nse_session_lock = threading.Lock()
_nse_session_ts = 0
_NSE_SESSION_TTL = 180  # refresh cookies every 3 min

_NSE_BASE = "https://www.nseindia.com"
_NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.nseindia.com/",
    "Connection": "keep-alive",
}

# Try curl_cffi first (bypasses NSE's TLS fingerprint blocking)
try:
    from curl_cffi import requests as cffi_requests
    _HAS_CURL_CFFI = True
except ImportError:
    _HAS_CURL_CFFI = False


def _get_nse_session():
    """Get or create a session with valid NSE cookies using curl_cffi."""
    global _nse_session, _nse_session_ts
    with _nse_session_lock:
        now = time.time()
        if _nse_session and (now - _nse_session_ts) < _NSE_SESSION_TTL:
            return _nse_session

        if _HAS_CURL_CFFI:
            s = cffi_requests.Session(impersonate="chrome120")
        else:
            s = requests.Session()
            s.headers.update(_NSE_HEADERS)
        
        # Visit main page to get cookies
        try:
            r = s.get(_NSE_BASE, timeout=10)
            logger.info(f"nse_live: session created (curl_cffi={_HAS_CURL_CFFI}), status={r.status_code}")
        except Exception as e:
            logger.warning(f"nse_live: cookie fetch failed: {e}")
        _nse_session = s
        _nse_session_ts = now
        return s


def _nse_get(path: str, params: dict = None, retries: int = 2) -> Optional[dict]:
    """Make a GET request to NSE API with retry logic."""
    for attempt in range(retries + 1):
        try:
            s = _get_nse_session()
            url = f"{_NSE_BASE}{path}"
            r = s.get(url, params=params, timeout=10)
            if r.status_code == 401 or r.status_code == 403:
                # Cookie expired, force refresh
                global _nse_session_ts
                _nse_session_ts = 0
                if attempt < retries:
                    time.sleep(1)
                    continue
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.warning(f"nse_live: {path} attempt {attempt+1} failed: {e}")
            if attempt < retries:
                time.sleep(1 + random.random())
    return None


# ── Public API ───────────────────────────────────────────────────

def fetch_index_quotes(index: str = "NIFTY 50") -> List[dict]:
    """
    Fetch live quotes for all stocks in an NSE index.
    Returns list of dicts with: symbol, open, high, low, ltp, change, pChange,
    totalTradedVolume, previousClose, etc.
    
    This is the BULK endpoint - one call gives all 50 stocks instantly.
    No need to loop through tickers one by one.
    """
    data = _nse_get("/api/equity-stockIndices", params={"index": index})
    if not data or "data" not in data:
        return []
    
    results = []
    for item in data["data"]:
        if item.get("symbol") == index.replace(" ", ""):
            continue  # Skip the index row itself
        results.append({
            "symbol": item.get("symbol", ""),
            "name": item.get("meta", {}).get("companyName", item.get("symbol", "")),
            "open": item.get("open", 0),
            "high": item.get("dayHigh", 0),
            "low": item.get("dayLow", 0),
            "ltp": item.get("lastPrice", 0),
            "prev_close": item.get("previousClose", 0),
            "change": item.get("change", 0),
            "change_pct": item.get("pChange", 0),
            "volume": item.get("totalTradedVolume", 0),
            "value": item.get("totalTradedValue", 0),
            "year_high": item.get("yearHigh", 0),
            "year_low": item.get("yearLow", 0),
            "last_update": item.get("lastUpdateTime", ""),
        })
    return results


def fetch_top_gainers() -> List[dict]:
    """Fetch top gainers from NSE live analysis."""
    data = _nse_get("/api/live-analysis-variations", params={"index": "gainers"})
    if not data or "NIFTY" not in data:
        return []
    return data.get("NIFTY", {}).get("data", [])


def fetch_top_losers() -> List[dict]:
    """Fetch top losers from NSE live analysis."""
    data = _nse_get("/api/live-analysis-variations", params={"index": "losers"})
    if not data or "NIFTY" not in data:
        return []
    return data.get("NIFTY", {}).get("data", [])


def fetch_preopen_data(key: str = "NIFTY") -> List[dict]:
    """Fetch pre-open session data (9:00-9:08 AM)."""
    data = _nse_get("/api/market-data-pre-open", params={"key": key})
    if not data or "data" not in data:
        return []
    return [item.get("metadata", {}) for item in data["data"]]


def fetch_market_status() -> dict:
    """Check if market is open/closed."""
    data = _nse_get("/api/marketStatus")
    if not data:
        return {"status": "unknown"}
    states = data.get("marketState", [])
    for s in states:
        if s.get("market") == "Capital Market":
            return {
                "status": s.get("marketStatus", "unknown"),
                "trade_date": s.get("tradeDate", ""),
                "index": s.get("index", ""),
                "last": s.get("last", 0),
                "variation": s.get("variation", 0),
                "percent_change": s.get("percentChange", 0),
            }
    return {"status": "unknown"}


def is_market_open() -> bool:
    """Quick check: is Indian equity market currently open?"""
    now = datetime.now(IST)
    # Market hours: 9:15 AM to 3:30 PM, Mon-Fri
    if now.weekday() >= 5:
        return False
    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return market_open <= now <= market_close


def fetch_all_nse_stocks(index_list: List[str] = None) -> List[dict]:
    """
    Fetch bulk live data for multiple indices in parallel.
    Default: Nifty 50 + Nifty Next 50 + Nifty Midcap 50.
    Each call gets ~50 stocks instantly (no per-ticker loops).
    """
    if index_list is None:
        index_list = ["NIFTY 50", "NIFTY NEXT 50", "NIFTY MIDCAP 50"]
    
    all_stocks = {}
    for idx in index_list:
        quotes = fetch_index_quotes(idx)
        for q in quotes:
            sym = q["symbol"]
            if sym not in all_stocks:
                all_stocks[sym] = q
        # Small delay between index calls to be polite
        time.sleep(0.5)
    
    return list(all_stocks.values())
