import feedparser
import logging

logger = logging.getLogger(__name__)

class NewsSentimentEngine:
    def __init__(self):
        # Sentiment engine is now local/free
        pass

    def fetch_news(self, query, max_results=8):
        try:
            encoded = query.replace(" ", "+")
            url = f"https://news.google.com/rss/search?q={encoded}+NSE+stock+India&hl=en-IN&gl=IN&ceid=IN:en"
            feed = feedparser.parse(url)
            return [{"title": entry.title, "link": entry.link, "source": entry.source.get('title', 'Unknown')} 
                    for entry in feed.entries[:max_results]]
        except Exception as e:
            logger.error(f"News fetch error: {e}")
            return []

    async def analyze_sentiment_batch(self, headlines):
        results = []
        for h in headlines:
            text = h.lower()
            score = 50
            # Local keyword-based sentiment logic
            if any(w in text for w in ["profit", "growth", "high", "dividend", "buy", "record"]): 
                score += 20
            if any(w in text for w in ["loss", "debt", "fall", "caution", "low", "investigation"]): 
                score -= 20
            
            s = "BULLISH" if score > 60 else "BEARISH" if score < 40 else "NEUTRAL"
            results.append({"s": s, "sc": score, "r": "Local Keyword Logic"})
        return results