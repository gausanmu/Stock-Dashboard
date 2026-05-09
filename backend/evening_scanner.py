"""
Evening Scanner — Predictive Pre-Rally Pattern Detection Engine

Runs at 3:45 PM IST daily. Analyzes EOD data to find stocks showing
pre-rally signatures for next-day entry.

6 Patterns Detected:
  1. Compression Breakout   (20%) — Tight range breaking with volume
  2. Volume Accumulation    (20%) — Institutional buying signals
  3. Seller Exhaustion      (15%) — Oversold reversal candles
  4. Breakout Retest        (20%) — Pullback to new support level
  5. EMA Power Alignment    (10%) — All EMAs stacked bullish
  6. Sector Rotation Lag    (15%) — Cheapest stock in hottest sector
"""
import logging
import yfinance as yf
from datetime import datetime
from typing import List, Optional, Dict
import pytz

logger = logging.getLogger(__name__)
IST = pytz.timezone("Asia/Kolkata")

# Pattern weights — calibrated from backtest win rates
# Volume Accumulation: 55.6% WR, Compression: 50%, Retest: 42%, EMA: 43%, Exhaustion: 37%
PATTERN_WEIGHTS = {
    "volume_accumulation": 0.40,
    "compression_breakout": 0.30,
    "breakout_retest": 0.15,
    "ema_power": 0.10,
    "seller_exhaustion": 0.05,
}

# Conviction thresholds — tightened to reduce weak signals
ROCKET_THRESHOLD = 0.55
STRONG_THRESHOLD = 0.40
WATCH_THRESHOLD = 0.32
MIN_RR_RATIO = 2.0

# Pre-filters
MIN_AVG_VOLUME = 100_000    # Minimum daily volume (shares)
MIN_ATR_PCT = 0.015         # Minimum ATR as % of price (1.5%)


# ── Helper functions ─────────────────────────────────────────────
def _sma(values, period):
    if len(values) < period:
        return values[-1] if values else 0
    return sum(values[-period:]) / period


def _ema(values, period):
    if not values:
        return 0
    if len(values) < period:
        return sum(values) / len(values)
    k = 2 / (period + 1)
    ema = sum(values[:period]) / period
    for v in values[period:]:
        ema = v * k + ema * (1 - k)
    return ema


def _rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50.0
    gains, losses = [], []
    for i in range(1, len(prices)):
        delta = prices[i] - prices[i - 1]
        gains.append(max(0, delta))
        losses.append(max(0, -delta))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _atr(h, l, c, period=14):
    if len(c) < period + 1:
        return max(c[-1] * 0.02 if c else 1.0, 0.01)
    tr_list = []
    for i in range(1, len(c)):
        tr = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
        tr_list.append(tr)
    return sum(tr_list[-period:]) / period if tr_list else 1.0


def _adx(h, l, c, period=14):
    """Average Directional Index — trend strength. >25 = strong trend."""
    if len(c) < period * 2 + 1:
        return 20.0  # default neutral
    plus_dm, minus_dm, tr_list = [], [], []
    for i in range(1, len(c)):
        up = h[i] - h[i-1]
        down = l[i-1] - l[i]
        plus_dm.append(max(up, 0) if up > down else 0)
        minus_dm.append(max(down, 0) if down > up else 0)
        tr_list.append(max(h[i] - l[i], abs(h[i] - c[i-1]), abs(l[i] - c[i-1])))
    # Smoothed averages
    atr_s = sum(tr_list[:period]) / period
    pdm_s = sum(plus_dm[:period]) / period
    mdm_s = sum(minus_dm[:period]) / period
    dx_list = []
    for i in range(period, len(tr_list)):
        atr_s = (atr_s * (period - 1) + tr_list[i]) / period
        pdm_s = (pdm_s * (period - 1) + plus_dm[i]) / period
        mdm_s = (mdm_s * (period - 1) + minus_dm[i]) / period
        pdi = (pdm_s / atr_s * 100) if atr_s > 0 else 0
        mdi = (mdm_s / atr_s * 100) if atr_s > 0 else 0
        dx = abs(pdi - mdi) / (pdi + mdi) * 100 if (pdi + mdi) > 0 else 0
        dx_list.append(dx)
    if not dx_list:
        return 20.0
    return sum(dx_list[-period:]) / min(len(dx_list), period)


