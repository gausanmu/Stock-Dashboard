from fastapi import FastAPI, APIRouter, Request, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
from pydantic import BaseModel
from typing import Optional, List
import threading
import time
import asyncio
from datetime import datetime

from analysis_engine import AnalysisEngine
from nse_universe import get_tickers, get_scan_info
from news_sentiment import NewsSentimentEngine
from alert_service import AlertService
from risk_manager import RiskManager

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory stores ──────────────────────────────────────────────
stocks_db = {}          # ticker -> stock data dict
watchlist_db = {}       # ticker -> { ticker, tag, added_at }
portfolio_db = {}       # ticker -> { ticker, buy_price, quantity, tag }
regime_changes_db = []  # list of { ticker, name, old_regime, new_regime, timestamp }
scan_state = {"running": False, "progress": 0, "total": 0, "current_ticker": "", "last_updated": None}
alert_settings = {"email": "", "enabled": False}

engine = AnalysisEngine()
news_engine = NewsSentimentEngine()
alert_service = AlertService()
risk_mgr = RiskManager(account_size=50000.0)


# ── Pydantic models ──────────────────────────────────────────────
class ScanRequest(BaseModel):
    universe: str = "nifty50"
    profile: str = "INVESTOR"

class WatchlistItem(BaseModel):
    ticker: str
    tag: str = "STAYER"

class PortfolioItem(BaseModel):
    ticker: str
    buy_price: float
    quantity: int = 1
    tag: str = "STAYER"

class AlertSettings(BaseModel):
    email: str = ""
    enabled: bool = False


# ── Request logger ────────────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Incoming: {request.method} {request.url.path}")
    response = await call_next(request)
    return response


# ── Background scan worker ────────────────────────────────────────
def run_scan_worker(tickers, profile):
    global scan_state, stocks_db, regime_changes_db
    scan_state["running"] = True
    scan_state["total"] = len(tickers)
    scan_state["progress"] = 0

    for i, ticker in enumerate(tickers):
        if not scan_state["running"]:
            break
        scan_state["current_ticker"] = ticker
        scan_state["progress"] = i + 1

        try:
            result = engine.analyze_stock(ticker, profile)
            if result:
                old_regime = stocks_db.get(ticker, {}).get("regime")
                # Enrich with extra fields the frontend expects
                result["sector"] = result.get("sector", "General")
                result["change_pct"] = result.get("change_pct", 0)
                result["sma50"] = result.get("sma50", 0)
                result["sma200"] = result.get("sma200", 0)
                result["rsi"] = result.get("rsi", 50)
                result["vol_ratio"] = result.get("vol_ratio", 1.0)
                result["trade_types"] = result.get("trade_types", [])
                stocks_db[ticker] = result

                # Track regime changes
                if old_regime and old_regime != result["regime"]:
                    regime_changes_db.insert(0, {
                        "ticker": ticker,
                        "name": result.get("name", ticker),
                        "old_regime": old_regime,
                        "new_regime": result["regime"],
                        "timestamp": datetime.now().isoformat(),
                    })
            logger.info(f"[{i+1}/{len(tickers)}] {ticker}: {result['regime'] if result else 'SKIP'}")
        except Exception as e:
            logger.error(f"Error scanning {ticker}: {e}")

        # Small delay to avoid rate-limiting by yfinance
        time.sleep(1.2)

    scan_state["running"] = False
    scan_state["current_ticker"] = ""
    scan_state["last_updated"] = datetime.now().isoformat()
    logger.info("Scan complete.")


# ── SCAN endpoints ────────────────────────────────────────────────
@app.post("/api/scan/start")
async def start_scan(request: ScanRequest):
    if scan_state["running"]:
        raise HTTPException(status_code=400, detail="A scan is already running")
    tickers = get_tickers(request.universe)
    thread = threading.Thread(target=run_scan_worker, args=(tickers, request.profile), daemon=True)
    thread.start()
    return {"status": "started", "total": len(tickers)}


@app.get("/api/scan/status")
async def get_scan_status():
    return scan_state


@app.get("/api/scan/levels")
async def get_scan_levels():
    return get_scan_info()


# ── STOCKS endpoints ──────────────────────────────────────────────
@app.get("/api/stocks")
async def get_stocks(regime: Optional[str] = None, sort: Optional[str] = None):
    result = list(stocks_db.values())
    if regime:
        result = [s for s in result if s.get("regime") == regime.upper()]
    if sort == "quality":
        result.sort(key=lambda s: s.get("quality_score", 0), reverse=True)
    return result


