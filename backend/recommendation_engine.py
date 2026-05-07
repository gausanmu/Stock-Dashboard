"""Recommendation engine: given a stock's analysis dict + the user's buy_price
and chosen profile, return a recommended target price, stop loss, holding
period, action and rationale.

Profiles:
  LONG_TERM   : months → years   (target ~+25–60%, stop SMA200 break)
  SWING       : 3 days → 4 weeks (target ~+5–15%, stop 1.5×ATR)
  SHORT_TERM  : intraday → 2 days (target ~+1.5–3%, stop 0.5–1×ATR)
"""
from datetime import datetime, timedelta
from typing import Optional


def _safe(v, default=0.0):
    try:
        f = float(v)
        if f != f:  # NaN
            return default
        return f
    except (TypeError, ValueError):
        return default


def recommend(stock: dict, buy_price: float, profile: str = "LONG_TERM", buy_date: Optional[str] = None) -> dict:
    profile = (profile or "LONG_TERM").upper()
    price   = _safe(stock.get("price"), buy_price)
    sma50   = _safe(stock.get("sma50"), price)
    sma200  = _safe(stock.get("sma200"), price)
    rsi     = _safe(stock.get("rsi"), 50)
    atr     = _safe(stock.get("atr"), price * 0.02)
    quality = _safe(stock.get("quality_score"), 50)
    regime  = (stock.get("regime") or "NEUTRAL").upper()

    invested_pct = ((price - buy_price) / buy_price * 100) if buy_price > 0 else 0

    # ── PROFILE-SPECIFIC TARGETS & STOPS ───────────────────────────
    if profile == "SHORT_TERM":
        # Intraday-ish: 1.5–3% target, 0.5–1× ATR stop
        target_gain_pct = 2.0 if regime in ("SPRINTER", "BREAKOUT_LONG", "ORB_LONG") else 1.2
        stop_distance = max(atr * 0.8, price * 0.005)
        hold_min, hold_max, hold_unit = 1, 2, "days"
    elif profile == "SWING":
        # 5–15% target, 1.5× ATR stop
        if regime in ("SPRINTER", "BREAKOUT_LONG"):
            target_gain_pct = 12.0
        elif regime == "REVERSAL":
            target_gain_pct = 8.0
        else:
            target_gain_pct = 6.0
        stop_distance = max(atr * 1.5, price * 0.025)
        hold_min, hold_max, hold_unit = 5, 25, "days"
    else:  # LONG_TERM (default)
        # 25–60% target, stop = SMA200 break or 12% trail
        if regime in ("COMPOUNDER", "WEALTH_BUILDER"):
            target_gain_pct = 45.0
            hold_min, hold_max, hold_unit = 12, 36, "months"
        elif regime == "SPRINTER":
            target_gain_pct = 30.0
            hold_min, hold_max, hold_unit = 6, 18, "months"
        else:
            target_gain_pct = 20.0
            hold_min, hold_max, hold_unit = 6, 12, "months"
        stop_distance = max(price - sma200, price * 0.12)

    # ── Compute target & stop based on entry (buy_price) ──────────
    target_price = round(buy_price * (1 + target_gain_pct / 100), 2)
    stop_price   = round(max(buy_price - stop_distance, buy_price * 0.5), 2)
    upside_pct   = round((target_price - price) / price * 100, 2) if price > 0 else 0
    downside_pct = round((stop_price - price) / price * 100, 2) if price > 0 else 0
    risk_reward  = round(abs(target_price - price) / max(abs(price - stop_price), 0.01), 2)

    # ── Action decision ───────────────────────────────────────────
    action = "HOLD"
    rationale = []

    if price <= stop_price:
        action = "SELL"
        rationale.append(f"Price ₹{price} hit stop-loss ₹{stop_price}.")
    elif price >= target_price:
        action = "BOOK_PROFIT"
        rationale.append(f"Target ₹{target_price} reached (+{round(invested_pct,1)}%).")
    elif profile == "LONG_TERM":
        if regime in ("COMPOUNDER", "WEALTH_BUILDER") and quality >= 60:
            action = "HOLD" if invested_pct < target_gain_pct * 0.8 else "PARTIAL_BOOK"
            rationale.append(f"Strong fundamentals (Q={int(quality)}) and {regime} regime.")
        elif regime == "AVOID" or quality < 45:
            action = "EXIT"
            rationale.append(f"Quality dropped to {int(quality)} / regime={regime}. Reduce exposure.")
        elif rsi > 75:
            action = "PARTIAL_BOOK"
            rationale.append(f"RSI={int(rsi)} overheated — book some profits.")
        else:
            rationale.append(f"Trend intact (price > SMA200={sma200}). Continue holding.")
    elif profile == "SWING":
        if rsi > 70:
            action = "BOOK_PROFIT"
            rationale.append(f"RSI={int(rsi)} overbought — exit swing.")
        elif regime in ("SPRINTER", "BREAKOUT_LONG"):
            action = "HOLD"
            rationale.append(f"Momentum intact, target {target_price}, R:R={risk_reward}.")
        elif rsi < 35 and price > sma50:
            action = "ADD"
            rationale.append(f"Pullback to support, RSI={int(rsi)} — add on strength.")
        else:
            rationale.append(f"Hold; respect stop ₹{stop_price}.")
    else:  # SHORT_TERM
        if rsi > 70:
            action = "BOOK_PROFIT"
            rationale.append("RSI overbought intraday.")
        elif rsi < 40:
            action = "EXIT"
            rationale.append("Intraday momentum lost.")
        else:
            rationale.append("Trail stop near VWAP / day-low.")

    # ── Days held ─────────────────────────────────────────────────
    days_held = None
    if buy_date:
        try:
            d = datetime.fromisoformat(buy_date.replace("Z", ""))
            days_held = max(0, (datetime.utcnow() - d).days)
        except Exception:
            days_held = None

    holding_label = f"{hold_min}–{hold_max} {hold_unit}"
    if days_held is not None:
        holding_label = f"Held {days_held}d  •  Target window: {hold_min}–{hold_max} {hold_unit}"

    return {
        "profile": profile,
        "target_price": target_price,
        "target_gain_pct": round(target_gain_pct, 2),
        "stop_price": stop_price,
        "upside_pct_from_now": upside_pct,
        "downside_pct_from_now": downside_pct,
        "risk_reward": risk_reward,
        "holding_period": holding_label,
        "hold_min": hold_min,
        "hold_max": hold_max,
        "hold_unit": hold_unit,
        "days_held": days_held,
        "action": action,
        "rationale": " ".join(rationale) if rationale else "Continue monitoring.",
        "current_price": price,
        "buy_price": buy_price,
        "unrealized_pct": round(invested_pct, 2),
    }
