"""
Background scan worker + APScheduler-driven refresh.

Workflow:
  1. APScheduler triggers `refresh_universe(universe)` every 20 min during
     IST market hours, plus once at 16:00 IST for EOD snapshot.
  2. refresh_universe acquires a Mongo-backed lock so concurrent triggers
     (e.g. user-initiated /api/scan/refresh + scheduled tick) don't double-run.
  3. Iterates the universe ticker list, calls yf_fetcher → analysis_engine,
     writes results to MongoDB scan_results.
  4. Per-batch yields scan progress via a shared scan_state dict (read by
     /api/scan/status).
  5. Evening Scanner runs at 15:45 IST to detect pre-rally patterns for
     next-day entries.
"""
import logging
import threading
import time
from datetime import datetime, timezone
from typing import List

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

import cache
import db
from analysis_engine import AnalysisEngine
from market_hours import IST, is_market_open, is_trading_day
from nse_universe import get_tickers, UNIVERSE_MAP
from yf_fetcher import fetch_ticker
from evening_scanner import run_evening_scan, scan_single_stock

logger = logging.getLogger(__name__)

_engine = AnalysisEngine()

# Shared progress dict (read by /api/scan/status)
scan_state = {
    "running": False,
    "universe": "",
    "progress": 0,
    "total": 0,
    "current_ticker": "",
    "profile": "LONG_TERM",
    "started_at": None,
    "completed_at": None,
    "status": "idle",      # idle | running | complete | partial | failed
    "success_count": 0,
    "fail_count": 0,
    "last_refreshed": {},  # universe -> iso timestamp
}

# Evening scan progress state
evening_scan_state = {
    "running": False,
    "progress": 0,
    "total": 0,
    "current_ticker": "",
    "started_at": None,
    "completed_at": None,
    "status": "idle",
    "results_count": 0,
}

_state_lock = threading.Lock()


def _persist_scan_result(universe: str, profile: str, results: List[dict],
                         status: str, success: int, failed: int) -> str:
    """Write the scan result to MongoDB. Keeps last 3 versions per universe."""
    if not db._use_mongo:
        return ""
    scan_id = f"{universe}_{int(time.time())}"
    try:
        db._db.scan_results.insert_one({
            "scan_id": scan_id,
            "universe": universe,
            "profile": profile,
            "results": results,
            "success_count": success,
            "fail_count": failed,
            "status": status,
            "timestamp": datetime.now(timezone.utc),
        })
        # Prune: keep only last 3 per universe
        old = list(db._db.scan_results.find(
            {"universe": universe}, {"_id": 1}
        ).sort("timestamp", -1).skip(3))
        if old:
            db._db.scan_results.delete_many({"_id": {"$in": [d["_id"] for d in old]}})
        # Also write summary to scan_runs
        db._db.scan_runs.insert_one({
            "scan_id": scan_id,
            "universe": universe,
            "profile": profile,
            "started_at": datetime.now(timezone.utc),
            "success_count": success,
            "fail_count": failed,
            "status": status,
        })
    except Exception as e:
        logger.error(f"persist scan {universe}: {e}")
    return scan_id


def get_latest_scan(universe: str) -> dict:
    """Return the most recent persisted scan results for a universe."""
    if not db._use_mongo:
        return {"universe": universe, "results": [], "timestamp": None}
    try:
        doc = db._db.scan_results.find_one(
            {"universe": universe},
            sort=[("timestamp", -1)],
        )
        if not doc:
            return {"universe": universe, "results": [], "timestamp": None}
        doc.pop("_id", None)
        if isinstance(doc.get("timestamp"), datetime):
            doc["timestamp"] = doc["timestamp"].isoformat()
        return doc
    except Exception as e:
        logger.error(f"get_latest_scan {universe}: {e}")
        return {"universe": universe, "results": [], "timestamp": None}


