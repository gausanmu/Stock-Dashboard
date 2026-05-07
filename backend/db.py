"""MongoDB persistence layer.
Falls back to a local JSON file if Mongo is unreachable, so the app keeps
working on Render free tier (where Mongo is not provisioned by default).
Users should set MONGO_URL env var to a Mongo Atlas URI for true persistence
on Render.
"""
import os
import sys
import json
import tempfile
import logging
import threading
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_FALLBACK_FILE = Path(os.environ.get("DB_FALLBACK_PATH", os.path.join(tempfile.gettempdir(), "stock_dashboard_db.json")))

_MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
_DB_NAME = os.environ.get("DB_NAME", "stock_dashboard")

_client = None
_db = None
_use_mongo = False

def _init():
    global _client, _db, _use_mongo
    try:
        from pymongo import MongoClient
        _client = MongoClient(_MONGO_URL, serverSelectionTimeoutMS=2500)
        # ping to fail fast
        _client.admin.command("ping")
        _db = _client[_DB_NAME]
        _use_mongo = True
        logger.info(f"DB: connected to MongoDB at {_MONGO_URL} (db={_DB_NAME})")
    except Exception as e:
        logger.warning(f"DB: MongoDB unavailable ({e}). Falling back to JSON file at {_FALLBACK_FILE}.")
        _use_mongo = False
        _FALLBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
        if not _FALLBACK_FILE.exists():
            _FALLBACK_FILE.write_text(json.dumps({"portfolio": {}, "watchlist": {}, "regime_changes": [], "alert_settings": {"email": "", "enabled": False}}))

_init()

# ── JSON-fallback helpers ─────────────────────────────────────────
def _read_file():
    try:
        with _lock:
            return json.loads(_FALLBACK_FILE.read_text())
    except Exception:
        return {"portfolio": {}, "watchlist": {}, "regime_changes": [], "alert_settings": {"email": "", "enabled": False}}

def _write_file(data):
    with _lock:
        _FALLBACK_FILE.write_text(json.dumps(data, default=str))

# ── Portfolio ────────────────────────────────────────────────────
def portfolio_all():
    if _use_mongo:
        return {d["ticker"]: {k: v for k, v in d.items() if k != "_id"} for d in _db.portfolio.find()}
    return _read_file().get("portfolio", {})

def portfolio_get(ticker):
    if _use_mongo:
        d = _db.portfolio.find_one({"ticker": ticker})
        if d:
            d.pop("_id", None)
        return d
    return _read_file().get("portfolio", {}).get(ticker)

def portfolio_upsert(ticker, doc):
    doc = {**doc, "ticker": ticker, "updated_at": datetime.utcnow().isoformat()}
    if _use_mongo:
        _db.portfolio.update_one({"ticker": ticker}, {"$set": doc}, upsert=True)
        return doc
    data = _read_file()
    data.setdefault("portfolio", {})[ticker] = doc
    _write_file(data)
    return doc

def portfolio_delete(ticker):
    if _use_mongo:
        return _db.portfolio.delete_one({"ticker": ticker}).deleted_count > 0
    data = _read_file()
    if ticker in data.get("portfolio", {}):
        del data["portfolio"][ticker]
        _write_file(data)
        return True
    return False

# ── Watchlist ────────────────────────────────────────────────────
def watchlist_all():
    if _use_mongo:
        return {d["ticker"]: {k: v for k, v in d.items() if k != "_id"} for d in _db.watchlist.find()}
    return _read_file().get("watchlist", {})

def watchlist_get(ticker):
    if _use_mongo:
        d = _db.watchlist.find_one({"ticker": ticker})
        if d:
            d.pop("_id", None)
        return d
    return _read_file().get("watchlist", {}).get(ticker)

def watchlist_upsert(ticker, doc):
    doc = {**doc, "ticker": ticker}
    if _use_mongo:
        _db.watchlist.update_one({"ticker": ticker}, {"$set": doc}, upsert=True)
        return doc
    data = _read_file()
    data.setdefault("watchlist", {})[ticker] = doc
    _write_file(data)
    return doc

def watchlist_delete(ticker):
    if _use_mongo:
        return _db.watchlist.delete_one({"ticker": ticker}).deleted_count > 0
    data = _read_file()
    if ticker in data.get("watchlist", {}):
        del data["watchlist"][ticker]
        _write_file(data)
        return True
    return False

# ── Regime changes ───────────────────────────────────────────────
def regime_changes_add(change):
    if _use_mongo:
        _db.regime_changes.insert_one({**change})
        return
    data = _read_file()
    data.setdefault("regime_changes", []).insert(0, change)
    data["regime_changes"] = data["regime_changes"][:200]
    _write_file(data)

def regime_changes_list(limit=50):
    if _use_mongo:
        docs = list(_db.regime_changes.find().sort("timestamp", -1).limit(limit))
        for d in docs:
            d.pop("_id", None)
        return docs
    return _read_file().get("regime_changes", [])[:limit]

# ── Alert settings ───────────────────────────────────────────────
def alerts_get():
    if _use_mongo:
        d = _db.alert_settings.find_one({"_id": "singleton"}) or {"email": "", "enabled": False}
        d.pop("_id", None)
        return d
    return _read_file().get("alert_settings", {"email": "", "enabled": False})

def alerts_set(settings):
    if _use_mongo:
        _db.alert_settings.update_one({"_id": "singleton"}, {"$set": settings}, upsert=True)
        return
    data = _read_file()
    data["alert_settings"] = {**data.get("alert_settings", {}), **settings}
    _write_file(data)
