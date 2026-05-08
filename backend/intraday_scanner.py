"""
Intraday Bull Run Scanner.

Detects stocks currently in a bull run using live NSE data.
Results stream out one-by-one via Server-Sent Events as they are detected,
not after scanning all stocks.

Detection Logic (5 independent signals, each scored 0-1):
──────────────────────────────────────────────────────────
1. MOMENTUM SURGE (weight: 0.25)
   - Price vs Open: How far above today's open price?
   - >3% above open = 1.0, >2% = 0.8, >1% = 0.5, <0% = 0.0

2. VOLUME CONFIRMATION (weight: 0.25)
   - Today's volume vs 20-day average volume (from yfinance hist).
   - >3x avg = 1.0, >2x = 0.8, >1.5x = 0.6, <1x = 0.0
   - High volume + rising price = institutional buying, not retail noise.

3. RANGE BREAKOUT (weight: 0.20)
   - Is price near intraday high? (buyers in control, no selling pressure)
   - Price within 0.5% of day high = 1.0, within 1% = 0.7, within 2% = 0.4

4. PREVIOUS DAY BREAKOUT (weight: 0.15)
   - Is current price above yesterday's high?
   - If yes = 1.0 (multi-day momentum confirmed)
   - If price > prev_close but < prev_high = 0.5
   - If price < prev_close = 0.0

5. 52-WEEK STRENGTH (weight: 0.15)
   - How close to 52-week high?
   - Within 5% = 1.0 (new highs = strongest momentum)
   - Within 10% = 0.6
   - Below 20% from high = 0.2

Final bull_score = weighted sum of all 5 signals.
Bull run detected if bull_score >= 0.55 (adjustable threshold).

Classification:
  bull_score >= 0.80 → "ROCKET"     (all signals aligned, extreme momentum)
  bull_score >= 0.65 → "STRONG_BUY" (clear bull run, high confidence)
  bull_score >= 0.55 → "BUILDING"   (momentum building, watch closely)
  bull_score <  0.55 → filtered out (not shown)
"""
import logging
import json
import asyncio
import time
from datetime import datetime
from typing import AsyncGenerator, List, Optional

import pytz

logger = logging.getLogger(__name__)
IST = pytz.timezone("Asia/Kolkata")

# ── Signal weights ───────────────────────────────────────────────
WEIGHTS = {
    "momentum":    0.25,
    "volume":      0.25,
    "range":       0.20,
    "prev_break":  0.15,
    "yearly":      0.15,
}

BULL_THRESHOLD = 0.55  # Minimum score to qualify as bull run


def _score_momentum(ltp: float, open_price: float) -> tuple:
    """Score based on how far price is above today's open."""
    if open_price <= 0:
        return 0.0, "no_open_data"
    pct = ((ltp - open_price) / open_price) * 100
    if pct >= 3.0:
        return 1.0, f"+{pct:.1f}% from open (strong surge)"
    elif pct >= 2.0:
        return 0.8, f"+{pct:.1f}% from open (solid momentum)"
    elif pct >= 1.0:
        return 0.5, f"+{pct:.1f}% from open (mild positive)"
    elif pct >= 0:
        return 0.2, f"+{pct:.1f}% from open (flat)"
    else:
        return 0.0, f"{pct:.1f}% from open (bearish)"


def _score_volume(volume: int, avg_volume: float) -> tuple:
    """Score based on volume spike vs 20-day average."""
    if avg_volume <= 0:
        return 0.3, "no_avg_volume"  # Give neutral if no historical data
    ratio = volume / avg_volume
    if ratio >= 3.0:
        return 1.0, f"{ratio:.1f}x avg volume (massive buying)"
    elif ratio >= 2.0:
        return 0.8, f"{ratio:.1f}x avg volume (heavy activity)"
    elif ratio >= 1.5:
        return 0.6, f"{ratio:.1f}x avg volume (above normal)"
    elif ratio >= 1.0:
        return 0.3, f"{ratio:.1f}x avg volume (normal)"
    else:
        return 0.0, f"{ratio:.1f}x avg volume (low interest)"


def _score_range_position(ltp: float, day_high: float, day_low: float) -> tuple:
    """Score based on where price sits in today's range. Near high = buyers winning."""
    if day_high <= day_low or day_high <= 0:
        return 0.3, "narrow_range"
    pct_from_high = ((day_high - ltp) / day_high) * 100
    if pct_from_high <= 0.3:
        return 1.0, "at day high (buyers dominating)"
    elif pct_from_high <= 1.0:
        return 0.7, f"{pct_from_high:.1f}% from day high"
    elif pct_from_high <= 2.0:
        return 0.4, f"{pct_from_high:.1f}% from day high"
    else:
        return 0.1, f"{pct_from_high:.1f}% below day high"