def refresh_universe(universe: str, profile: str = "LONG_TERM",
                     force: bool = False) -> dict:
    """
    Refresh the cache for a given universe. Lock-protected.
    `force=True` skips the trading-hours check (for manual user-triggered refresh).
    """
    universe = universe.lower()
    if universe not in UNIVERSE_MAP:
        return {"error": "unknown_universe", "universe": universe}

    lock_key = f"scan:{universe}:{profile}"
    if not cache.acquire_scan_lock(lock_key, ttl_seconds=900):
        logger.info(f"scan {universe}/{profile}: lock held, skipping")
        return {"status": "locked", "universe": universe}

    tickers = get_tickers(universe)
    started = datetime.now(timezone.utc)

    with _state_lock:
        scan_state.update({
            "running": True,
            "universe": universe,
            "profile": profile,
            "progress": 0,
            "total": len(tickers),
            "current_ticker": "",
            "started_at": started.isoformat(),
            "completed_at": None,
            "status": "running",
            "success_count": 0,
            "fail_count": 0,
        })

    results = []
    success = 0
    fail = 0

    try:
        for i, ticker in enumerate(tickers):
            with _state_lock:
                scan_state["progress"] = i + 1
                scan_state["current_ticker"] = ticker

            try:
                # Penny-stock price guard: only include if last close < 50
                # (we apply after fetch so we use real price)
                fetched = fetch_ticker(ticker)
                if not fetched:
                    fail += 1
                    continue

                analysis = _engine.analyze_stock(ticker, profile)
                if not analysis:
                    fail += 1
                    continue

                # Penny universe: hard price filter
                if universe == "penny" and analysis.get("price", 999) > 50:
                    continue

                # Cache the analysis dict (L1+L2)
                cache.set_ticker(ticker, analysis, ttl=900)

                # Track regime change
                old = cache.get_ticker(f"{ticker}::regime") or {}
                old_regime = old.get("regime") if isinstance(old, dict) else None
                if old_regime and old_regime != analysis.get("regime"):
                    db.regime_changes_add({
                        "ticker": ticker,
                        "name": analysis.get("name", ticker),
                        "old_regime": old_regime,
                        "new_regime": analysis.get("regime"),
                        "profile": profile,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                cache.set_ticker(f"{ticker}::regime", {"regime": analysis.get("regime")}, ttl=86400)

                results.append(analysis)
                success += 1
                with _state_lock:
                    scan_state["success_count"] = success
            except Exception as e:
                logger.error(f"scan {ticker}: {e}")
                cache.log_error(ticker, "scan_inner", str(e))
                fail += 1
                with _state_lock:
                    scan_state["fail_count"] = fail

        # Determine status
        total = len(tickers)
        if success == 0:
            status = "failed"
        elif fail / max(total, 1) > 0.20:
            status = "partial"
        else:
            status = "complete"

        scan_id = _persist_scan_result(universe, profile, results, status, success, fail)
        completed = datetime.now(timezone.utc)
        with _state_lock:
            scan_state.update({
                "running": False,
                "completed_at": completed.isoformat(),
                "current_ticker": "",
                "status": status,
            })
            scan_state["last_refreshed"][universe] = completed.isoformat()

        logger.info(f"scan {universe}/{profile} done: {success} ok, {fail} fail ({status})")
        return {
            "status": status,
            "universe": universe,
            "profile": profile,
            "scan_id": scan_id,
            "success": success,
            "fail": fail,
            "total": total,
            "duration_sec": (completed - started).total_seconds(),
        }
    finally:
        cache.release_scan_lock(lock_key)
        with _state_lock:
            if scan_state["running"]:
                scan_state["running"] = False


# ── Evening Scan persistence ──────────────────────────────────────
def _persist_evening_result(results: List[dict], status: str) -> str:
    """Write evening scan results to MongoDB."""
    if not db._use_mongo:
        return ""
    scan_id = f"evening_{int(time.time())}"
    try:
        db._db.evening_scan_results.insert_one({
            "scan_id": scan_id,
            "results": results,
            "results_count": len(results),
            "status": status,
            "timestamp": datetime.now(timezone.utc),
        })
        # Keep last 5 evening scans
        old = list(db._db.evening_scan_results.find(
            {}, {"_id": 1}
        ).sort("timestamp", -1).skip(5))
        if old:
            db._db.evening_scan_results.delete_many({"_id": {"$in": [d["_id"] for d in old]}})
    except Exception as e:
        logger.error(f"persist evening scan: {e}")
    return scan_id


def get_latest_evening_scan() -> dict:
    """Return the most recent evening scan results."""
    if not db._use_mongo:
        return {"results": [], "timestamp": None, "status": "no_db"}
    try:
        doc = db._db.evening_scan_results.find_one(
            {}, sort=[("timestamp", -1)]
        )
        if not doc:
            return {"results": [], "timestamp": None, "status": "no_data"}
        doc.pop("_id", None)
        if isinstance(doc.get("timestamp"), datetime):
            doc["timestamp"] = doc["timestamp"].isoformat()
        return doc
    except Exception as e:
        logger.error(f"get_latest_evening_scan: {e}")
        return {"results": [], "timestamp": None, "status": "error"}


def refresh_evening_scan(universe: str = "nifty200", force: bool = False) -> dict:
    """
    Run the evening scanner across a universe.
    Designed to run at 15:45 IST after market close.
    """
    from nse_universe import NIFTY_200, FNO_UNDERLYING, UNIVERSE_MAP

    # Build combined universe: Nifty 200 + F&O (deduplicated)
    if universe == "evening_default":
        tickers = list(set(NIFTY_200 + FNO_UNDERLYING))
    else:
        tickers = UNIVERSE_MAP.get(universe, NIFTY_200)

    started = datetime.now(timezone.utc)
    total = len(tickers)

    with _state_lock:
        evening_scan_state.update({
            "running": True,
            "progress": 0,
            "total": total,
            "current_ticker": "",
            "started_at": started.isoformat(),
            "completed_at": None,
            "status": "running",
            "results_count": 0,
        })

    # First pass: gather sector performance from recent scan data
    existing_results = []
    latest = get_latest_scan("nifty200") or get_latest_scan("nifty100")
    if latest and latest.get("results"):
        existing_results = latest["results"]

    from evening_scanner import build_sector_performance
    sector_perf = build_sector_performance(existing_results) if existing_results else {}

    results = []
    for i, ticker in enumerate(tickers):
        with _state_lock:
            evening_scan_state["progress"] = i + 1
            evening_scan_state["current_ticker"] = ticker

        try:
            result = scan_single_stock(ticker, sector_perf)
            if result:
                results.append(result)
        except Exception as e:
            logger.error(f"evening scan {ticker}: {e}")

    # Sort by conviction
    results.sort(key=lambda x: x.get("conviction_score", 0), reverse=True)

    status = "complete" if results else "no_signals"
    scan_id = _persist_evening_result(results, status)
    completed = datetime.now(timezone.utc)

    with _state_lock:
        evening_scan_state.update({
            "running": False,
            "completed_at": completed.isoformat(),
            "current_ticker": "",
            "status": status,
            "results_count": len(results),
        })

    logger.info(f"Evening scan done: {len(results)} signals from {total} stocks")
    return {
        "status": status,
        "scan_id": scan_id,
        "results_count": len(results),
        "total_scanned": total,
        "duration_sec": (completed - started).total_seconds(),
    }


# ── APScheduler setup ─────────────────────────────────────────────
_scheduler = None
_default_universes = ["nifty50", "nifty100", "fno"]   # quick refresh during day
_deep_universes = ["nifty500", "smallcap"]              # EOD refresh only


def _scheduled_market_hours_refresh():
    """Runs every 20min during IST market hours."""
    if not is_market_open():
        return
    for universe in _default_universes:
        try:
            refresh_universe(universe, "LONG_TERM")
        except Exception as e:
            logger.error(f"scheduled refresh {universe}: {e}")


def _scheduled_eod_refresh():
    """Runs once at 16:00 IST on trading days."""
    if not is_trading_day():
        return
    for universe in _default_universes + _deep_universes:
        try:
            refresh_universe(universe, "LONG_TERM")
        except Exception as e:
            logger.error(f"EOD refresh {universe}: {e}")


def _scheduled_evening_scan():
    """Runs at 15:45 IST on trading days. Predictive pre-rally scanner."""
    if not is_trading_day():
        return
    try:
        refresh_evening_scan("evening_default", force=True)
    except Exception as e:
        logger.error(f"scheduled evening scan: {e}")


def start_scheduler():
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    _scheduler = BackgroundScheduler(timezone=IST)

    # Every 20 min during market hours, Mon-Fri 09:15-15:30 IST
    _scheduler.add_job(
        _scheduled_market_hours_refresh,
        CronTrigger(day_of_week="mon-fri", hour="9-15", minute="*/20", timezone=IST),
        id="market_hours_refresh",
        replace_existing=True,
    )
    # EOD at 16:00 IST
    _scheduler.add_job(
        _scheduled_eod_refresh,
        CronTrigger(day_of_week="mon-fri", hour=16, minute=0, timezone=IST),
        id="eod_refresh",
        replace_existing=True,
    )
    # Evening Scanner at 15:45 IST
    _scheduler.add_job(
        _scheduled_evening_scan,
        CronTrigger(day_of_week="mon-fri", hour=15, minute=45, timezone=IST),
        id="evening_scan",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("Scheduler started: market_hours (20min) + eod (16:00) + evening_scan (15:45 IST)")
    return _scheduler


def stop_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