def _bollinger_width(prices, period=20):
    """Returns BB width as % of price — measures compression."""
    if len(prices) < period:
        return 5.0  # default wide
    recent = prices[-period:]
    mean = sum(recent) / period
    var = sum((p - mean) ** 2 for p in recent) / period
    sd = var ** 0.5
    if mean == 0:
        return 5.0
    return (4 * sd / mean) * 100  # width as percentage


def _macd_hist(prices):
    if len(prices) < 35:
        return 0.0
    ema12 = _ema(prices, 12)
    ema26 = _ema(prices, 26)
    macd_line = ema12 - ema26
    macd_series = []
    for i in range(26, len(prices) + 1):
        macd_series.append(_ema(prices[:i], 12) - _ema(prices[:i], 26))
    signal = _ema(macd_series[-9:], 9) if len(macd_series) >= 9 else macd_line
    return macd_line - signal


# ── Pattern 1: Compression Breakout ──────────────────────────────
def _detect_compression_breakout(close, high, low, volume):
    """
    Tight range for 5+ days then today breaks out with volume.
    Score 0.0-1.0
    """
    if len(close) < 25:
        return 0.0, "Insufficient data"

    # Calculate BB width for last 20 days and compare to last 60 days
    current_width = _bollinger_width(close[-20:])
    historical_widths = []
    for i in range(max(0, len(close) - 60), len(close) - 5):
        w = _bollinger_width(close[max(0, i-20):i])
        if w > 0:
            historical_widths.append(w)

    if not historical_widths:
        return 0.0, "No historical width data"

    avg_width = sum(historical_widths) / len(historical_widths)
    width_ratio = current_width / avg_width if avg_width > 0 else 1.0

    # Check if range was tight (compressed)
    is_compressed = width_ratio < 0.7  # Current width < 70% of average

    # Check today's candle breaks out of recent range
    recent_high = max(high[-6:-1]) if len(high) >= 6 else high[-2]
    today_breakout = close[-1] > recent_high

    # Volume confirmation
    avg_vol = sum(volume[-20:]) / max(len(volume[-20:]), 1) if volume else 1
    vol_ratio = volume[-1] / avg_vol if avg_vol > 0 else 1

    score = 0.0
    reasons = []

    if is_compressed:
        score += 0.4
        reasons.append(f"BB width compressed to {width_ratio:.0%} of avg")

    if today_breakout:
        score += 0.3
        reasons.append(f"Price broke above {recent_high:.0f} range high")

    if vol_ratio >= 1.5:
        score += 0.3
        reasons.append(f"Volume {vol_ratio:.1f}x average")
    elif vol_ratio >= 1.2:
        score += 0.15
        reasons.append(f"Volume {vol_ratio:.1f}x average (mild)")

    reason = " | ".join(reasons) if reasons else "No compression pattern"
    return min(1.0, score), reason


# ── Pattern 2: Volume Accumulation ───────────────────────────────
def _detect_volume_accumulation(close, volume, high, low):
    """
    Heavy volume + price up + estimated high delivery = institutional buying.
    """
    if len(close) < 21:
        return 0.0, "Insufficient data"

    price_change = (close[-1] - close[-2]) / close[-2] * 100 if close[-2] else 0
    avg_vol = sum(volume[-20:]) / max(len(volume[-20:]), 1)
    vol_ratio = volume[-1] / avg_vol if avg_vol > 0 else 1

    # Estimate delivery: narrow range + high volume = likely high delivery
    # Wide range + high volume = likely speculative
    today_range = (high[-1] - low[-1]) / close[-1] * 100 if close[-1] else 0
    avg_range = sum(
        (high[i] - low[i]) / close[i] * 100
        for i in range(max(0, len(close) - 20), len(close) - 1)
        if close[i] > 0
    ) / max(min(19, len(close) - 1), 1)

    # Narrow range + big volume = accumulation (institutions buying quietly)
    range_ratio = today_range / avg_range if avg_range > 0 else 1
    is_quiet_accumulation = range_ratio < 0.8 and vol_ratio > 1.5

    score = 0.0
    reasons = []

    if price_change > 0:
        if vol_ratio >= 2.5:
            score += 0.5
            reasons.append(f"Volume surge {vol_ratio:.1f}x with +{price_change:.1f}%")
        elif vol_ratio >= 1.8:
            score += 0.35
            reasons.append(f"Strong volume {vol_ratio:.1f}x with +{price_change:.1f}%")
        elif vol_ratio >= 1.3:
            score += 0.2
            reasons.append(f"Above-avg volume {vol_ratio:.1f}x")

    if is_quiet_accumulation:
        score += 0.3
        reasons.append("Quiet accumulation (narrow range + big volume)")

    # Multi-day accumulation: 3+ of last 5 days had above-average volume
    if len(volume) >= 5:
        above_avg_days = sum(1 for v in volume[-5:] if v > avg_vol * 1.2)
        if above_avg_days >= 3:
            score += 0.2
            reasons.append(f"{above_avg_days}/5 days above-avg volume")

    reason = " | ".join(reasons) if reasons else "No accumulation signal"
    return min(1.0, score), reason