@app.get("/api/stocks/search")
async def search_stocks(q: str = ""):
    if not q:
        return []
    q_lower = q.lower()
    return [s for s in stocks_db.values()
            if q_lower in s.get("ticker", "").lower()
            or q_lower in s.get("name", "").lower()
            or q_lower in s.get("sector", "").lower()]


@app.get("/api/stocks/{ticker}")
async def get_stock_detail(ticker: str):
    t = ticker.upper()
    if t not in stocks_db:
        # Try to scan it on the fly!
        result = engine.analyze_stock(t)
        if result:
            result["sector"] = result.get("sector", "General")
            result["change_pct"] = result.get("change_pct", 0)
            stocks_db[t] = result
        else:
            raise HTTPException(status_code=404, detail="Stock not found or invalid ticker.")

    if t in stocks_db:
        data = stocks_db[t].copy()
        
        # Inject Advanced Risk Metrics dynamically
        portfolio_tickers = list(portfolio_db.keys())
        corr_data = risk_mgr.check_correlation(t, portfolio_tickers)
        data["correlation_warning"] = corr_data
        
        # Recommend position size
        size_data = risk_mgr.position_sizing_kelly(
            win_rate=0.55, 
            win_loss_ratio=2.0, 
            current_price=data["price"], 
            stop_loss_price=data["price"] * 0.90 # Default 10% stop loss
        )
        data["position_sizing"] = size_data
        
        return data
        
    raise HTTPException(status_code=404, detail="Stock not found. Run a scan first.")


@app.get("/api/stocks/{ticker}/history")
async def get_stock_history(ticker: str, period: str = "6mo"):
    try:
        import yfinance as yf
        symbol = ticker if ticker.endswith(".NS") else f"{ticker}.NS"
        hist = yf.Ticker(symbol).history(period=period)
        if hist.empty:
            return []
        records = []
        for date, row in hist.iterrows():
            records.append({
                "date": date.strftime("%Y-%m-%d"),
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "close": round(float(row["Close"]), 2),
                "volume": int(row["Volume"]),
            })
        return records
    except Exception as e:
        logger.error(f"History error for {ticker}: {e}")
        return []


@app.get("/api/stocks/regimes")
async def get_stock_regimes():
    regimes = {}
    for s in stocks_db.values():
        r = s.get("regime", "NEUTRAL")
        regimes.setdefault(r, []).append(s)
    return regimes


# ── MARKET / MACRO endpoints ─────────────────────────────────────
@app.get("/api/market/macro")
async def get_macro():
    import yfinance as yf
    try:
        tickers = yf.download(["^NSEI", "^NSEBANK"], period="5d")['Close']
        nifty = tickers["^NSEI"]
        bank = tickers["^NSEBANK"]
        
        n_price = nifty.iloc[-1]
        n_prev = nifty.iloc[-2]
        n_chg = ((n_price - n_prev) / n_prev) * 100

        b_price = bank.iloc[-1]
        b_prev = bank.iloc[-2]
        b_chg = ((b_price - b_prev) / b_prev) * 100

        return {
            "NIFTY50": {"price": round(n_price, 2), "change_pct": round(n_chg, 2)},
            "BANKNIFTY": {"price": round(b_price, 2), "change_pct": round(b_chg, 2)}
        }
    except:
        return {
            "NIFTY50": {"price": 22500.0, "change_pct": 0.5},
            "BANKNIFTY": {"price": 48000.0, "change_pct": -0.2}
        }


@app.get("/api/market/confidence")
async def get_confidence():
    total = len(stocks_db)
    if total == 0:
        return {"score": 50, "status": "CAUTIOUS", "macro": {}}

    sprinters = sum(1 for s in stocks_db.values() if s.get("regime") == "SPRINTER")
    compounders = sum(1 for s in stocks_db.values() if s.get("regime") == "COMPOUNDER")
    avoids = sum(1 for s in stocks_db.values() if s.get("regime") == "AVOID")

    score = min(100, int(((sprinters + compounders) / total) * 100))
    if avoids > total * 0.5:
        status = "BEARISH"
    elif score > 60:
        status = "BULLISH"
    elif score > 30:
        status = "CAUTIOUS"
    else:
        status = "BEARISH"

    return {
        "score": score,
        "status": status,
        "macro": {
            "total_stocks": total,
            "sprinters": sprinters,
            "compounders": compounders,
            "avoids": avoids,
        }
    }


# ── WATCHLIST endpoints ───────────────────────────────────────────
@app.get("/api/watchlist")
async def get_watchlist():
    result = []
    for ticker, wl in watchlist_db.items():
        entry = dict(wl)
        entry["stock_data"] = stocks_db.get(ticker, {})
        result.append(entry)
    return result


