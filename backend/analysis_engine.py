import logging
import yfinance as yf

logger = logging.getLogger(__name__)

REGIME_THRESHOLDS = {
    'STRONG_BUY': 0.75,   # All components highly aligned
    'BUY': 0.60,          # Majority positive
    'NEUTRAL': 0.40,      # Mixed signals
    'SELL': 0.25,         # Majority negative
    'NO_TRADE': 0.40      # Too weak to act
}

# ── Indicator helpers ────────────────────────────────────────────
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


def _macd(prices):
    if len(prices) < 35:
        return 0.0, 0.0, 0.0
    ema12 = _ema(prices, 12)
    ema26 = _ema(prices, 26)
    macd_line = ema12 - ema26
    # crude signal line: 9-period EMA of last few macd points
    macd_series = []
    for i in range(26, len(prices) + 1):
        macd_series.append(_ema(prices[:i], 12) - _ema(prices[:i], 26))
    signal = _ema(macd_series[-9:], 9) if len(macd_series) >= 9 else macd_line
    return macd_line, signal, macd_line - signal


def _bollinger(prices, period=20, std=2):
    if len(prices) < period:
        m = prices[-1] if prices else 0
        return m, m, m
    recent = prices[-period:]
    mean = sum(recent) / period
    var = sum((p - mean) ** 2 for p in recent) / period
    sd = var ** 0.5
    return mean + std * sd, mean, mean - std * sd


def _adx(h, l, c, period=14):
    """Simplified ADX (trend strength 0-100)."""
    if len(c) < period * 2:
        return 20.0
    plus_dm, minus_dm, tr_list = [], [], []
    for i in range(1, len(c)):
        up = h[i] - h[i - 1]
        dn = l[i - 1] - l[i]
        plus_dm.append(up if up > dn and up > 0 else 0)
        minus_dm.append(dn if dn > up and dn > 0 else 0)
        tr = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
        tr_list.append(tr)
    atr_v = sum(tr_list[-period:]) / period or 1
    pdi = 100 * (sum(plus_dm[-period:]) / period) / atr_v
    mdi = 100 * (sum(minus_dm[-period:]) / period) / atr_v
    dx = 100 * abs(pdi - mdi) / (pdi + mdi) if (pdi + mdi) > 0 else 20
    return dx


# ── Profile-specific regime classifiers ──────────────────────────
def _calculate_trend_score(price, sma50, sma200, ema20, ema50):
    score = 0.0
    if price > sma200: score += 0.4
    if price > sma50: score += 0.3
    if ema20 > ema50: score += 0.3
    elif ema20 < ema50: score -= 0.2
    return max(0.0, min(1.0, score))

def _calculate_momentum_score(rsi, macd_hist):
    score = 0.0
    if 50 < rsi < 70: score += 0.6
    elif rsi >= 70: score += 0.3  # Overbought but strong
    elif 30 < rsi <= 50: score += 0.2
    if macd_hist > 0: score += 0.4
    return max(0.0, min(1.0, score))

def _calculate_volatility_score(adx, price, bb_upper, bb_lower):
    score = 0.0
    if adx > 20: score += 0.5
    if adx > 25: score += 0.2
    # Position in range
    range_size = bb_upper - bb_lower
    if range_size > 0:
        pos = (price - bb_lower) / range_size
        if 0.5 < pos < 0.9: score += 0.3  # Trending up but not hitting upper band
        elif pos >= 0.9: score += 0.1     # Near breakout
    return max(0.0, min(1.0, score))

def _classify_long_term(price, sma50, sma200, ema20, ema50, rsi, macd_hist, adx, bb_upper, bb_lower, quality, debt_eq, div_yield, weights):
    trend = _calculate_trend_score(price, sma50, sma200, ema20, ema50)
    mom = _calculate_momentum_score(rsi, macd_hist)
    vol = _calculate_volatility_score(adx, price, bb_upper, bb_lower)
    
    total_score = (trend * weights['trend']) + (mom * weights['momentum']) + (vol * weights['volatility'])
    
    if quality < 45 or total_score < REGIME_THRESHOLDS['SELL']:
        return "AVOID"
    
    if total_score >= REGIME_THRESHOLDS['BUY']:
        if quality >= 70 and debt_eq < 60:
            return "WEALTH_BUILDER"
        if div_yield and div_yield >= 2.5 and quality >= 60:
            return "DIVIDEND_KING"
        if quality >= 60:
            return "COMPOUNDER"
            
    if price < sma200 * 0.85 and quality >= 60 and rsi < 40:
        return "VALUE_PICK"
        
    return "NEUTRAL"


def _classify_swing(price, sma50, sma200, ema20, ema50, rsi, macd_hist, adx, bb_upper, bb_lower, weights):
    trend = _calculate_trend_score(price, sma50, sma200, ema20, ema50)
    mom = _calculate_momentum_score(rsi, macd_hist)
    vol = _calculate_volatility_score(adx, price, bb_upper, bb_lower)
    
    total_score = (trend * weights['trend']) + (mom * weights['momentum']) + (vol * weights['volatility'])
    
    if total_score < REGIME_THRESHOLDS['NO_TRADE']:
        return "RANGE_BOUND" if adx < 20 else "NO_TRADE"
        
    if total_score >= REGIME_THRESHOLDS['BUY']:
        if price > bb_upper and rsi > 55:
            return "BREAKOUT_LONG"
        return "EMA_TREND_LONG"
        
    if price < bb_lower and rsi < 35:
        return "MEAN_REVERSION_LONG"
        
    if total_score < REGIME_THRESHOLDS['SELL'] and ema20 < ema50:
        return "SWING_SHORT"
        
    return "NO_TRADE"


def _classify_short_term(price, ema9, ema20, rsi, vwap, atr_pct, macd_hist, adx, bb_upper, bb_lower, weights):
    trend = _calculate_trend_score(price, price, price, ema9, ema20) # Use short term EMAs for trend
    mom = _calculate_momentum_score(rsi, macd_hist)
    vol = _calculate_volatility_score(adx, price, bb_upper, bb_lower)
    
    total_score = (trend * weights['trend']) + (mom * weights['momentum']) + (vol * weights['volatility'])
    
    if atr_pct < 0.6 or total_score < REGIME_THRESHOLDS['NO_TRADE']:
        return "FLAT"
        
    if total_score >= REGIME_THRESHOLDS['BUY'] and price > vwap:
        return "INTRADAY_LONG"
        
    if total_score <= REGIME_THRESHOLDS['SELL'] and price < vwap:
        return "INTRADAY_SHORT"
        
    return "FLAT"


