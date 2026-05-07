"""
News fetcher (Google News RSS) + Gemini-based sentiment classifier.

Architecture:
  1. fetch_news(ticker): pulls 5-10 headlines from Google News RSS (English India)
  2. score_headlines_batch(headlines): batches 10 headlines per Gemini call,
     returns [{score, label}, ...]; uses headline-hash dedup so same headline
     across stocks is only LLM'd once
  3. sentiment_for_ticker(ticker): orchestrates fetch + score + cache
"""
import asyncio
import hashlib
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from typing import List, Optional

import feedparser

import cache

logger = logging.getLogger(__name__)

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

# Bound batch sizes
MAX_HEADLINES_PER_TICKER = 5
MAX_BATCH_SIZE = 10  # headlines per LLM call


def _hash(text: str) -> str:
    norm = re.sub(r"\s+", " ", (text or "").strip().lower())
    return hashlib.sha256(norm.encode()).hexdigest()[:16]


# ── 1. Google News RSS fetcher ────────────────────────────────────
def fetch_news(query: str, max_results: int = MAX_HEADLINES_PER_TICKER) -> List[dict]:
    """Fetch headlines from Google News RSS for a ticker / company."""
    try:
        encoded = (query or "").replace(" ", "+")
        url = (f"https://news.google.com/rss/search?"
               f"q={encoded}+NSE+stock+India&hl=en-IN&gl=IN&ceid=IN:en")
        feed = feedparser.parse(url)
        if feed.bozo and not feed.entries:
            return []
        articles = []
        for entry in feed.entries[:max_results]:
            title = getattr(entry, "title", "").strip()
            if not title:
                continue
            articles.append({
                "id": _hash(title),
                "title": title,
                "link": getattr(entry, "link", ""),
                "source": getattr(getattr(entry, "source", None), "title", "Unknown") if hasattr(entry, "source") else "Google News",
                "published": getattr(entry, "published", ""),
            })
        return articles
    except Exception as e:
        logger.error(f"news fetch error for {query}: {e}")
        return []


# ── 2. LLM batch sentiment classifier ─────────────────────────────
async def _score_batch_llm(headlines: List[dict]) -> List[dict]:
    """Batch classify headlines via Gemini 3 Flash. Returns same order as input."""
    if not headlines:
        return []
    if not EMERGENT_LLM_KEY:
        # Fallback: neutral scores
        return [{"id": h["id"], "score": 0.0, "label": "neutral", "source": "no_key"}
                for h in headlines]

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage

        system_msg = (
            "You are a financial-news sentiment classifier. "
            "Classify each headline as bullish, neutral, or bearish for the stock mentioned. "
            "Return ONLY a valid JSON array. No markdown. No commentary."
        )

        # Build prompt
        items = "\n".join([f'{i+1}. "{h["title"]}"' for i, h in enumerate(headlines)])
        user_text = (
            f"Classify these {len(headlines)} headlines.\n\n"
            f"{items}\n\n"
            'Return JSON array of objects: [{"idx": 1, "score": -1.0..1.0, "label": "bullish|neutral|bearish"}, ...]\n'
            "score: -1.0 = strongly bearish, 0.0 = neutral, 1.0 = strongly bullish.\n"
            "Return ONLY the JSON array."
        )

        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"sentiment-{int(time.time()*1000)}",
            system_message=system_msg,
        ).with_model("gemini", "gemini-3-flash-preview")

        response = await chat.send_message(UserMessage(text=user_text))
        text = (response or "").strip()

        # Strip markdown fences if any (defensive — even with response_mime_type)
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            # Try to find array in text
            m = re.search(r"\[.*\]", text, re.DOTALL)
            if m:
                parsed = json.loads(m.group(0))
            else:
                raise

        if not isinstance(parsed, list):
            raise ValueError(f"Expected JSON array, got {type(parsed).__name__}")

        # Normalize: ensure idx 1..N maps back to headlines
        by_idx = {}
        for item in parsed:
            if not isinstance(item, dict):
                continue
            idx = item.get("idx")
            if not isinstance(idx, int) or idx < 1 or idx > len(headlines):
                continue
            score = float(item.get("score", 0))
            score = max(-1.0, min(1.0, score))
            label = str(item.get("label", "neutral")).lower()
            if label not in ("bullish", "neutral", "bearish"):
                label = "bullish" if score > 0.2 else "bearish" if score < -0.2 else "neutral"
            by_idx[idx] = {"score": score, "label": label}

        results = []
        for i, h in enumerate(headlines):
            scored = by_idx.get(i + 1, {"score": 0.0, "label": "neutral"})
            results.append({
                "id": h["id"],
                "score": scored["score"],
                "label": scored["label"],
                "source": "gemini-3-flash",
            })
        return results

    except Exception as e:
        logger.error(f"LLM batch sentiment failed: {e}")
        # Fallback: neutral on every headline
        return [{"id": h["id"], "score": 0.0, "label": "neutral", "source": "llm_error"}
                for h in headlines]


