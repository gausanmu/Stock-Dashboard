"""Phase 3 NSE Quant Engine: Universe expansion + News Sentiment + Fundamental Health.

Tests all new endpoints from review_request, plus regression for portfolio/watchlist.
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://stock-tracker-1346.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ---------- Scan / Universe ----------
class TestScanLevels:
    def test_scan_levels_returns_eight_universes(self, client):
        r = client.get(f"{API}/scan/levels", timeout=30)
        assert r.status_code == 200
        data = r.json()
        expected = {"nifty50", "nifty100", "nifty200", "nifty500", "midcap", "smallcap", "fno", "penny"}
        assert expected.issubset(set(data.keys())), f"Missing universes: {expected - set(data.keys())}"
        for k, v in data.items():
            assert "label" in v and "count" in v and "est_minutes" in v and "tier" in v
            assert isinstance(v["count"], int) and v["count"] > 0
            assert v["tier"] in {"fast", "medium", "deep"}


class TestAdminHealth:
    def test_admin_health(self, client):
        r = client.get(f"{API}/admin/health", timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert "scan_state" in data and "cache" in data
        assert data["cache"].get("mode") == "mongodb"


class TestFnoIndices:
    def test_fno_indices_list(self, client):
        r = client.get(f"{API}/fno/indices", timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list) and len(data) >= 5
        names = {d["name"] for d in data}
        for required in ("NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCAPNIFTY", "NIFTYIT"):
            assert required in names, f"Missing index: {required}"
        for d in data:
            assert "price" in d and "change_pct" in d


# ---------- Fundamentals ----------
class TestFundamentals:
    def test_fundamentals_reliance_refresh(self, client):
        r = client.get(f"{API}/fundamentals/RELIANCE?refresh=true", timeout=60)
        assert r.status_code == 200
        d = r.json()
        assert d["ticker"] == "RELIANCE"
        assert d["state"] == "ok"
        assert 0 <= d["score"] <= 100
        assert d["grade"] in {"A+", "A", "B", "C", "D", "F"}
        assert isinstance(d["components"], dict)
        assert isinstance(d["drivers"], list)
        assert isinstance(d["raw"], dict)

    def test_fundamentals_caching(self, client):
        # warm cache
        client.get(f"{API}/fundamentals/RELIANCE", timeout=60)
        t1 = time.time()
        r2 = client.get(f"{API}/fundamentals/RELIANCE", timeout=60)
        elapsed = time.time() - t1
        assert r2.status_code == 200
        # cached should be reasonably fast (< 5s)
        assert elapsed < 5, f"Cached call too slow: {elapsed:.2f}s"


# ---------- Sentiment / News ----------
class TestSentiment:
    def test_sentiment_reliance(self, client):
        r = client.get(f"{API}/sentiment/RELIANCE?refresh=true", timeout=90)
        assert r.status_code == 200
        d = r.json()
        assert d["ticker"] == "RELIANCE"
        assert d["state"] in {"ok", "processing", "unavailable"}
        if d["state"] == "ok":
            assert -1.0 <= d["score"] <= 1.0
            assert d["label"] in {"bullish", "neutral", "bearish"}
            assert "headline_count" in d
            assert "computed_at" in d

    def test_news_reliance_full(self, client):
        r = client.get(f"{API}/news/RELIANCE", timeout=60)
        assert r.status_code == 200
        d = r.json()
        assert d["ticker"] == "RELIANCE"
        assert "headlines" in d
        assert isinstance(d["headlines"], list)
        if d["headlines"]:
            h0 = d["headlines"][0]
            assert "title" in h0
            # score/label may be present
            if "score" in h0:
                assert -1.0 <= h0["score"] <= 1.0

    def test_sentiment_market_nifty50(self, client):
        r = client.get(f"{API}/sentiment/market/nifty50", timeout=60)
        assert r.status_code == 200
        d = r.json()
        assert "score" in d and "label" in d
        assert d["label"] in {"bullish", "neutral", "bearish"}
        assert "counts" in d
        for k in ("bullish", "neutral", "bearish"):
            assert k in d["counts"]
        assert "tickers_with_data" in d


# ---------- Scan Start / Status / Results ----------
class TestScanFlow:
    def test_scan_start_nifty50(self, client):
        r = client.post(f"{API}/scan/start", json={"universe": "nifty50", "profile": "LONG_TERM"}, timeout=30)
        assert r.status_code == 200
        d = r.json()
        # accepts both "started" and "already_running"
        assert d.get("status") in {"started", "already_running"} or "status" in d

    def test_scan_status(self, client):
        r = client.get(f"{API}/scan/status", timeout=30)
        assert r.status_code == 200
        d = r.json()
        for k in ("running", "progress", "total", "current_ticker", "status"):
            assert k in d, f"Missing field {k}"

    def test_scan_results_nifty50(self, client):
        r = client.get(f"{API}/scan/results?universe=nifty50", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert "results" in d
        assert isinstance(d["results"], list)

    def test_scan_refresh(self, client):
        r = client.post(f"{API}/scan/refresh", timeout=30)
        assert r.status_code == 200

    def test_sentiment_refresh(self, client):
        r = client.post(f"{API}/sentiment/refresh?universe=nifty50&limit=5", timeout=30)
        assert r.status_code in (200, 202)


# ---------- Regression: portfolio + watchlist ----------
class TestPortfolioRegression:
    TICKER = "TEST_REL"

    def test_add_portfolio(self, client):
        r = client.post(
            f"{API}/portfolio",
            json={"ticker": "RELIANCE", "buy_price": 1000, "quantity": 5},
            timeout=30,
        )
        assert r.status_code in (200, 201)

    def test_get_portfolio(self, client):
        r = client.get(f"{API}/portfolio", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert "items" in d or isinstance(d, list)

    def test_remove_portfolio(self, client):
        r = client.delete(f"{API}/portfolio/RELIANCE", timeout=30)
        assert r.status_code in (200, 204, 404)


class TestWatchlistRegression:
    def test_add_watchlist(self, client):
        r = client.post(f"{API}/watchlist", json={"ticker": "TCS"}, timeout=30)
        assert r.status_code in (200, 201)

    def test_get_watchlist(self, client):
        r = client.get(f"{API}/watchlist", timeout=30)
        assert r.status_code == 200

    def test_remove_watchlist(self, client):
        r = client.delete(f"{API}/watchlist/TCS", timeout=30)
        assert r.status_code in (200, 204, 404)
