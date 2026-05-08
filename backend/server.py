from fastapi import FastAPI, APIRouter, Request, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
from pydantic import BaseModel
from typing import Optional, List
import threading
import time
import asyncio
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

from analysis_engine import AnalysisEngine
from nse_universe import get_tickers, get_scan_info, UNIVERSE_MAP, INDEX_PROXIES
import news_sentiment as ns
from alert_service import AlertService
from risk_manager import RiskManager
from recommendation_engine import recommend
from fundamental_health import health_for_ticker
from yf_fetcher import fetch_ticker
import cache
import db
import scan_worker
from scan_worker import refresh_universe, get_latest_scan, scan_state

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

# ── Legacy in-memory store (kept as a thin layer) ─────────────────
stocks_db = {}
stocks_db_by_profile = {"LONG_TERM": {}, "SWING": {}, "SHORT_TERM": {}}

# ── Persistent stores helpers ─────────────────────────────────────
def _portfolio_db():
    return db.portfolio_all()

def _watchlist_db():
    return db.watchlist_all()

def _alert_settings():
    return db.alerts_get()

engine = AnalysisEngine()
alert_service = AlertService()
risk_mgr = RiskManager(account_size=80000.0)


# ── Pydantic models ──────────────────────────────────────────────
class ScanRequest(BaseModel):
    universe: str = "nifty50"
    profile: str = "LONG_TERM"


class ScanRefreshRequest(BaseModel):
    universe: str = "nifty50"
    profile: str = "LONG_TERM"


class WatchlistItem(BaseModel):
    ticker: str
    tag: str = "STAYER"


class PortfolioItem(BaseModel):
    ticker: str
    buy_price: float
    quantity: int = 1
    tag: str = "STAYER"
    profile: str = "LONG_TERM"
    buy_date: Optional[str] = None
    notes: Optional[str] = ""


class AlertSettings(BaseModel):
    email: str = ""
    enabled: bool = False


# ── Request logger ────────────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Incoming: {request.method} {request.url.path}")
    response = await call_next(request)
    return response


# ── Startup: indexes + scheduler ─────────────────────────────────
@app.on_event("startup")
def _on_startup():
    cache.ensure_indexes()
    try:
        scan_worker.start_scheduler()
    except Exception as e:
        logger.error(f"scheduler start failed: {e}")


@app.on_event("shutdown")
def _on_shutdown():
    try:
        scan_worker.stop_scheduler()
    except Exception:
        pass


# ── Helper: hydrate stocks_db from latest cached scan ─────────────
def _hydrate_from_scan(universe: str):
    """Pull latest scan results for a universe into the in-memory cache."""
    latest = get_latest_scan(universe)
    if not latest.get("results"):
        return
    profile_cache = stocks_db_by_profile.setdefault(latest.get("profile", "LONG_TERM"), {})
    for s in latest["results"]:
        t = s.get("ticker", "").upper().replace(".NS", "")
        if not t:
            continue
        stocks_db[t] = s
        profile_cache[t] = s


# ── SCAN endpoints ────────────────────────────────────────────────
@app.post("/api/scan/start")
async def start_scan(request: ScanRequest, background_tasks: BackgroundTasks):
    """Trigger a fresh scan for a universe (async). Returns immediately."""
    if scan_state.get("running"):
        raise HTTPException(status_code=400, detail="A scan is already running")
    if request.universe.lower() not in UNIVERSE_MAP:
        raise HTTPException(status_code=400, detail=f"Unknown universe: {request.universe}")

    background_tasks.add_task(refresh_universe, request.universe.lower(),
                              request.profile.upper(), True)
    return {
        "status": "started",
        "universe": request.universe.lower(),
        "total": len(get_tickers(request.universe.lower())),
    }


@app.post("/api/scan/refresh")
async def refresh_scan(request: ScanRefreshRequest, background_tasks: BackgroundTasks):
    """Same as /scan/start but explicitly bypasses any cache."""
    background_tasks.add_task(refresh_universe, request.universe.lower(),
                              request.profile.upper(), True)
    return {"status": "refreshing", "universe": request.universe.lower()}


@app.get("/api/scan/status")
async def get_scan_status():
    return scan_state


@app.get("/api/scan/levels")
async def get_scan_levels():
    return get_scan_info()


