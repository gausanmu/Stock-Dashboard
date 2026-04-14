# NSE Autonomous Quant Engine - PRD

## Original Problem Statement
Build a professional web-based dashboard for high-conviction investment decision-making in the Indian Equity Market (NSE/BSE). Autonomous multi-factor analysis engine with regime classification, quality scoring, trade type recommendations, news sentiment analysis, and portfolio management with Gainer/Stayer/Quitter strategy.

## Architecture
- **Backend**: FastAPI (Python) + MongoDB + yfinance + GPT-5-nano (sentiment)
- **Frontend**: React + Tailwind CSS + Shadcn/UI + Recharts
- **Data Source**: yfinance (NSE stock data), Google News RSS (news)
- **AI**: OpenAI GPT-5-nano via Emergent LLM Key (cheapest model for credit efficiency)
- **Email**: Resend (infrastructure ready, needs API key)
- **Database**: MongoDB (stocks, watchlist, portfolio, news_cache, regime_changes, alert_settings)

## What's Implemented (April 13, 2026)

### Phase 1 (Complete)
- [x] Full backend API (22+ endpoints)
- [x] Analysis engine: RSI, SMA, ATR, quality scoring, regime classification, GSQ tagging
- [x] Background scanner with progress tracking
- [x] Professional dark-mode dashboard
- [x] Macro ticker tape, confidence widget, regime columns
- [x] Full stock table with sorting
- [x] Deep dive sheet with price chart, fundamentals, technicals
- [x] Watchlist/Portfolio CRUD with P&L

### Phase 2 (Complete)
- [x] Trade type classification (SCALP/SWING/INVEST/HOLD/AVOID)
- [x] News sentiment analysis (GPT-5-nano, 6hr cache, credit-efficient)
- [x] Expanded universe: 286 stocks (Nifty 50/100/200+/Full Market)
- [x] Sector heatmap with performance visualization
- [x] Regime change detection + history tracking
- [x] Email alert infrastructure (ready for Resend API key)
- [x] Alerts tab with regime change log

## Prioritized Backlog
### P1 (Next)
- Auto-scheduled scanning (cron-based daily/overnight scan)
- Activate email alerts (needs Resend API key: re_...)
- Stock comparison tool (side-by-side analysis)
- Custom screener builder (ROE > X AND D/E < Y filters)

### P2 (Future)
- Historical regime tracking timeline
- Portfolio correlation matrix
- Backtesting engine
- Telegram bot alerts
- Export reports (PDF/CSV)