# ── Pattern 3: Seller Exhaustion ─────────────────────────────────
def _detect_seller_exhaustion(close, high, low, volume):
    """
    Stock dropped significantly, RSI oversold, reversal candle appears.
    """
    if len(close) < 30:
        return 0.0, "Insufficient data"

    rsi_val = _rsi(close)
    recent_high = max(close[-30:])
    drawdown = (close[-1] - recent_high) / recent_high * 100

    # Reversal candle: today's close > today's open AND near the high
    # Approximation: close near high of the day
    candle_body_pct = abs(close[-1] - close[-2]) / close[-2] * 100 if close[-2] else 0
    close_near_high = (high[-1] - close[-1]) / high[-1] * 100 if high[-1] else 5
    long_lower_wick = (min(close[-1], close[-2]) - low[-1]) / close[-1] * 100 if close[-1] else 0

    # Volume on reversal day should be above average
    avg_vol = sum(volume[-20:]) / max(len(volume[-20:]), 1)
    vol_ratio = volume[-1] / avg_vol if avg_vol > 0 else 1

    score = 0.0
    reasons = []

    # Need meaningful drawdown first
    if drawdown < -8:
        score += 0.2
        reasons.append(f"Down {drawdown:.1f}% from recent high")

        if rsi_val < 35:
            score += 0.3
            reasons.append(f"RSI oversold at {rsi_val:.0f}")
        elif rsi_val < 42:
            score += 0.15
            reasons.append(f"RSI approaching oversold at {rsi_val:.0f}")

        # Reversal candle: close near high + long lower wick
        if close_near_high < 1.0 and long_lower_wick > 1.0:
            score += 0.3
            reasons.append("Hammer/reversal candle detected")
        elif close[-1] > close[-2]:
            score += 0.1
            reasons.append("Green candle after decline")

        if vol_ratio > 1.3:
            score += 0.2
            reasons.append(f"Reversal on {vol_ratio:.1f}x volume")

    reason = " | ".join(reasons) if reasons else "No exhaustion signal"
    return min(1.0, score), reason


# ── Pattern 4: Breakout Retest ───────────────────────────────────
def _detect_breakout_retest(close, high, low):
    """
    Stock broke a resistance in last 5 days, pulled back to test it as support.
    """
    if len(close) < 30:
        return 0.0, "Insufficient data"

    sma50 = _sma(close, 50) if len(close) >= 50 else _sma(close, 20)

    # Find if there was a breakout in the last 5-10 days
    # Breakout = price crossed above the prior 20-day high
    prior_20d_high = max(high[-25:-5]) if len(high) >= 25 else max(high[:-5]) if len(high) > 5 else 0

    # Did price go above it in last 5 days?
    breakout_happened = any(h > prior_20d_high for h in high[-5:])

    # Is today's price pulling back near the breakout level?
    if prior_20d_high > 0:
        distance_from_breakout = (close[-1] - prior_20d_high) / prior_20d_high * 100
    else:
        distance_from_breakout = 999

    # Retest = price is within 2% above the old resistance (now support)
    is_retesting = 0 <= distance_from_breakout <= 3.0

    # Also check SMA50 bounce
    if sma50 > 0:
        distance_from_sma50 = abs(close[-1] - sma50) / sma50 * 100
    else:
        distance_from_sma50 = 999

    sma50_bounce = distance_from_sma50 < 1.5 and close[-1] >= sma50

    score = 0.0
    reasons = []

    if breakout_happened and is_retesting:
        score += 0.6
        reasons.append(f"Retesting breakout level ₹{prior_20d_high:.0f} (+{distance_from_breakout:.1f}%)")

        # Holding above = strong
        if close[-1] > prior_20d_high:
            score += 0.2
            reasons.append("Holding above breakout (support confirmed)")

        # Today's low didn't break the level
        if low[-1] >= prior_20d_high * 0.99:
            score += 0.2
            reasons.append("Low respected the breakout level")

    elif sma50_bounce:
        score += 0.4
        reasons.append(f"Bouncing off SMA50 (₹{sma50:.0f})")

        if close[-1] > close[-2]:
            score += 0.2
            reasons.append("Green candle on SMA50 touch")

    reason = " | ".join(reasons) if reasons else "No retest pattern"
    return min(1.0, score), reason