@app.get("/api/scan/results")
async def get_scan_results(universe: str = "nifty50",
                           regime: Optional[str] = None,
                           sort: Optional[str] = None,
                           limit: Optional[int] = None):
    """Return cached scan results for a universe, with optional filters."""
    universe = universe.lower()
    latest = get_latest_scan(universe)
    results = latest.get("results", [])

    # Hydrate in-memory cache for downstream endpoints
    if results:
        _hydrate_from_scan(universe)

    if regime:
        results = [s for s in results if s.get("regime") == regime.upper()]
    if sort == "quality":
        results.sort(key=lambda s: s.get("quality_score", 0), reverse=True)
    elif sort == "change":
        results.sort(key=lambda s: s.get("change_pct", 0), reverse=True)
    elif sort == "rsi":
        results.sort(key=lambda s: s.get("rsi", 50), reverse=True)
    if limit:
        results = results[:limit]

    return {
        "universe": universe,
        "count": len(results),
        "timestamp": latest.get("timestamp"),
        "status": latest.get("status"),
        "results": results,
    }


# ── STOCKS endpoints (legacy preserved) ───────────────────────────
@app.get("/api/stocks")
async def get_stocks(regime: Optional[str] = None, sort: Optional[str] = None,
                     profile: Optional[str] = None):
    if profile:
        cache_dict = stocks_db_by_profile.get(profile.upper(), {})
        result = list(cache_dict.values())
    else:
        result = list(stocks_db.values())
    if regime:
        result = [s for s in result if s.get("regime") == regime.upper()]
    if sort == "quality":
        result.sort(key=lambda s: s.get("quality_score", 0), reverse=True)
    elif sort == "change":
        result.sort(key=lambda s: s.get("change_pct", 0), reverse=True)
    elif sort == "rsi":
        result.sort(key=lambda s: s.get("rsi", 50), reverse=True)
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
    t = ticker.upper().replace(".NS", "")
    cached = cache.get_ticker(t)
    if cached:
        stocks_db[t] = cached

    if t not in stocks_db:
        result = engine.analyze_stock(t)
        if result:
            cache.set_ticker(t, result)
            stocks_db[t] = result
        else:
            raise HTTPException(status_code=404, detail="Stock not found or invalid ticker.")

    if t in stocks_db:
        data = stocks_db[t].copy()
        portfolio_tickers = list(_portfolio_db().keys())
        corr_data = risk_mgr.check_correlation(t, portfolio_tickers)
        data["correlation_warning"] = corr_data
        size_data = risk_mgr.position_sizing_kelly(
            win_rate=0.55,
            win_loss_ratio=2.0,
            current_price=data["price"],
            stop_loss_price=data["price"] * 0.90,
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

        n_price = nifty.iloc[-1]; n_prev = nifty.iloc[-2]
        n_chg = ((n_price - n_prev) / n_prev) * 100
        b_price = bank.iloc[-1]; b_prev = bank.iloc[-2]
        b_chg = ((b_price - b_prev) / b_prev) * 100

        return {
            "NIFTY50":   {"price": round(n_price, 2), "change_pct": round(n_chg, 2)},
            "BANKNIFTY": {"price": round(b_price, 2), "change_pct": round(b_chg, 2)},
        }
    except Exception:
        return {
            "NIFTY50":   {"price": 22500.0, "change_pct": 0.5},
            "BANKNIFTY": {"price": 48000.0, "change_pct": -0.2},
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
    for ticker, wl in _watchlist_db().items():
        entry = dict(wl)
        entry["stock_data"] = stocks_db.get(ticker, cache.get_ticker(ticker) or {})
        result.append(entry)
    return result


@app.post("/api/watchlist")
async def add_to_watchlist(item: WatchlistItem):
    t = item.ticker.upper()
    if db.watchlist_get(t):
        raise HTTPException(status_code=400, detail=f"{t} already in watchlist")
    db.watchlist_upsert(t, {"ticker": t, "tag": item.tag,
                            "added_at": datetime.now(timezone.utc).isoformat()})
    return {"status": "added", "ticker": t}


@app.delete("/api/watchlist/{ticker}")
async def remove_from_watchlist(ticker: str):
    t = ticker.upper()
    if db.watchlist_delete(t):
        return {"status": "removed"}
    raise HTTPException(status_code=404, detail="Not in watchlist")


@app.put("/api/watchlist/{ticker}/tag")
async def update_watchlist_tag(ticker: str, tag: str = "STAYER"):
    t = ticker.upper()
    existing = db.watchlist_get(t)
    if existing:
        db.watchlist_upsert(t, {**existing, "tag": tag})
        return {"status": "updated"}
    raise HTTPException(status_code=404, detail="Not in watchlist")


# ── PORTFOLIO endpoints ──────────────────────────────────────────
@app.get("/api/portfolio")
async def get_portfolio():
    items = []
    total_invested = 0
    total_current = 0
    for ticker, p in _portfolio_db().items():
        sd = stocks_db.get(ticker) or cache.get_ticker(ticker)
        if not sd:
            try:
                sd = engine.analyze_stock(ticker, p.get("profile", "LONG_TERM"))
                if sd:
                    cache.set_ticker(ticker, sd)
                    stocks_db[ticker] = sd
            except Exception:
                sd = None
        current_price = (sd or {}).get("price", p["buy_price"])
        invested = p["buy_price"] * p["quantity"]
        current_val = current_price * p["quantity"]
        pnl = current_val - invested
        pnl_pct = (pnl / invested * 100) if invested > 0 else 0
        total_invested += invested
        total_current += current_val

        rec = recommend(sd or {"price": current_price}, p["buy_price"],
                        p.get("profile", "LONG_TERM"), p.get("buy_date"))

        items.append({
            "ticker": ticker,
            "name": (sd or {}).get("name", ticker),
            "buy_price": p["buy_price"],
            "current_price": round(current_price, 2),
            "quantity": p["quantity"],
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "tag": p.get("tag", "STAYER"),
            "profile": p.get("profile", "LONG_TERM"),
            "buy_date": p.get("buy_date"),
            "notes": p.get("notes", ""),
            "recommendation": rec,
            "stock_data": sd or {},
        })
    total_pnl = total_current - total_invested
    total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0
    risk_analysis = risk_mgr.analyze_portfolio_risk(items, total_current)
    return {
        "items": items,
        "summary": {
            "total_invested": round(total_invested, 2),
            "total_current": round(total_current, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl_pct, 2),
        },
        "risk": risk_analysis
    }


@app.post("/api/portfolio")
async def add_to_portfolio(item: PortfolioItem):
    t = item.ticker.upper()
    if db.portfolio_get(t):
        raise HTTPException(status_code=400, detail=f"{t} already in portfolio")
    db.portfolio_upsert(t, {
        "ticker": t,
        "buy_price": item.buy_price,
        "quantity": item.quantity,
        "tag": item.tag,
        "profile": (item.profile or "LONG_TERM").upper(),
        "buy_date": item.buy_date or datetime.now(timezone.utc).isoformat(),
        "notes": item.notes or "",
        "added_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"status": "added", "ticker": t}


@app.put("/api/portfolio/{ticker}")
async def update_portfolio(ticker: str, item: PortfolioItem):
    t = ticker.upper()
    existing = db.portfolio_get(t)
    if not existing:
        raise HTTPException(status_code=404, detail="Not in portfolio")
    db.portfolio_upsert(t, {
        **existing,
        "buy_price": item.buy_price,
        "quantity": item.quantity,
        "tag": item.tag,
        "profile": (item.profile or existing.get("profile", "LONG_TERM")).upper(),
        "buy_date": item.buy_date or existing.get("buy_date"),
        "notes": item.notes if item.notes is not None else existing.get("notes", ""),
    })
    return {"status": "updated"}


@app.get("/api/portfolio/correlation-matrix")
async def get_correlation_matrix():
    portfolio_tickers = list(_portfolio_db().keys())
    if len(portfolio_tickers) < 2:
        return {"matrix": [], "tickers": portfolio_tickers, "message": "Need at least 2 stocks"}
    
    # We can reuse RiskManager to compute pairwise
    # Or fetch hist for all and compute. 
    # For simplicity, we just use risk_mgr.check_correlation
    matrix = []
    import pandas as pd
    import yfinance as yf
    
    try:
        # Download 3mo history for all portfolio stocks
        symbols = [(t if t.endswith(".NS") else f"{t}.NS") for t in portfolio_tickers]
        data = yf.download(symbols, period="3mo")['Close']
        if isinstance(data, pd.Series): # only 1 valid
            return {"matrix": [], "tickers": portfolio_tickers}
            
        corr = data.corr()
        
        for i, t1 in enumerate(portfolio_tickers):
            row = []
            s1 = t1 if t1.endswith(".NS") else f"{t1}.NS"
            for t2 in portfolio_tickers:
                s2 = t2 if t2.endswith(".NS") else f"{t2}.NS"
                if s1 in corr.columns and s2 in corr.columns:
                    val = corr.loc[s1, s2]
                    row.append(round(val, 2) if pd.notna(val) else 0)
                else:
                    row.append(0)
            matrix.append(row)
            
        return {"matrix": matrix, "tickers": portfolio_tickers}
    except Exception as e:
        logger.error(f"Correlation matrix error: {e}")
        return {"matrix": [], "tickers": portfolio_tickers, "error": str(e)}

@app.delete("/api/portfolio/{ticker}")
async def remove_from_portfolio(ticker: str):
    t = ticker.upper()
    if db.portfolio_delete(t):
        return {"status": "removed"}
    raise HTTPException(status_code=404, detail="Not in portfolio")


@app.get("/api/portfolio/{ticker}/recommendation")
async def get_portfolio_recommendation(ticker: str):
    t = ticker.upper()
    p = db.portfolio_get(t)
    if not p:
        raise HTTPException(status_code=404, detail="Not in portfolio")
    sd = stocks_db.get(t) or cache.get_ticker(t)
    if not sd:
        sd = engine.analyze_stock(t, p.get("profile", "LONG_TERM"))
        if sd:
            cache.set_ticker(t, sd)
            stocks_db[t] = sd
    if not sd:
        raise HTTPException(status_code=404, detail="Stock data unavailable")
    return {
        "ticker": t,
        "stock": sd,
        "holding": {
            "buy_price": p["buy_price"],
            "quantity": p["quantity"],
            "buy_date": p.get("buy_date"),
            "profile": p.get("profile", "LONG_TERM"),
        },
        "recommendation": recommend(sd, p["buy_price"], p.get("profile", "LONG_TERM"), p.get("buy_date")),
    }


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


# ── NEWS + SENTIMENT endpoints ───────────────────────────────────
@app.get("/api/news/{ticker}")
async def get_stock_news(ticker: str, refresh: bool = False):
    """Per-ticker news + sentiment. Returns full headlines with bullish/bearish labels."""
    t = ticker.upper().replace(".NS", "")
    name = (stocks_db.get(t) or cache.get_ticker(t) or {}).get("name") or t
    return await ns.sentiment_for_ticker(t, name, force_refresh=refresh)


@app.get("/api/sentiment/{ticker}")
async def get_ticker_sentiment(ticker: str, refresh: bool = False):
    """Returns just the aggregate sentiment block (lightweight)."""
    t = ticker.upper().replace(".NS", "")
    name = (stocks_db.get(t) or cache.get_ticker(t) or {}).get("name") or t
    full = await ns.sentiment_for_ticker(t, name, force_refresh=refresh)
    return {
        "ticker": full.get("ticker"),
        "state": full.get("state"),
        "score": full.get("score"),
        "label": full.get("label"),
        "headline_count": full.get("headline_count", 0),
        "computed_at": full.get("computed_at"),
    }


@app.get("/api/sentiment/market/{universe}")
async def get_market_sentiment(universe: str = "nifty50"):
    """Market-wide sentiment aggregated from cached per-ticker sentiments."""
    universe = universe.lower()
    if universe not in UNIVERSE_MAP:
        raise HTTPException(status_code=400, detail=f"Unknown universe: {universe}")
    tickers = get_tickers(universe)
    return ns.aggregate_market_sentiment(tickers)


@app.post("/api/sentiment/refresh")
async def refresh_sentiment(background_tasks: BackgroundTasks,
                            universe: str = "nifty50", limit: int = 30):
    """
    Trigger a background sentiment refresh for top-N tickers in a universe.
    Runs async; clients should poll /api/sentiment/{ticker} to read.
    """
    universe = universe.lower()
    if universe not in UNIVERSE_MAP:
        raise HTTPException(status_code=400, detail=f"Unknown universe: {universe}")
    tickers = get_tickers(universe)[:limit]

    def _bg(tickers):
        for t in tickers:
            try:
                name = (cache.get_ticker(t) or {}).get("name") or t
                ns.sentiment_for_ticker_sync(t, name, force_refresh=True)
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"sentiment refresh {t}: {e}")

    background_tasks.add_task(_bg, tickers)
    return {"status": "queued", "universe": universe, "count": len(tickers)}


# ── FUNDAMENTAL HEALTH endpoints ─────────────────────────────────
@app.get("/api/fundamentals/{ticker}")
async def get_fundamental(ticker: str, refresh: bool = False):
    t = ticker.upper().replace(".NS", "")
    return health_for_ticker(t, force_refresh=refresh)


# ── F&O endpoints ────────────────────────────────────────────────
@app.get("/api/fno/indices")
async def get_fno_indices():
    """Returns sentiment+technical for the major F&O indices (NIFTY, BANKNIFTY, etc).
    yfinance doesn't expose Indian option chains, so we surface index-level data.
    """
    import yfinance as yf
    out = []
    for label, symbol in INDEX_PROXIES.items():
        try:
            t = yf.Ticker(symbol)
            hist = t.history(period="5d")
            if hist.empty:
                continue
            last = float(hist["Close"].iloc[-1])
            prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else last
            chg_pct = ((last - prev) / prev * 100) if prev else 0
            out.append({
                "name": label,
                "symbol": symbol,
                "price": round(last, 2),
                "change_pct": round(chg_pct, 2),
            })
        except Exception as e:
            logger.error(f"fno_indices {symbol}: {e}")
    return out


# ── ALERTS endpoints ─────────────────────────────────────────────
@app.get("/api/alerts/settings")
async def get_alert_settings():
    return _alert_settings()


@app.post("/api/alerts/settings")
async def update_alert_settings(settings: AlertSettings):
    db.alerts_set(settings.dict())
    return {"status": "updated"}


@app.get("/api/alerts/regime-changes")
async def get_regime_changes(limit: int = 50):
    return db.regime_changes_list(limit)


# ── ADMIN / HEALTH endpoints ─────────────────────────────────────
@app.get("/api/admin/health")
async def get_health():
    return {
        "scan_state": scan_state,
        "cache": cache.health_summary(),
        "tracked_universes": list(scan_state.get("last_refreshed", {}).keys()),
    }

@app.get("/api/admin/cache_stats")
async def get_cache_stats():
    """Monitor cache hit rates to ensure limits aren't too restrictive."""
    summary = cache.health_summary()
    return {
        "ticker_cache_hit_rate": summary.get("l1_cache_sizes", {}).get("ticker", 0),
        "news_cache_hit_rate": summary.get("l1_cache_sizes", {}).get("news", 0),
        "note": "Hit rate proxy (current size in memory vs limit of 1000)"
    }


import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# ── React Static Serve ───────────────────────────────────────────
frontend_build_path = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend", "build")
)
logger.info(f"Frontend build path: {frontend_build_path}")
logger.info(f"Frontend build exists: {os.path.exists(frontend_build_path)}")

if os.path.exists(frontend_build_path):
    static_dir = os.path.join(frontend_build_path, "static")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
        logger.info("Mounted /static from frontend build.")
    else:
        logger.warning(f"Static dir not found at {static_dir}")

    @app.get("/{full_path:path}")
    async def serve_react_app(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        file_path = os.path.join(frontend_build_path, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_build_path, "index.html"))
else:
    logger.error(f"Frontend build NOT found at {frontend_build_path}. Listing parent dir:")
    parent = os.path.dirname(frontend_build_path)
    if os.path.exists(parent):
        logger.error(f"  Contents of {parent}: {os.listdir(parent)}")
    else:
        grandparent = os.path.dirname(parent)
        if os.path.exists(grandparent):
            logger.error(f"  Contents of {grandparent}: {os.listdir(grandparent)}")

    @app.get("/")
    async def fallback_root():
        return {
            "status": "backend_only",
            "message": "API is running but frontend build was not found.",
            "debug_path": frontend_build_path,
            "api_docs": "/docs",
        }


# ── Main ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port)
