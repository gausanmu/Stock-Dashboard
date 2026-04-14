import json
import urllib.request
import urllib.error
import logging

logger = logging.getLogger(__name__)

class AnalysisEngine:
    def _safe(self, val, default=0.0):
        if val is None: return default
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

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
            url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1y"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
            
            result = data["chart"]["result"][0]
            meta = result["meta"]
            current_price = self._safe(meta.get("regularMarketPrice"))
            prev_close = self._safe(meta.get("previousClose"))
            change_pct = ((current_price - prev_close) / prev_close * 100) if prev_close else 0.0

            close_prices = result["indicators"]["quote"][0].get("close", [])
            close_prices = [p for p in close_prices if p is not None]
            
            if not close_prices: return None

            sma50 = self.calculate_sma(close_prices, 50)
            sma200 = self.calculate_sma(close_prices, 200)
            rsi = self.calculate_rsi(close_prices, 14)
            
            # Simple heuristic for volatility/quality
            vol_ratio = 1.2 if change_pct > 2 else 0.9
            quality_score = int(60 + min(change_pct * 5, 30))

            regime = self.classify_regime(current_price, sma50, sma200, rsi, vol_ratio, quality_score, profile)
            
            return {
                "ticker": ticker_symbol,
                "name": ticker_symbol,
                "price": round(current_price, 2),
                "change_pct": round(change_pct, 2),
                "sector": "NSE Component",
                "sma50": round(sma50, 2),
                "sma200": round(sma200, 2),
                "rsi": round(rsi, 2),
                "vol_ratio": round(vol_ratio, 2),
                "quality_score": max(10, min(100, quality_score)),
                "regime": regime
            }
        except Exception as e:
            logger.error(f"Error fetching {ticker_symbol}: {e}")
            return None