# ── Pattern 5: EMA Power Alignment ──────────────────────────────
def _detect_ema_power(close):
    """
    EMA9 > EMA20 > EMA50, price above EMA9, MACD just turned positive.
    """
    if len(close) < 55:
        return 0.0, "Insufficient data"

    ema9 = _ema(close, 9)
    ema20 = _ema(close, 20)
    ema50 = _ema(close, 50)
    price = close[-1]
    macd_h = _macd_hist(close)

    # Check previous MACD to detect fresh crossover
    prev_macd = _macd_hist(close[:-1])
    macd_just_crossed = prev_macd <= 0 and macd_h > 0

    score = 0.0
    reasons = []

    # EMA alignment
    if ema9 > ema20 > ema50:
        score += 0.4
        reasons.append("Perfect EMA stack: 9 > 20 > 50")
    elif ema9 > ema20:
        score += 0.2
        reasons.append("EMA9 > EMA20 (short-term bullish)")

    # Price above EMA9
    if price > ema9:
        score += 0.2
        reasons.append("Price above EMA9")

    # MACD crossover
    if macd_just_crossed:
        score += 0.3
        reasons.append("MACD histogram just turned positive (fresh momentum)")
    elif macd_h > 0:
        score += 0.1
        reasons.append("MACD positive")

    reason = " | ".join(reasons) if reasons else "EMAs not aligned"
    return min(1.0, score), reason


# ── Pattern 6: Sector Rotation Lag ───────────────────────────────
def _detect_sector_rotation(change_pct, sector, sector_performance):
    """
    Stock's sector is top performing but this stock is lagging.
    Laggers tend to catch up in 1-3 days.
    """
    if not sector or not sector_performance:
        return 0.0, "No sector data"

    # Rank sectors by performance
    sorted_sectors = sorted(sector_performance.items(), key=lambda x: x[1], reverse=True)
    if not sorted_sectors:
        return 0.0, "No sector ranking"

    # Find this stock's sector rank
    sector_rank = None
    sector_perf = 0
    for i, (sec, perf) in enumerate(sorted_sectors):
        if sec == sector:
            sector_rank = i + 1
            sector_perf = perf
            break

    if sector_rank is None:
        return 0.0, f"Sector '{sector}' not found in performance data"

    total_sectors = len(sorted_sectors)

    score = 0.0
    reasons = []

    # Sector is in top 3
    if sector_rank <= 3 and total_sectors >= 5:
        score += 0.4
        reasons.append(f"Sector '{sector}' ranked #{sector_rank} today (+{sector_perf:.1f}%)")

        # This stock is lagging its sector
        if change_pct < sector_perf * 0.5:
            score += 0.4
            lag = sector_perf - change_pct
            reasons.append(f"Stock lagging sector by {lag:.1f}% (catch-up potential)")
        elif change_pct < sector_perf:
            score += 0.2
            reasons.append("Slightly lagging sector peers")

    elif sector_rank <= 2 and total_sectors >= 3:
        score += 0.3
        reasons.append(f"Sector '{sector}' ranked #{sector_rank}")

    reason = " | ".join(reasons) if reasons else "Sector not in rotation"
    return min(1.0, score), reason


