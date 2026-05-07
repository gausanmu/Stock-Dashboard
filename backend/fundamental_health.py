"""
Fundamental Health Score (NOT sentiment).

Pure mathematical score based on balance-sheet metrics. 0-100 scale.

Scoring buckets:
  ROE                     0..25
  Debt-to-Equity (lower)  0..20
  Profit Margin           0..15
  Earnings Growth         0..15
  Revenue Growth          0..10
  P/E Ratio (Goldilocks)  0..10
  Free Cash Flow status   0..5
"""
import logging
from datetime import datetime, timezone
from typing import Optional

import cache

logger = logging.getLogger(__name__)


def _safe(v, default=None):
    try:
        f = float(v)
        if f != f:  # NaN
            return default
        return f
    except (TypeError, ValueError):
        return default


def compute_health(info: dict) -> dict:
    """info = yfinance Ticker.info dict.
    Returns: { score, grade, components, drivers }
    """
    roe = _safe(info.get("returnOnEquity"))
    if roe is not None:
        roe *= 100
    de = _safe(info.get("debtToEquity"))
    margin = _safe(info.get("profitMargins"))
    if margin is not None:
        margin *= 100
    eg = _safe(info.get("earningsGrowth"))
    if eg is not None:
        eg *= 100
    rg = _safe(info.get("revenueGrowth"))
    if rg is not None:
        rg *= 100
    pe = _safe(info.get("trailingPE"))
    fcf = _safe(info.get("freeCashflow"))

    components = {}
    drivers = []

    # ROE 0..25
    if roe is None:
        components["roe"] = 0
    elif roe >= 25:
        components["roe"] = 25; drivers.append(f"Excellent ROE {roe:.1f}%")
    elif roe >= 15:
        components["roe"] = 20; drivers.append(f"Strong ROE {roe:.1f}%")
    elif roe >= 8:
        components["roe"] = 12
    elif roe >= 3:
        components["roe"] = 6
    else:
        components["roe"] = 0; drivers.append(f"Weak ROE {roe:.1f}%")

    # Debt/Equity 0..20 (lower is better; capped)
    if de is None:
        components["debt"] = 10  # neutral if unknown
    elif de < 30:
        components["debt"] = 20; drivers.append(f"Low debt D/E {de:.0f}")
    elif de < 60:
        components["debt"] = 15
    elif de < 100:
        components["debt"] = 8
    elif de < 200:
        components["debt"] = 3
    else:
        components["debt"] = 0; drivers.append(f"High leverage D/E {de:.0f}")

    # Profit margin 0..15
    if margin is None:
        components["margin"] = 0
    elif margin >= 20:
        components["margin"] = 15; drivers.append(f"Premium margin {margin:.1f}%")
    elif margin >= 10:
        components["margin"] = 11
    elif margin >= 5:
        components["margin"] = 6
    elif margin > 0:
        components["margin"] = 2
    else:
        components["margin"] = 0; drivers.append(f"Negative margin {margin:.1f}%")

    # Earnings growth 0..15
    if eg is None:
        components["eg"] = 0
    elif eg >= 25:
        components["eg"] = 15; drivers.append(f"Strong earnings growth {eg:.1f}%")
    elif eg >= 10:
        components["eg"] = 10
    elif eg >= 0:
        components["eg"] = 5
    else:
        components["eg"] = 0; drivers.append(f"Earnings decline {eg:.1f}%")

    # Revenue growth 0..10
    if rg is None:
        components["rg"] = 0
    elif rg >= 20:
        components["rg"] = 10; drivers.append(f"Top-line growth {rg:.1f}%")
    elif rg >= 8:
        components["rg"] = 7
    elif rg >= 0:
        components["rg"] = 3
    else:
        components["rg"] = 0

    # P/E Goldilocks 0..10 — penalize too cheap or too expensive
    if pe is None or pe <= 0:
        components["pe"] = 5  # neutral
    elif 12 <= pe <= 28:
        components["pe"] = 10; drivers.append(f"Fair valuation P/E {pe:.1f}")
    elif 8 <= pe < 12 or 28 < pe <= 45:
        components["pe"] = 6
    elif pe > 45:
        components["pe"] = 2; drivers.append(f"Expensive P/E {pe:.1f}")
    else:
        components["pe"] = 3  # too cheap may signal trouble

    # Free Cash Flow 0..5
    if fcf is None:
        components["fcf"] = 2
    elif fcf > 0:
        components["fcf"] = 5
    else:
        components["fcf"] = 0; drivers.append("Negative free cash flow")

    score = sum(components.values())
    if score >= 80:
        grade = "A+"
    elif score >= 70:
        grade = "A"
    elif score >= 60:
        grade = "B"
    elif score >= 45:
        grade = "C"
    elif score >= 30:
        grade = "D"
    else:
        grade = "F"

    return {
        "score": score,
        "grade": grade,
        "components": components,
        "drivers": drivers[:4],  # top 4 drivers shown in UI
        "raw": {
            "roe": roe, "debt_to_equity": de, "profit_margin": margin,
            "earnings_growth": eg, "revenue_growth": rg, "pe": pe,
            "free_cash_flow": fcf,
        },
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }


def health_for_ticker(ticker: str, info: Optional[dict] = None,
                      force_refresh: bool = False) -> dict:
    ticker = ticker.upper().replace(".NS", "")
    if not force_refresh:
        cached = cache.get_fundamental(ticker)
        if cached:
            return cached

    if info is None:
        # Lazy import to avoid circular dep
        from yf_fetcher import fetch_ticker
        raw = fetch_ticker(ticker)
        if not raw:
            result = {"ticker": ticker, "state": "unavailable", "score": 0, "grade": "—",
                      "components": {}, "drivers": ["No data"]}
            cache.set_fundamental(ticker, result, ttl=3600)
            return result
        info = raw["info"]

    health = compute_health(info)
    health["ticker"] = ticker
    health["state"] = "ok"
    cache.set_fundamental(ticker, health, ttl=86400)
    return health