@app.post("/api/watchlist")
async def add_to_watchlist(item: WatchlistItem):
    t = item.ticker.upper()
    if t in watchlist_db:
        raise HTTPException(status_code=400, detail=f"{t} already in watchlist")
    watchlist_db[t] = {"ticker": t, "tag": item.tag, "added_at": datetime.now().isoformat()}
    return {"status": "added", "ticker": t}


@app.delete("/api/watchlist/{ticker}")
async def remove_from_watchlist(ticker: str):
    t = ticker.upper()
    if t in watchlist_db:
        del watchlist_db[t]
        return {"status": "removed"}
    raise HTTPException(status_code=404, detail="Not in watchlist")


@app.put("/api/watchlist/{ticker}/tag")
async def update_watchlist_tag(ticker: str, tag: str = "STAYER"):
    t = ticker.upper()
    if t in watchlist_db:
        watchlist_db[t]["tag"] = tag
        return {"status": "updated"}
    raise HTTPException(status_code=404, detail="Not in watchlist")


# ── PORTFOLIO endpoints ──────────────────────────────────────────

def _recommend_action(buy_price, current_price, pnl_pct, stock_data):
    """
    Returns (action, reason) tuple for a portfolio holding.
    Rules (evaluated top-to-bottom, first match wins):
      1. Stop-loss hit: P&L <= -10%           -> SELL  "Stop Loss Hit (-10%)"
      2. Regime = AVOID                       -> SELL  "Weak Trend / Avoid Regime"
      3. Target reached (Compounder >= +20%)  -> SELL  "Target Reached"
      4. Target reached (Sprinter >= +15%)    -> SELL  "Momentum Target Hit"
      5. RSI > 80 (heavily overbought)        -> SELL  "Overbought (RSI > 80)"
      6. Sprinter + up > 5%                   -> ADD   "Momentum – Pyramid Into Strength"
      7. Compounder + up > 3%                 -> HOLD  "Compounding – Stay The Course"
      8. Default                              -> HOLD  "Trend Intact"
    """
    regime = stock_data.get("regime", "NEUTRAL")
    rsi = stock_data.get("rsi", 50)
    quality = stock_data.get("quality_score", 50)
    target_pct = stock_data.get("target_pct", 0)

    # 1. Hard stop-loss
    if pnl_pct <= -10:
        return "SELL", "Stop Loss Hit (-10%)"

    # 2. Regime collapse
    if regime == "AVOID":
        return "SELL", "Weak Trend / Avoid Regime"

    # 3. Target reached – Compounder
    if regime == "COMPOUNDER" and pnl_pct >= 20:
        return "SELL", "Target Reached (+20%)"

    # 4. Target reached – Sprinter
    if regime == "SPRINTER" and pnl_pct >= 15:
        return "SELL", "Momentum Target Hit (+15%)"

    # 5. Overbought
    if rsi > 80:
        return "SELL", f"Overbought (RSI {round(rsi, 1)})"

    # 6. Momentum add
    if regime == "SPRINTER" and pnl_pct > 5:
        return "ADD", "Momentum – Pyramid Into Strength"

    # 7. Compounder hold
    if regime == "COMPOUNDER" and pnl_pct > 3:
        return "HOLD", "Compounding – Stay The Course"

    # 8. Reversal / early stage
    if regime == "REVERSAL":
        if pnl_pct > 0:
            return "HOLD", "Reversal Playing Out – Lock Partial?"
        else:
            return "HOLD", "Reversal In Progress – Patience"

    # Default
    if quality >= 60:
        return "HOLD", "Fundamentals Strong – Trend Intact"
    
    return "HOLD", "Trend Intact"


@app.get("/api/portfolio")
async def get_portfolio():
    items = []
    total_invested = 0
    total_current = 0
    sell_count = 0
    add_count = 0
    
    for ticker, p in portfolio_db.items():
        stock_data = stocks_db.get(ticker, {})
        current_price = stock_data.get("price", p["buy_price"])
        invested = p["buy_price"] * p["quantity"]
        current_val = current_price * p["quantity"]
        pnl = current_val - invested
        pnl_pct = (pnl / invested * 100) if invested > 0 else 0
        total_invested += invested
        total_current += current_val
        
        # Generate recommendation
        action, reason = _recommend_action(p["buy_price"], current_price, pnl_pct, stock_data)
        if action == "SELL":
            sell_count += 1
        elif action == "ADD":
            add_count += 1

        items.append({
            "ticker": ticker,
            "buy_price": p["buy_price"],
            "current_price": round(current_price, 2),
            "quantity": p["quantity"],
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "tag": p.get("tag", "STAYER"),
            "stock_data": stock_data,
            "action": action,
            "action_reason": reason,
            "regime": stock_data.get("regime", "NEUTRAL"),
            "rsi": stock_data.get("rsi", 50),
            "quality_score": stock_data.get("quality_score", 0),
        })
    total_pnl = total_current - total_invested
    total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0
    
    # Advanced Risk Analysis
    risk_analysis = risk_mgr.analyze_portfolio_risk(items, total_current)
    
    return {
        "items": items,
        "summary": {
            "total_invested": round(total_invested, 2),
            "total_current": round(total_current, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl_pct, 2),
            "sell_signals": sell_count,
            "add_signals": add_count,
            "hold_count": len(items) - sell_count - add_count,
        },
        "risk": risk_analysis
    }