async def score_headlines_batch(headlines: List[dict]) -> List[dict]:
    """Score headlines with per-headline dedup cache + batched LLM calls."""
    if not headlines:
        return []

    # Split into cached vs uncached
    out_by_id = {}
    uncached = []
    for h in headlines:
        cached = cache.get_headline_sentiment(h["id"])
        if cached:
            out_by_id[h["id"]] = cached
        else:
            uncached.append(h)

    # Batch the uncached ones (max MAX_BATCH_SIZE per LLM call)
    for i in range(0, len(uncached), MAX_BATCH_SIZE):
        batch = uncached[i:i + MAX_BATCH_SIZE]
        scored = await _score_batch_llm(batch)
        for s in scored:
            cache.set_headline_sentiment(s["id"], s)
            out_by_id[s["id"]] = s

    # Return in input order
    return [out_by_id.get(h["id"], {"id": h["id"], "score": 0.0, "label": "neutral"})
            for h in headlines]


# ── 3. Per-ticker sentiment orchestrator ──────────────────────────
async def sentiment_for_ticker(ticker: str, company_name: Optional[str] = None,
                               force_refresh: bool = False) -> dict:
    """Compute aggregate sentiment for a ticker. Returns:
       { ticker, state, score, label, computed_at, headlines: [...] }
    """
    ticker = ticker.upper().replace(".NS", "")
    if not force_refresh:
        cached = cache.get_sentiment(ticker)
        if cached:
            return cached

    query = company_name or ticker
    articles = fetch_news(query, MAX_HEADLINES_PER_TICKER)
    if not articles:
        result = {
            "ticker": ticker,
            "state": "unavailable",
            "score": 0.0,
            "label": "neutral",
            "headline_count": 0,
            "headlines": [],
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }
        cache.set_sentiment(ticker, result, ttl=1800)  # shorter TTL: re-check sooner
        return result

    cache.set_news(ticker, articles)

    scored = await score_headlines_batch(articles)
    by_id = {s["id"]: s for s in scored}

    # Aggregate score
    scores = [by_id[a["id"]]["score"] for a in articles if a["id"] in by_id]
    avg_score = sum(scores) / len(scores) if scores else 0.0
    label = "bullish" if avg_score > 0.15 else "bearish" if avg_score < -0.15 else "neutral"

    headlines_with_sent = []
    for a in articles:
        s = by_id.get(a["id"], {"score": 0.0, "label": "neutral"})
        headlines_with_sent.append({
            "title": a["title"],
            "link": a["link"],
            "source": a["source"],
            "published": a.get("published", ""),
            "score": s["score"],
            "label": s["label"],
        })

    result = {
        "ticker": ticker,
        "state": "ok",
        "score": round(avg_score, 3),
        "label": label,
        "headline_count": len(articles),
        "headlines": headlines_with_sent,
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }
    cache.set_sentiment(ticker, result, ttl=3600)
    return result


# ── Sync wrapper for non-async callers (background worker) ────────
def sentiment_for_ticker_sync(ticker: str, company_name: Optional[str] = None,
                              force_refresh: bool = False) -> dict:
    return asyncio.run(sentiment_for_ticker(ticker, company_name, force_refresh))


# ── Market-wide aggregate (over a list of tickers) ────────────────
def aggregate_market_sentiment(tickers: List[str]) -> dict:
    """Returns market-wide sentiment from already-cached per-ticker sentiments."""
    bullish = neutral = bearish = 0
    total_score = 0.0
    counted = 0
    for t in tickers:
        s = cache.get_sentiment(t.upper().replace(".NS", ""))
        if not s or s.get("state") != "ok":
            continue
        counted += 1
        total_score += s["score"]
        if s["label"] == "bullish": bullish += 1
        elif s["label"] == "bearish": bearish += 1
        else: neutral += 1

    avg = round(total_score / counted, 3) if counted else 0.0
    overall = "bullish" if avg > 0.15 else "bearish" if avg < -0.15 else "neutral"
    return {
        "score": avg,
        "label": overall,
        "counts": {"bullish": bullish, "neutral": neutral, "bearish": bearish},
        "tickers_with_data": counted,
        "tickers_total": len(tickers),
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }
