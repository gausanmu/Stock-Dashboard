import json
import urllib.request
import urllib.error
import logging
import yfinance as yf
import numpy as pd

logger = logging.getLogger(__name__)

class AnalysisEngine:
    def _safe(self, val, default=0.0):
        if val is None: return default
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

    def calculate_atr(self, h, l, c, period=14):
        if len(c) < period: return 1.0
        tr_list = []
        for i in range(1, len(c)):
            tr = max(h[i] - l[i], abs(h[i] - c[i-1]), abs(l[i] - c[i-1]))
            tr_list.append(tr)
        return sum(tr_list[-period:]) / period if tr_list else 1.0

    def calculate_rsi(self, prices, period=14):
        if len(prices) < period + 1: return 50.0
        gains, losses = [], []
        for i in range(1, len(prices)):
            delta = prices[i] - prices[i-1]
            gains.append(max(0, delta))
            losses.append(max(0, -delta))
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        if avg_loss == 0: return 100
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def calculate_sma(self, prices, period):
        if len(prices) < period: return prices[-1] if prices else 0
        return sum(prices[-period:]) / period

    def classify_regime(self, price, sma50, sma200, rsi, vol_ratio, quality, profile="INVESTOR"):
        if quality < 50: return "AVOID"
        if price > sma200 and quality > 60: return "COMPOUNDER"
        if price > sma50 and rsi > 55: return "SPRINTER"
        if rsi < 40: return "REVERSAL"
        return "NEUTRAL"

    def analyze_stock(self, ticker_symbol, profile="INVESTOR"):
        try:
            ticker = ticker_symbol if ticker_symbol.endswith(".NS") else f"{ticker_symbol}.NS"
            
            # Fetch real fundamental data using yfinance
            stock = yf.Ticker(ticker)
            info = stock.info
            hist = stock.history(period="1y")
            
            if hist.empty: return None

            current_price = hist['Close'].iloc[-1]
            prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
            change_pct = ((current_price - prev_close) / prev_close * 100)
            
            close_prices = hist['Close'].tolist()
            high_prices = hist['High'].tolist()
            low_prices = hist['Low'].tolist()

            sma50 = self.calculate_sma(close_prices, 50)
            sma200 = self.calculate_sma(close_prices, 200)
            rsi = self.calculate_rsi(close_prices, 14)
            atr = self.calculate_atr(high_prices, low_prices, close_prices, 14)
            
            # Real volatility ratio (ATR % of Price) vs normal
            avg_volatility = (atr / current_price) if current_price > 0 else 0.05
            vol_ratio = avg_volatility * 100 # percentage

            # Real Fundamental Scoring
            roe = info.get("returnOnEquity", 0) or 0
            debt_to_eq = info.get("debtToEquity", 100) or 100
            margins = info.get("profitMargins", 0) or 0
            
            q_score = 0
            if roe > 0.15: q_score += 30
            elif roe > 0.05: q_score += 15
            
            if debt_to_eq < 50: q_score += 30
            elif debt_to_eq < 100: q_score += 15
            
            if margins > 0.10: q_score += 20
            elif margins > 0.05: q_score += 10
            
            if q_score == 0: # Fallback if missing data
                q_score = int(50 + min(change_pct * 5, 20))

            regime = self.classify_regime(current_price, sma50, sma200, rsi, vol_ratio, q_score, profile)
            
            # Additional UI Elements Logic
            trade_types = []
            if regime == "SPRINTER": trade_types.append("MOMENTUM")
            elif regime == "COMPOUNDER": trade_types.append("CORE")
            elif regime == "REVERSAL": trade_types.append("SWING")
            
            gsq_tag = "STAYER"
            if rsi > 75: gsq_tag = "QUITTER"
            elif rsi < 35: gsq_tag = "GAINER"
            
            target_pct = 20.0 if regime == "COMPOUNDER" else (8.0 if regime in ["SPRINTER", "REVERSAL"] else 0.0)
            
            return {
                "ticker": ticker_symbol,
                "name": info.get("shortName", ticker_symbol),
                "price": round(current_price, 2),
                "change_pct": round(change_pct, 2),
                "sector": info.get("sector", "NSE Component"),
                "sma50": round(sma50, 2),
                "sma200": round(sma200, 2),
                "rsi": round(rsi, 2),
                "atr": round(atr, 2),
                "vol_ratio": round(vol_ratio, 2),
                "quality_score": q_score,
                "regime": regime,
                "trade_types": trade_types,
                "gsq_tag": gsq_tag,
                "target_pct": target_pct
            }
        except Exception as e:
            logger.error(f"Error fetching {ticker_symbol}: {e}")
            return None