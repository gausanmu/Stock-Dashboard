# NSE Quant Engine - Comprehensive Logic Document

This document covers every mechanism, calculation, and workflow powering the NSE Quant Engine backend.

---

## 1. Technical Analysis Engine (`analysis_engine.py`)

The core engine that calculates technical indicators, scores them based on a weighted system, and assigns a specific "regime" (trade setup) to a stock.

### Indicators Calculated
- **Moving Averages:** Simple (SMA50, SMA200) and Exponential (EMA9, EMA20, EMA50)
- **RSI (Relative Strength Index):** 14-period momentum oscillator.
- **MACD (Moving Average Convergence Divergence):** Standard (12, 26, 9). Line, Signal, and Histogram are computed.
- **ATR (Average True Range):** 14-period volatility measure.
- **Bollinger Bands:** 20-period SMA with ±2 standard deviations.
- **ADX (Average Directional Index):** 14-period trend strength indicator (0-100).
- **VWAP (Volume Weighted Average Price):** 20-period proxy based on (High+Low+Close)/3 * Volume.
- **Volume Ratio:** Current volume divided by 20-day average volume.
- **52-Week High/Low:** Max/Min price over the last 252 trading periods, and distance from current price.

### Scoring Logic
The engine uses three sub-scores that feed into a master score based on the user's selected profile:

#### Trend Score (0.0 to 1.0)
- Price > SMA200: +0.4
- Price > SMA50: +0.3
- EMA20 > EMA50: +0.3
- EMA20 < EMA50: -0.2

#### Momentum Score (0.0 to 1.0)
- 50 < RSI < 70: +0.6
- RSI >= 70 (Overbought but strong): +0.3
- 30 < RSI <= 50: +0.2
- MACD Histogram > 0: +0.4

#### Volatility Score (0.0 to 1.0)
- ADX > 20: +0.5
- ADX > 25: +0.2
- Position within Bollinger Bands (Price - Lower Band / Band Width):
  - 0.5 to 0.9 (Trending up but not hitting upper band): +0.3
  - >= 0.9 (Near breakout): +0.1

#### Master Weights (Default)
- Trend: 50%
- Momentum: 30%
- Volatility: 20%

### Regime Classification & Thresholds
Total scores are evaluated against thresholds: `STRONG_BUY (0.75), BUY (0.60), NEUTRAL (0.40), SELL (0.25)`.
Based on the **Profile**, different regimes are assigned:

**LONG_TERM Profile:**
- **WEALTH_BUILDER**: Buy threshold met + Quality Score >= 70 + Debt/Equity < 60
- **DIVIDEND_KING**: Buy threshold met + Dividend Yield >= 2.5% + Quality Score >= 60
- **COMPOUNDER**: Buy threshold met + Quality Score >= 60
- **VALUE_PICK**: Price < SMA200 * 0.85 + Quality Score >= 60 + RSI < 40
- **AVOID**: Quality Score < 45 OR Total Score < SELL threshold
- **NEUTRAL**: Anything else

**SWING Profile:**
- **BREAKOUT_LONG**: Buy threshold met + Price > Bollinger Upper Band + RSI > 55
- **EMA_TREND_LONG**: Buy threshold met (standard trend following)
- **MEAN_REVERSION_LONG**: Price < Bollinger Lower Band + RSI < 35
- **SWING_SHORT**: Score < SELL threshold + EMA20 < EMA50
- **RANGE_BOUND**: Score < NO_TRADE threshold but ADX < 20
- **NO_TRADE**: Score < NO_TRADE threshold

**SHORT_TERM Profile (Intraday/2-day):**
- **INTRADAY_LONG**: Buy threshold met + Price > VWAP
- **INTRADAY_SHORT**: Sell threshold met + Price < VWAP
- **FLAT**: Score < NO_TRADE threshold OR ATR% < 0.6% (Too little volatility to trade)

---

## 2. Fundamental Health Engine (`fundamental_health.py`)

A pure mathematical scoring system evaluating a company's balance sheet, returning a score from 0-100 and a letter grade (A+ to F).