def _score_prev_day_breakout(ltp: float, prev_close: float, prev_high: float = None) -> tuple:
    """Score based on breakout above previous day levels."""
    if prev_close <= 0:
        return 0.3, "no_prev_data"
    # If we don't have prev_high, estimate it as prev_close * 1.02
    if not prev_high or prev_high <= 0:
        prev_high = prev_close * 1.02

    if ltp > prev_high:
        return 1.0, f"above prev high {prev_high:.0f} (breakout confirmed)"
    elif ltp > prev_close:
        return 0.5, f"above prev close {prev_close:.0f}"
    else:
        return 0.0, f"below prev close"


def _score_yearly_strength(ltp: float, year_high: float) -> tuple:
    """Score based on proximity to 52-week high."""
    if year_high <= 0:
        return 0.3, "no_52w_data"
    pct_from_high = ((year_high - ltp) / year_high) * 100
    if pct_from_high <= 2:
        return 1.0, f"near 52w high (within {pct_from_high:.1f}%)"
    elif pct_from_high <= 5:
        return 0.8, f"{pct_from_high:.1f}% from 52w high"
    elif pct_from_high <= 10:
        return 0.6, f"{pct_from_high:.1f}% from 52w high"
    elif pct_from_high <= 20:
        return 0.3, f"{pct_from_high:.1f}% from 52w high"
    else:
        return 0.1, f"{pct_from_high:.1f}% below 52w high"


def _calculate_exit_levels(ltp, open_price, high, low, prev_close, year_high):
    """
    Calculate stop loss, targets, and risk:reward for an intraday bull.

    Logic:
    ─────
    STOP LOSS: The higher of today's low or 1.5% below current price.
    - Today's low = the level where buyers already stepped in once.
    - 1.5% trailing = max acceptable loss on an intraday momentum trade.

    TARGET 1 (Conservative): Range extension.
    - Today's range (high - low) projected above current price.
    - If stock moved ₹50 today, expect another ₹25-50 move in same direction.

    TARGET 2 (Aggressive): 52-week high.
    - For stocks already near 52w high, use 5% above current price.
    - Ultimate resistance level — book profits here.

    TRAILING STOP: If stock is already up 3%+ from open, tighten stop to
    1% below current. Protects gains on fast runners.

    RISK:REWARD: Calculated as (Target1 - LTP) / (LTP - StopLoss).
    - Below 1.5 = not worth the risk, skip.
    - 2.0+ = good trade.
    - 3.0+ = excellent setup.
    """
    # Stop loss
    stop_at_low = low if low > 0 else ltp * 0.985
    stop_pct_trail = ltp * 0.985  # 1.5% below current
    stop_loss = max(stop_at_low, stop_pct_trail)

    # If already up big, tighten trailing stop
    if open_price > 0:
        gain_from_open = ((ltp - open_price) / open_price) * 100
        if gain_from_open >= 3.0:
            # Tighten to 1% below current for fast movers
            tight_stop = ltp * 0.99
            stop_loss = max(stop_loss, tight_stop)
    else:
        gain_from_open = 0

    # Target 1: Range extension
    day_range = high - low if (high > 0 and low > 0) else ltp * 0.02
    target_1 = ltp + (day_range * 0.5)  # Half-range extension (conservative)

    # Target 2: 52-week high or 5% above current if already near it
    if year_high > 0 and year_high > ltp * 1.02:
        target_2 = year_high
    else:
        target_2 = ltp * 1.05  # 5% above current

    # Risk:Reward
    risk = ltp - stop_loss
    reward = target_1 - ltp
    rr_ratio = round(reward / risk, 2) if risk > 0 else 0

    # Stop loss and target as percentages from LTP
    sl_pct = round(((ltp - stop_loss) / ltp) * 100, 2) if ltp > 0 else 0
    t1_pct = round(((target_1 - ltp) / ltp) * 100, 2) if ltp > 0 else 0
    t2_pct = round(((target_2 - ltp) / ltp) * 100, 2) if ltp > 0 else 0

    # Action advice
    if rr_ratio >= 2.0:
        action = "ENTER"
        reason = f"R:R {rr_ratio}:1 — favorable setup"
    elif rr_ratio >= 1.5:
        action = "WATCH"
        reason = f"R:R {rr_ratio}:1 — decent but wait for dip to improve entry"
    elif gain_from_open >= 5:
        action = "LATE_ENTRY"
        reason = f"Already up {gain_from_open:.1f}% — most of the move is done, trail tight"
    else:
        action = "RISKY"
        reason = f"R:R {rr_ratio}:1 — risk too high relative to upside"

    return {
        "stop_loss": round(stop_loss, 2),
        "stop_loss_pct": sl_pct,
        "target_1": round(target_1, 2),
        "target_1_pct": t1_pct,
        "target_2": round(target_2, 2),
        "target_2_pct": t2_pct,
        "risk_reward": rr_ratio,
        "action": action,
        "action_reason": reason,
        "trailing_active": gain_from_open >= 3.0,
    }