# ── Main engine ──────────────────────────────────────────────────
class AnalysisEngine:
    def __init__(self, weights=None):
        self.weights = weights or {'trend': 0.50, 'momentum': 0.30, 'volatility': 0.20}

    def analyze_stock(self, ticker_symbol, profile="LONG_TERM"):
        try:
            ticker = ticker_symbol if ticker_symbol.endswith(".NS") else f"{ticker_symbol}.NS"
            stock = yf.Ticker(ticker)
            info = stock.info or {}
            hist = stock.history(period="1y")
            if hist.empty:
                return None

            current_price = float(hist["Close"].iloc[-1])
            prev_close = float(hist["Close"].iloc[-2]) if len(hist) > 1 else current_price
            change_pct = ((current_price - prev_close) / prev_close * 100) if prev_close else 0

            close = hist["Close"].tolist()
            high = hist["High"].tolist()
            low = hist["Low"].tolist()
            vol = hist["Volume"].tolist()

            sma50 = _sma(close, 50)
            sma200 = _sma(close, 200)
            ema9 = _ema(close, 9)
            ema20 = _ema(close, 20)
            ema50 = _ema(close, 50)
            rsi = _rsi(close, 14)
            atr = _atr(high, low, close, 14)
            atr_pct = (atr / current_price * 100) if current_price else 0
            macd_line, macd_signal, macd_hist = _macd(close)
            bb_upper, bb_mid, bb_lower = _bollinger(close, 20, 2)
            adx = _adx(high, low, close, 14)

            # 20-day VWAP proxy (typical_price * volume) / sum(volume)
            typical = [(high[i] + low[i] + close[i]) / 3 for i in range(len(close))]
            recent_n = min(20, len(close))
            tv = sum(typical[i] * vol[i] for i in range(len(close) - recent_n, len(close)))
            sv = sum(vol[-recent_n:]) or 1
            vwap = tv / sv

            # Volume ratio
            avg_vol = sum(vol[-20:]) / max(len(vol[-20:]), 1) if vol else 1
            vol_ratio = (vol[-1] / avg_vol) if avg_vol else 1

            # Fundamentals
            pe = info.get("trailingPE") or 0
            pb = info.get("priceToBook") or 0
            roe = (info.get("returnOnEquity") or 0) * 100
            debt_eq = info.get("debtToEquity") or 0
            margins = (info.get("profitMargins") or 0) * 100
            div_yield = (info.get("dividendYield") or 0) * 100
            eps_growth = (info.get("earningsGrowth") or 0) * 100
            rev_growth = (info.get("revenueGrowth") or 0) * 100
            mcap = info.get("marketCap") or 0

            # Quality score
            q = 0
            if roe > 15: q += 30
            elif roe > 5: q += 15
            if 0 < debt_eq < 50: q += 25
            elif debt_eq < 100: q += 12
            if margins > 10: q += 20
            elif margins > 5: q += 10
            if eps_growth > 15: q += 15
            elif eps_growth > 5: q += 7
            if rev_growth > 10: q += 10
            elif rev_growth > 0: q += 5
            if q == 0:
                q = int(50 + min(change_pct * 5, 20))

            # 52-week high / low
            high_52w = max(high[-252:]) if len(high) >= 50 else max(high)
            low_52w = min(low[-252:]) if len(low) >= 50 else min(low)
            pct_from_52w_high = round((current_price - high_52w) / high_52w * 100, 2)
            pct_from_52w_low = round((current_price - low_52w) / low_52w * 100, 2)

            # Profile-specific regime
            profile = (profile or "LONG_TERM").upper()
            if profile == "SWING":
                regime = _classify_swing(current_price, sma50, sma200, ema20, ema50, rsi,
                                         macd_hist, adx, bb_upper, bb_lower, self.weights)
            elif profile == "SHORT_TERM":
                regime = _classify_short_term(current_price, ema9, ema20, rsi, vwap, atr_pct,
                                              macd_hist, adx, bb_upper, bb_lower, self.weights)
            else:
                regime = _classify_long_term(current_price, sma50, sma200, ema20, ema50, rsi,
                                             macd_hist, adx, bb_upper, bb_lower, q, debt_eq, div_yield, self.weights)

            # Trade types & tags
            trade_types = []
            if regime in ("WEALTH_BUILDER", "COMPOUNDER", "DIVIDEND_KING"):
                trade_types.append("CORE")
            if regime in ("BREAKOUT_LONG", "EMA_TREND_LONG", "SPRINTER"):
                trade_types.append("MOMENTUM")
            if regime in ("MEAN_REVERSION_LONG", "VALUE_PICK", "REVERSAL"):
                trade_types.append("SWING")
            if regime in ("INTRADAY_LONG", "INTRADAY_SHORT"):
                trade_types.append("INTRADAY")

            gsq_tag = "STAYER"
            if rsi > 75: gsq_tag = "QUITTER"
            elif rsi < 35: gsq_tag = "GAINER"

            # Setups detected
            setups = []
            if pct_from_52w_high > -2 and macd_hist > 0:
                setups.append("52W_HIGH_BREAKOUT")
            if abs(current_price - ema20) / current_price < 0.015 and ema20 > ema50:
                setups.append("EMA20_BOUNCE")
            if current_price < bb_lower and rsi < 35:
                setups.append("OVERSOLD_BOUNCE")
            if vol_ratio > 1.8:
                setups.append("VOLUME_SPIKE")
            if macd_hist > 0 and rsi > 50 and rsi < 65:
                setups.append("MACD_BULLISH")

            # Default target % per profile
            if profile == "SHORT_TERM":
                target_pct = 2.0
            elif profile == "SWING":
                target_pct = 10.0 if regime in ("BREAKOUT_LONG", "EMA_TREND_LONG") else 6.0
            else:
                target_pct = 30.0 if regime in ("WEALTH_BUILDER", "COMPOUNDER") else 15.0

            return {
                "ticker": ticker_symbol.replace(".NS", ""),
                "name": info.get("shortName") or info.get("longName") or ticker_symbol,
                "price": round(current_price, 2),
                "change_pct": round(change_pct, 2),
                "sector": info.get("sector", "General"),
                "industry": info.get("industry", ""),
                "market_cap": mcap,
                # Trend
                "sma50": round(sma50, 2),
                "sma200": round(sma200, 2),
                "ema9": round(ema9, 2),
                "ema20": round(ema20, 2),
                "ema50": round(ema50, 2),
                # Momentum
                "rsi": round(rsi, 2),
                "macd": round(macd_line, 3),
                "macd_signal": round(macd_signal, 3),
                "macd_hist": round(macd_hist, 3),
                "adx": round(adx, 2),
                # Volatility
                "atr": round(atr, 2),
                "atr_pct": round(atr_pct, 2),
                "vol_ratio": round(vol_ratio, 2),
                "bb_upper": round(bb_upper, 2),
                "bb_mid": round(bb_mid, 2),
                "bb_lower": round(bb_lower, 2),
                "vwap": round(vwap, 2),
                # Range
                "high_52w": round(high_52w, 2),
                "low_52w": round(low_52w, 2),
                "pct_from_52w_high": pct_from_52w_high,
                "pct_from_52w_low": pct_from_52w_low,
                # Fundamentals
                "pe": round(pe, 2) if pe else None,
                "pb": round(pb, 2) if pb else None,
                "roe": round(roe, 2),
                "debt_to_equity": round(debt_eq, 2),
                "profit_margin": round(margins, 2),
                "dividend_yield": round(div_yield, 2),
                "eps_growth": round(eps_growth, 2),
                "revenue_growth": round(rev_growth, 2),
                # Verdict
                "quality_score": int(q),
                "regime": regime,
                "profile": profile,
                "trade_types": trade_types,
                "gsq_tag": gsq_tag,
                "setups": setups,
                "target_pct": target_pct,
            }
        except Exception as e:
            logger.error(f"Error fetching {ticker_symbol}: {e}")
            return None
