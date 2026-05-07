"""
Two-tier cache layer:
  L1: In-process TTLCache (fast, bounded, per-process)
  L2: MongoDB collection with TTL index (durable across restarts, shared)

Typed wrappers per data class so TTLs are explicit and consistent.
"""
import logging
import threading
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from cachetools import TTLCache

import db

logger = logging.getLogger(__name__)

# ── L1: in-process bounded caches ─────────────────────────────────
# (maxsize prevents memory blow-up if a runaway loop floods them)
L1_TICKER = TTLCache(maxsize=1000, ttl=300)        # 5 min
L1_NEWS = TTLCache(maxsize=1000, ttl=3600)         # 1 hour
L1_FUNDA = TTLCache(maxsize=1000, ttl=86400)       # 24 hour
L1_SENTI = TTLCache(maxsize=1000, ttl=3600)        # 1 hour
_l1_lock = threading.Lock()


# ── L2: MongoDB-backed cache ──────────────────────────────────────
def _coll(name: str):
    if not db._use_mongo:
        return None
    return db._db[name]


def ensure_indexes():
    """Create TTL + lookup indexes. Idempotent — safe to call on every boot."""
    if not db._use_mongo:
        logger.info("cache: skipping index creation (JSON fallback mode)")
        return
    try:
        # ── Cache collections (TTL on `expires_at`) ──────────────
        for cname in ("ticker_cache", "news_cache", "fundamental_cache", "sentiment_cache"):
            db._db[cname].create_index("expires_at", expireAfterSeconds=0)
            db._db[cname].create_index("key", unique=True)

        # ── Scan results: index by universe + timestamp ──────────
        db._db.scan_results.create_index([("universe", 1), ("scan_id", -1)])
        db._db.scan_results.create_index("timestamp")
        db._db.scan_runs.create_index([("universe", 1), ("started_at", -1)])

        # ── Distributed lock collection (TTL on expires_at) ──────
        db._db.scan_locks.create_index("expires_at", expireAfterSeconds=0)
        db._db.scan_locks.create_index("key", unique=True)

        # ── Error log ────────────────────────────────────────────
        db._db.error_log.create_index("timestamp")
        db._db.error_log.create_index([("ticker", 1), ("timestamp", -1)])

        # ── Failures tracker (consecutive failures per ticker) ───
        db._db.ticker_failures.create_index("ticker", unique=True)

        # ── Existing collection indexes ──────────────────────────
        db._db.portfolio.create_index("ticker", unique=True)
        db._db.watchlist.create_index("ticker", unique=True)
        db._db.regime_changes.create_index([("ticker", 1), ("timestamp", -1)])
        logger.info("cache: indexes ensured")
    except Exception as e:
        logger.error(f"cache: index creation failed: {e}")


# ── Generic L2 helpers ────────────────────────────────────────────
def _l2_get(coll_name: str, key: str) -> Optional[Any]:
    c = _coll(coll_name)
    if c is None:
        return None
    try:
        doc = c.find_one({"key": key}, {"_id": 0})
        if not doc:
            return None
        # belt-and-braces: TTL cleaner runs every 60s, so re-check
        expires = doc.get("expires_at")
        if expires:
            # MongoDB may return naive datetimes — normalize to UTC-aware
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if expires < datetime.now(timezone.utc):
                return None
        return doc.get("value")
    except Exception as e:
        logger.error(f"L2 get {coll_name}/{key}: {e}")
        return None


def _l2_set(coll_name: str, key: str, value: Any, ttl_seconds: int):
    c = _coll(coll_name)
    if c is None:
        return
    try:
        c.update_one(
            {"key": key},
            {"$set": {
                "key": key,
                "value": value,
                "expires_at": datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds),
                "updated_at": datetime.now(timezone.utc),
            }},
            upsert=True,
        )
    except Exception as e:
        logger.error(f"L2 set {coll_name}/{key}: {e}")


# ── Typed accessors ───────────────────────────────────────────────
def get_ticker(ticker: str) -> Optional[dict]:
    with _l1_lock:
        v = L1_TICKER.get(ticker)
        if v is not None:
            return v
    v = _l2_get("ticker_cache", ticker)
    if v is not None:
        with _l1_lock:
            L1_TICKER[ticker] = v
    return v


def set_ticker(ticker: str, data: dict, ttl: int = 900):
    with _l1_lock:
        L1_TICKER[ticker] = data
    _l2_set("ticker_cache", ticker, data, ttl)


def get_news(ticker: str) -> Optional[list]:
    with _l1_lock:
        v = L1_NEWS.get(ticker)
        if v is not None:
            return v
    v = _l2_get("news_cache", ticker)
    if v is not None:
        with _l1_lock:
            L1_NEWS[ticker] = v
    return v


def set_news(ticker: str, articles: list, ttl: int = 3600):
    with _l1_lock:
        L1_NEWS[ticker] = articles
    _l2_set("news_cache", ticker, articles, ttl)


def get_fundamental(ticker: str) -> Optional[dict]:
    with _l1_lock:
        v = L1_FUNDA.get(ticker)
        if v is not None:
            return v
    v = _l2_get("fundamental_cache", ticker)
    if v is not None:
        with _l1_lock:
            L1_FUNDA[ticker] = v
    return v


def set_fundamental(ticker: str, data: dict, ttl: int = 86400):
    with _l1_lock:
        L1_FUNDA[ticker] = data
    _l2_set("fundamental_cache", ticker, data, ttl)