def analyze_bull_run(stock: dict, avg_volume: float = 0) -> Optional[dict]:
    """
    Run all 5 bull-detection signals on a single stock.
    Returns enriched dict if bull_score >= threshold, else None.
    """
    ltp = stock.get("ltp", 0) or 0
    open_price = stock.get("open", 0) or 0
    high = stock.get("high", 0) or 0
    low = stock.get("low", 0) or 0
    volume = stock.get("volume", 0) or 0
    prev_close = stock.get("prev_close", 0) or 0
    year_high = stock.get("year_high", 0) or 0
    change_pct = stock.get("change_pct", 0) or 0

    if ltp <= 0:
        return None

    # Run each signal
    mom_score, mom_reason = _score_momentum(ltp, open_price)
    vol_score, vol_reason = _score_volume(volume, avg_volume)
    range_score, range_reason = _score_range_position(ltp, high, low)
    prev_score, prev_reason = _score_prev_day_breakout(ltp, prev_close)
    year_score, year_reason = _score_yearly_strength(ltp, year_high)

    # Weighted total
    bull_score = (
        mom_score   * WEIGHTS["momentum"]
        + vol_score   * WEIGHTS["volume"]
        + range_score * WEIGHTS["range"]
        + prev_score  * WEIGHTS["prev_break"]
        + year_score  * WEIGHTS["yearly"]
    )

    if bull_score < BULL_THRESHOLD:
        return None

    # Classify intensity
    if bull_score >= 0.80:
        tag = "ROCKET"
    elif bull_score >= 0.65:
        tag = "STRONG_BUY"
    else:
        tag = "BUILDING"

    # Calculate exit levels
    exits = _calculate_exit_levels(ltp, open_price, high, low, prev_close, year_high)

    # Build signal breakdown for the UI
    signals = [
        {"name": "Momentum",       "score": round(mom_score, 2),   "reason": mom_reason,   "weight": WEIGHTS["momentum"]},
        {"name": "Volume",         "score": round(vol_score, 2),   "reason": vol_reason,   "weight": WEIGHTS["volume"]},
        {"name": "Range Position", "score": round(range_score, 2), "reason": range_reason, "weight": WEIGHTS["range"]},
        {"name": "Prev Breakout",  "score": round(prev_score, 2),  "reason": prev_reason,  "weight": WEIGHTS["prev_break"]},
        {"name": "52W Strength",   "score": round(year_score, 2),  "reason": year_reason,  "weight": WEIGHTS["yearly"]},
    ]

    return {
        "symbol": stock.get("symbol", ""),
        "name": stock.get("name", stock.get("symbol", "")),
        "ltp": ltp,
        "open": open_price,
        "high": high,
        "low": low,
        "prev_close": prev_close,
        "change": round(ltp - prev_close, 2),
        "change_pct": round(change_pct, 2),
        "volume": volume,
        "year_high": year_high,
        "bull_score": round(bull_score, 3),
        "bull_tag": tag,
        "signals": signals,
        "exits": exits,
        "detected_at": datetime.now(IST).strftime("%H:%M:%S"),
    }


async def stream_bull_scan(stocks: List[dict], avg_volumes: dict = None) -> AsyncGenerator[str, None]:
    """
    Async generator that yields SSE events as bull-run stocks are detected.
    Each stock is analyzed immediately and streamed if it qualifies.
    No waiting for the full scan to complete.
    """
    if avg_volumes is None:
        avg_volumes = {}

    total = len(stocks)
    found = 0

    # Send scan start event
    yield f"data: {json.dumps({'type': 'scan_start', 'total': total, 'timestamp': datetime.now(IST).strftime('%H:%M:%S')})}\n\n"

    for i, stock in enumerate(stocks):
        symbol = stock.get("symbol", "")
        avg_vol = avg_volumes.get(symbol, 0)

        result = analyze_bull_run(stock, avg_vol)
        if result:
            found += 1
            yield f"data: {json.dumps({'type': 'bull_detected', 'data': result, 'progress': i+1, 'total': total})}\n\n"

        # Send progress every 10 stocks
        if (i + 1) % 10 == 0:
            yield f"data: {json.dumps({'type': 'progress', 'progress': i+1, 'total': total, 'found': found})}\n\n"

        # Small yield to prevent blocking the event loop
        await asyncio.sleep(0.01)

    # Send scan complete
    yield f"data: {json.dumps({'type': 'scan_complete', 'total_scanned': total, 'bulls_found': found, 'timestamp': datetime.now(IST).strftime('%H:%M:%S')})}\n\n"