### Scoring Buckets
1. **ROE (0-25 pts)**: >=25% (25), >=15% (20), >=8% (12), >=3% (6).
2. **Debt/Equity (0-20 pts)**: <30 (20), <60 (15), <100 (8), <200 (3). Lower is better. Unknown = 10.
3. **Profit Margin (0-15 pts)**: >=20% (15), >=10% (11), >=5% (6), >0% (2).
4. **Earnings Growth (0-15 pts)**: >=25% (15), >=10% (10), >=0% (5).
5. **Revenue Growth (0-10 pts)**: >=20% (10), >=8% (7), >=0% (3).
6. **P/E Ratio (0-10 pts - "Goldilocks")**: 12 to 28 (10), 8 to 12 OR 28 to 45 (6), >45 (2), <8 (3 - penalize "too cheap/value trap").
7. **Free Cash Flow (0-5 pts)**: >0 (5), <=0 (0), Unknown (2).

### Grading
- >= 80: A+
- >= 70: A
- >= 60: B
- >= 45: C
- >= 30: D
- < 30: F

---

## 3. Recommendation Engine (`recommendation_engine.py`)

Takes the analysis result, the user's buy price, and profile to generate actionable advice (Target, Stop Loss, Holding Period, Action, Rationale).

### Profile Targets & Stops
- **SHORT_TERM**: 
  - Target: 1.2% - 2.0% (depending on regime)
  - Stop: Max(0.8 * ATR, 0.5% of price)
  - Holding: 1-2 days
- **SWING**: 
  - Target: 6.0% - 12.0%
  - Stop: Max(1.5 * ATR, 2.5% of price)
  - Holding: 5-25 days
- **LONG_TERM**: 
  - Target: 20.0% - 45.0%
  - Stop: Max(Distance to SMA200, 12% trailing stop)
  - Holding: 6-36 months

### Actions Generated
- **SELL**: Current price <= Stop price.
- **BOOK_PROFIT**: Current price >= Target price.
- **PARTIAL_BOOK**: Reached 80% of target (Long term) OR RSI > 75 (overheated).
- **EXIT**: Quality dropped < 45 or Regime flipped to AVOID.
- **ADD**: Pullback to support (Price > SMA50, RSI < 35 in Swing mode).
- **HOLD**: Price is between stop and target, trend intact.

---

## 4. Risk Manager (`risk_manager.py`)

Handles position sizing, portfolio correlation, transaction costs, and global drawdown.

### 1. Modified Kelly Criterion (Position Sizing)
Determines how many shares to buy to prevent account blowout.
- Uses a baseline Win Rate of 55% and Win/Loss ratio of 2.0.
- Calculates `Kelly % = W - [(1-W)/R]`.
- Applies "Half-Kelly" for safety, capped at a global `max_risk_pct` (default 2% of total account size per trade).
- Calculates the maximum loss per share (Current Price - Stop Loss Price).
- Returns the exact number of shares to buy so that if the stop loss is hit, the account only loses 2%.

### 2. Correlation Check
Prevents buying stocks that move identically to what you already own.
- Downloads 3-month price history for the target stock and all existing portfolio stocks.
- Computes Pearson correlation matrix.
- Flags any stock with >0.7 correlation to existing holdings.

### 3. Net Return Calculator (Indian Market Structure)
Calculates exact PnL after all Indian transaction costs (Zerodha style):
- Brokerage: 0 for delivery, min(20, 0.03%) for intraday.
- STT: 0.1% for delivery.
- Exchange Txn Charge: 0.00345%.
- GST: 18% on (Brokerage + Exchange).
- SEBI + Stamp Duty.

### 4. Portfolio Exposure
Monitors the whole portfolio against limits:
- Max Portfolio Drawdown (default 15%). Halts trading if exceeded.
- Max Sector Allocation (default 30%). Warns if too concentrated in one sector.

---

## 5. Background Scanner & Scheduler (`scan_worker.py`)

Automates the heavy lifting of analyzing the entire stock market.

### Architecture
- Runs `APScheduler` in the background within the FastAPI process.
- Uses a MongoDB-backed distributed lock (`scan_locks` collection) to ensure two workers don't run the same scan at the same time.
- Schedules:
  - **Every 20 mins (Market Hours 09:15-15:30 IST)**: Refreshes fast universes (Nifty 50, Nifty 100, F&O).
  - **Once a day (16:00 IST)**: Deep refresh of all universes (Nifty 500, Smallcap, Penny).