@app.post("/api/portfolio")
async def add_to_portfolio(item: PortfolioItem):
    t = item.ticker.upper()
    if t in portfolio_db:
        raise HTTPException(status_code=400, detail=f"{t} already in portfolio")
    portfolio_db[t] = {
        "ticker": t,
        "buy_price": item.buy_price,
        "quantity": item.quantity,
        "tag": item.tag,
    }
    return {"status": "added", "ticker": t}


@app.put("/api/portfolio/{ticker}")
async def update_portfolio(ticker: str, item: PortfolioItem):
    t = ticker.upper()
    if t not in portfolio_db:
        raise HTTPException(status_code=404, detail="Not in portfolio")
    portfolio_db[t].update({
        "buy_price": item.buy_price,
        "quantity": item.quantity,
        "tag": item.tag,
    })
    return {"status": "updated"}


@app.delete("/api/portfolio/{ticker}")
async def remove_from_portfolio(ticker: str):
    t = ticker.upper()
    if t in portfolio_db:
        del portfolio_db[t]
        return {"status": "removed"}
    raise HTTPException(status_code=404, detail="Not in portfolio")


# ── SECTORS endpoint ─────────────────────────────────────────────
@app.get("/api/sectors/heatmap")
async def get_sector_heatmap():
    sector_map = {}
    for s in stocks_db.values():
        sec = s.get("sector", "General")
        if sec not in sector_map:
            sector_map[sec] = {"sector": sec, "stocks": [], "total_quality": 0, "count": 0,
                               "sprinters": 0, "compounders": 0, "total_change": 0}
        sector_map[sec]["stocks"].append(s)
        sector_map[sec]["total_quality"] += s.get("quality_score", 0)
        sector_map[sec]["count"] += 1
        sector_map[sec]["total_change"] += s.get("change_pct", 0)
        if s.get("regime") == "SPRINTER":
            sector_map[sec]["sprinters"] += 1
        elif s.get("regime") == "COMPOUNDER":
            sector_map[sec]["compounders"] += 1

    result = []
    for sec_data in sector_map.values():
        count = sec_data["count"]
        result.append({
            "sector": sec_data["sector"],
            "count": count,
            "avg_quality": round(sec_data["total_quality"] / count, 1) if count else 0,
            "avg_change": round(sec_data["total_change"] / count, 2) if count else 0,
            "sprinters": sec_data["sprinters"],
            "compounders": sec_data["compounders"],
        })
    result.sort(key=lambda x: x["avg_change"], reverse=True)
    return result


# ── NEWS endpoint ────────────────────────────────────────────────
@app.get("/api/news/{ticker}")
async def get_stock_news(ticker: str):
    stock = stocks_db.get(ticker.upper(), {})
    name = stock.get("name", ticker)
    articles = news_engine.fetch_news(name)
    if articles:
        headlines = [a["title"] for a in articles]
        sentiments = await news_engine.analyze_sentiment_batch(headlines)
        for i, a in enumerate(articles):
            if i < len(sentiments):
                a["sentiment"] = sentiments[i]
    return articles


# ── ALERTS endpoints ─────────────────────────────────────────────
@app.get("/api/alerts/settings")
async def get_alert_settings():
    return alert_settings


@app.post("/api/alerts/settings")
async def update_alert_settings(settings: AlertSettings):
    alert_settings.update(settings.dict())
    return {"status": "updated"}


@app.get("/api/alerts/regime-changes")
async def get_regime_changes(limit: int = 50):
    return regime_changes_db[:limit]


import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# ── React Static Serve ───────────────────────────────────────────
frontend_build_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "build")
if os.path.exists(frontend_build_path):
    app.mount("/static", StaticFiles(directory=os.path.join(frontend_build_path, "static")), name="static")

    @app.get("/{full_path:path}")
    async def serve_react_app(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        file_path = os.path.join(frontend_build_path, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_build_path, "index.html"))

# ── Main ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port)