def get_sentiment(ticker: str) -> Optional[dict]:
    with _l1_lock:
        v = L1_SENTI.get(ticker)
        if v is not None:
            return v
    v = _l2_get("sentiment_cache", ticker)
    if v is not None:
        with _l1_lock:
            L1_SENTI[ticker] = v
    return v


def set_sentiment(ticker: str, data: dict, ttl: int = 3600):
    with _l1_lock:
        L1_SENTI[ticker] = data
    _l2_set("sentiment_cache", ticker, data, ttl)


# ── Per-headline sentiment dedup (avoid re-LLM same headline) ─────
def get_headline_sentiment(headline_hash: str) -> Optional[dict]:
    return _l2_get("headline_sentiment_cache", headline_hash)


def set_headline_sentiment(headline_hash: str, data: dict, ttl: int = 86400 * 3):
    _l2_set("headline_sentiment_cache", headline_hash, data, ttl)


# ── Distributed scan lock (Mongo-based, race-safe) ────────────────
def acquire_scan_lock(key: str, ttl_seconds: int = 600) -> bool:
    """Returns True if lock acquired, False if already held by someone else."""
    c = _coll("scan_locks")
    if c is None:
        return True  # JSON fallback: assume single process
    now = datetime.now(timezone.utc)
    try:
        # Atomic upsert: only succeeds if no doc exists OR existing doc expired
        c.find_one_and_update(
            {
                "key": key,
                "$or": [{"expires_at": {"$lt": now}}, {"expires_at": {"$exists": False}}],
            },
            {"$set": {
                "key": key,
                "locked_at": now,
                "expires_at": now + timedelta(seconds=ttl_seconds),
            }},
            upsert=True,
            return_document=False,
        )
        # If upsert inserted (no previous doc) OR previous lock had expired → we got it
        return True
    except Exception as e:
        # Duplicate key error → another process holds active lock
        logger.info(f"scan lock {key} held by another process: {e}")
        return False


def release_scan_lock(key: str):
    c = _coll("scan_locks")
    if c is None:
        return
    try:
        c.delete_one({"key": key})
    except Exception as e:
        logger.error(f"release lock {key}: {e}")


# ── Error logging ─────────────────────────────────────────────────
def log_error(ticker: str, error_type: str, message: str, context: dict = None):
    if not db._use_mongo:
        return
    try:
        db._db.error_log.insert_one({
            "ticker": ticker,
            "error_type": error_type,
            "message": str(message)[:500],
            "context": context or {},
            "timestamp": datetime.now(timezone.utc),
        })
    except Exception as e:
        logger.error(f"log_error: {e}")


def record_ticker_failure(ticker: str) -> int:
    """Increment failure count, return new count."""
    if not db._use_mongo:
        return 0
    try:
        doc = db._db.ticker_failures.find_one_and_update(
            {"ticker": ticker},
            {"$inc": {"count": 1}, "$set": {"last_failure": datetime.now(timezone.utc)}},
            upsert=True,
            return_document=True,
        )
        return doc.get("count", 1) if doc else 1
    except Exception as e:
        logger.error(f"record_ticker_failure: {e}")
        return 0


def reset_ticker_failure(ticker: str):
    if not db._use_mongo:
        return
    try:
        db._db.ticker_failures.delete_one({"ticker": ticker})
    except Exception:
        pass


def is_ticker_blacklisted(ticker: str, threshold: int = 3) -> bool:
    """Returns True if ticker has failed >= threshold times in last 24h."""
    if not db._use_mongo:
        return False
    try:
        doc = db._db.ticker_failures.find_one({"ticker": ticker})
        if not doc:
            return False
        if doc.get("count", 0) < threshold:
            return False
        last = doc.get("last_failure")
        if last:
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            if (datetime.now(timezone.utc) - last).total_seconds() > 86400:
                # Auto-recover after 24h
                reset_ticker_failure(ticker)
                return False
        return True
    except Exception:
        return False


def health_summary() -> dict:
    """Return summary stats for /api/admin/health."""
    if not db._use_mongo:
        return {"mode": "json_fallback"}
    try:
        def _hit_rate(cache):
            if hasattr(cache, 'hits') and hasattr(cache, 'misses'):
                total = cache.hits + cache.misses
                return round(cache.hits / total * 100, 2) if total > 0 else 0
            # Note: cachetools TTLCache natively doesn't track hits/misses unless wrapped or custom
            # We'll approximate or return N/A if not tracking
            return "N/A"
            
        out = {
            "mode": "mongodb",
            "l1_cache_sizes": {
                "ticker": len(L1_TICKER),
                "news": len(L1_NEWS),
                "fundamental": len(L1_FUNDA),
                "sentiment": len(L1_SENTI)
            },
            "ticker_cache": db._db.ticker_cache.estimated_document_count(),
            "news_cache": db._db.news_cache.estimated_document_count(),
            "sentiment_cache": db._db.sentiment_cache.estimated_document_count(),
            "fundamental_cache": db._db.fundamental_cache.estimated_document_count(),
            "blacklisted_tickers": db._db.ticker_failures.count_documents({"count": {"$gte": 3}}),
            "errors_last_24h": db._db.error_log.count_documents({
                "timestamp": {"$gt": datetime.now(timezone.utc) - timedelta(hours=24)}
            }),
        }
        return out
    except Exception as e:
        return {"mode": "mongodb", "error": str(e)}