### Process
1. Fetches universe tickers (e.g., all 500 stocks in NIFTY 500).
2. Iterates through them, passing each to `fetch_ticker()` and then `AnalysisEngine`.
3. Detects "Regime Changes" (e.g., a stock flipped from NEUTRAL to BREAKOUT_LONG) and logs them to MongoDB.
4. Writes the final batch results to MongoDB `scan_results` (keeping the last 3 versions per universe) and updates the in-memory progress `scan_state` for the frontend progress bar.

---

## 6. Yahoo Finance Fetcher (`yf_fetcher.py`)

A highly resilient wrapper around the `yfinance` library to prevent IP bans and handle bad data.

### Protections
- **Concurrency Limit:** Max 5 parallel requests (Semaphore).
- **Global Rate Limit:** Enforces `MIN_INTERVAL_S` (1.2s) between any two calls to prevent HTTP 429 Too Many Requests.
- **User-Agent Rotation:** Uses `curl_cffi` to impersonate real browsers (Chrome, Safari, Firefox) and rotates headers.
- **Exponential Backoff:** If a fetch fails, it retries in 5s, 15s, then 45s.
- **Blacklisting:** If a ticker fails 3 times, it is blacklisted for 24 hours to prevent it from stalling the scanner.
- **Data Quality:** Rejects empty data, 0 price, 0 volume, or data older than 4 trading days (stale data).

---

## 7. News & Sentiment Engine (`news_sentiment.py`)

Fetches latest news and uses LLMs to score market sentiment.

### Workflow
1. **Fetch:** Hits Google News RSS specifically scoped to Indian markets (`hl=en-IN&gl=IN&ceid=IN:en`). Pulls the top 5 recent headlines for a stock.
2. **De-duplication:** Hashes the headline. If that exact headline was analyzed before (even for a different stock), it skips the LLM call and uses the cached score.
3. **LLM Batching:** Groups up to 10 uncached headlines and sends a single prompt to Google Gemini 3 Flash.
4. **Scoring:** The LLM returns a JSON array scoring each headline from -1.0 (strongly bearish) to +1.0 (strongly bullish).
5. **Aggregation:** Averages the headline scores for a stock. >0.15 is Bullish, <-0.15 is Bearish, else Neutral.
6. **Market Sentiment:** The `/api/sentiment/market/{universe}` endpoint aggregates the individual stock sentiments to determine if the whole market is bullish or bearish.

---

## 8. Persistence & Caching (`db.py` & `cache.py`)

### Two-Tier Cache (`cache.py`)
- **L1 (In-Memory)**: Uses `cachetools.TTLCache`. Ultra-fast, bounded memory (max 1000 items), short TTLs (5-15 mins).
- **L2 (MongoDB)**: Uses MongoDB TTL indexes. Survives app restarts. 

### Dual-Mode Database (`db.py`)
Because Render Free Tier puts the backend to sleep and doesn't provide a database:
- Tries to connect to `MONGO_URL`.
- If MongoDB fails or isn't provided, it falls back to a **local JSON file** (`stock_dashboard_db.json`). 
- This ensures the app never crashes on boot, even if the database is down, allowing it to run entirely in RAM + JSON on free tiers.

---

## 9. Universes (`nse_universe.py`)

Static, hardcoded lists of NSE stock symbols categorized into:
- NIFTY_50
- NIFTY_NEXT_50
- NIFTY_MIDCAP_100
- NIFTY_SMALLCAP_100
- NIFTY_SMALLCAP_EXTRA (To make up the NIFTY 500)
- FNO_UNDERLYING (190 stocks eligible for futures & options)
- PENNY (Curated list of highly volatile sub-₹50 stocks)

---

## 10. Alert Service (`alert_service.py`)

Uses the Resend Email API (`RESEND_API_KEY`) to send real-time notifications.
- **Regime Changes**: Sends an immediate HTML email if a stock flips to a critical regime (e.g., NEUTRAL -> COMPOUNDER).
- **Daily Summary**: Sends an EOD summary of all stocks that changed regimes and the total market confidence score.