# ── Exit Level Calculator ────────────────────────────────────────
def _calculate_entry_exit(close, high, low, atr_val):
    """Calculate entry, stop loss, target levels for tomorrow's trade."""
    price = close[-1]
    if price <= 0:
        return None

    # Entry: at market open or limit slightly below today's close
    entry = round(price * 0.998, 2)  # 0.2% below close (limit order)

    # Stop loss: max of (today's low, 1.5 * ATR below entry)
    sl_atr = entry - (1.5 * atr_val)
    sl_day_low = min(low[-3:]) if len(low) >= 3 else low[-1]  # 3-day low
    stop_loss = max(sl_atr, sl_day_low)

    # Ensure SL is at least 1% below entry
    max_sl = entry * 0.99
    if stop_loss > max_sl:
        stop_loss = max_sl

    risk = entry - stop_loss

    # Target 1: 2x risk (R:R = 2:1)
    target_1 = entry + (2.0 * risk)

    # Target 2: 3x risk or recent swing high
    recent_swing_high = max(high[-20:]) if len(high) >= 20 else max(high[-10:])
    target_2 = max(entry + (3.0 * risk), recent_swing_high)

    rr_ratio = round((target_1 - entry) / risk, 2) if risk > 0 else 0

    sl_pct = round((entry - stop_loss) / entry * 100, 2)
    t1_pct = round((target_1 - entry) / entry * 100, 2)
    t2_pct = round((target_2 - entry) / entry * 100, 2)

    return {
        "entry": round(entry, 2),
        "stop_loss": round(stop_loss, 2),
        "stop_loss_pct": sl_pct,
        "target_1": round(target_1, 2),
        "target_1_pct": t1_pct,
        "target_2": round(target_2, 2),
        "target_2_pct": t2_pct,
        "risk_reward": rr_ratio,
        "risk_per_share": round(risk, 2),
    }


# ── Position Sizing ──────────────────────────────────────────────
def _position_size(entry, stop_loss, account_size=80000, max_risk_pct=1.0):
    """Conservative Kelly: risk max 1% of account per trade (25% Kelly)."""
    risk_per_share = entry - stop_loss
    if risk_per_share <= 0:
        return {"quantity": 0, "capital_required": 0, "risk_amount": 0}

    max_risk_amount = account_size * (max_risk_pct / 100)
    quantity = int(max_risk_amount / risk_per_share)
    capital = round(quantity * entry, 2)

    # Cap at 20% of account per position
    max_capital = account_size * 0.20
    if capital > max_capital:
        quantity = int(max_capital / entry)
        capital = round(quantity * entry, 2)

    return {
        "quantity": max(quantity, 1),
        "capital_required": capital,
        "risk_amount": round(quantity * risk_per_share, 2),
        "risk_pct_of_account": round((quantity * risk_per_share) / account_size * 100, 2),
    }


# ── Main Scanner ─────────────────────────────────────────────────
def scan_single_stock(ticker_symbol, sector_performance=None):
    """
    Run evening patterns on a single stock with pre-filters.
    Returns result dict if conviction >= WATCH_THRESHOLD, else None.
    """
    try:
        ticker = ticker_symbol if ticker_symbol.endswith(".NS") else f"{ticker_symbol}.NS"
        stock = yf.Ticker(ticker)
        info = stock.info or {}
        hist = stock.history(period="6mo")

        if hist.empty or len(hist) < 55:
            return None

        close = hist["Close"].tolist()
        high = hist["High"].tolist()
        low = hist["Low"].tolist()
        vol = hist["Volume"].tolist()
        price = close[-1]

        if price <= 0:
            return None

        # ── PRE-FILTERS (skip garbage early) ──────────────────────
        # 1. Liquidity filter: avg volume must be > 100k shares
        avg_vol_20 = sum(vol[-20:]) / max(len(vol[-20:]), 1)
        if avg_vol_20 < MIN_AVG_VOLUME:
            return None

        # 2. Trend filter: only trade stocks above SMA50 (with trend)
        sma50 = _sma(close, 50)
        if price < sma50:
            return None  # Don't catch falling knives

        # 3. Volatility filter: ATR% must be >= 1.5% (enough movement)
        atr_val = _atr(high, low, close)
        atr_pct = atr_val / price if price > 0 else 0
        if atr_pct < MIN_ATR_PCT:
            return None  # Too dead to profit from

        # 4. ADX filter: trend must be strong enough (ADX > 18)
        adx_val = _adx(high, low, close)
        if adx_val < 18:
            return None  # Choppy, patterns won't work

        sector = info.get("sector", "General")
        change_pct = ((close[-1] - close[-2]) / close[-2] * 100) if len(close) > 1 and close[-2] else 0

        # ── Run patterns (only the proven ones get real weight) ────
        p1_score, p1_reason = _detect_compression_breakout(close, high, low, vol)
        p2_score, p2_reason = _detect_volume_accumulation(close, vol, high, low)
        p3_score, p3_reason = _detect_seller_exhaustion(close, high, low, vol)
        p4_score, p4_reason = _detect_breakout_retest(close, high, low)
        p5_score, p5_reason = _detect_ema_power(close)

        # Weighted conviction — NO sector rotation (unused, 0 signals)
        # Weights from backtest: Vol Accum (40%), Compression (30%), Retest (15%), EMA (10%), Exhaustion (5%)
        conviction = (
            p2_score * PATTERN_WEIGHTS["volume_accumulation"]
            + p1_score * PATTERN_WEIGHTS["compression_breakout"]
            + p4_score * PATTERN_WEIGHTS["breakout_retest"]
            + p5_score * PATTERN_WEIGHTS["ema_power"]
            + p3_score * PATTERN_WEIGHTS["seller_exhaustion"]
        )

        if conviction < WATCH_THRESHOLD:
            return None

        # Conviction tier
        if conviction >= ROCKET_THRESHOLD:
            tier = "ROCKET"
        elif conviction >= STRONG_THRESHOLD:
            tier = "STRONG"
        else:
            tier = "WATCH"

        # Count patterns firing (score > 0.4)
        patterns_firing = sum(1 for s in [p1_score, p2_score, p3_score, p4_score, p5_score] if s >= 0.4)

        # Calculate entry/exit
        levels = _calculate_entry_exit(close, high, low, atr_val)
        if not levels or levels["risk_reward"] < MIN_RR_RATIO:
            if levels and levels["risk_reward"] < 1.5:
                return None

        # Position sizing
        sizing = _position_size(
            levels["entry"], levels["stop_loss"]
        ) if levels else {"quantity": 0, "capital_required": 0, "risk_amount": 0}

        # 52-week context
        high_52w = max(high) if high else price
        low_52w = min(low) if low else price
        pct_from_52w_high = round((price - high_52w) / high_52w * 100, 2)

        # RSI for display
        rsi_val = _rsi(close)

        return {
            "ticker": ticker_symbol.replace(".NS", ""),
            "name": info.get("shortName") or info.get("longName") or ticker_symbol,
            "price": round(price, 2),
            "change_pct": round(change_pct, 2),
            "sector": sector,
            "industry": info.get("industry", ""),
            "market_cap": info.get("marketCap", 0),
            "rsi": round(rsi_val, 1),
            "atr": round(atr_val, 2),
            "atr_pct": round(atr_val / price * 100, 2) if price else 0,
            "pct_from_52w_high": pct_from_52w_high,
            # Conviction
            "conviction_score": round(conviction, 3),
            "conviction_tier": tier,
            "patterns_firing": patterns_firing,
            # Pattern scores
            "patterns": [
                {"id": "compression_breakout", "name": "Compression Breakout", "score": round(p1_score, 2), "reason": p1_reason, "icon": "📊"},
                {"id": "volume_accumulation", "name": "Volume Accumulation", "score": round(p2_score, 2), "reason": p2_reason, "icon": "📈"},
                {"id": "seller_exhaustion", "name": "Seller Exhaustion", "score": round(p3_score, 2), "reason": p3_reason, "icon": "🔄"},
                {"id": "breakout_retest", "name": "Breakout Retest", "score": round(p4_score, 2), "reason": p4_reason, "icon": "🎯"},
                {"id": "ema_power", "name": "EMA Power Align", "score": round(p5_score, 2), "reason": p5_reason, "icon": "⚡"},
            ],
            # Trade plan
            "trade_plan": levels,
            "position_sizing": sizing,
            # Metadata
            "scanned_at": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S"),
        }

    except Exception as e:
        logger.error(f"Evening scan {ticker_symbol}: {e}")
        return None


def build_sector_performance(scan_results):
    """Build sector avg change from existing scan results."""
    sector_totals = {}
    sector_counts = {}
    for r in scan_results:
        sec = r.get("sector", "General")
        chg = r.get("change_pct", 0)
        sector_totals[sec] = sector_totals.get(sec, 0) + chg
        sector_counts[sec] = sector_counts.get(sec, 0) + 1

    return {
        sec: round(sector_totals[sec] / sector_counts[sec], 2)
        for sec in sector_totals
        if sector_counts[sec] > 0
    }


def run_evening_scan(tickers, existing_scan_results=None):
    """
    Run the full evening scan across a list of tickers.
    Returns sorted list of results (highest conviction first).
    """
    # Build sector performance from existing scan data if available
    sector_perf = {}
    if existing_scan_results:
        sector_perf = build_sector_performance(existing_scan_results)

    results = []
    for ticker in tickers:
        try:
            result = scan_single_stock(ticker, sector_perf)
            if result:
                results.append(result)
        except Exception as e:
            logger.error(f"Evening scan error {ticker}: {e}")

    # Sort by conviction score (highest first)
    results.sort(key=lambda x: x["conviction_score"], reverse=True)
    return results
