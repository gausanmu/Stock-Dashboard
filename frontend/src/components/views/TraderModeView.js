import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import StockCard from "@/components/StockCard";
import { Button } from "@/components/ui/button";
import { Loader2, RefreshCw, Sparkles } from "lucide-react";
import { toast } from "sonner";

/**
 * MODE CONFIG ────────────────────────────────────────────────────
 * Each trader mode has:
 *  - `id`           : profile id sent to backend
 *  - `title`, `subtitle`, `accent`
 *  - `regimes`     : array of buckets (column heads). Each: { key, label, regimes[], desc }
 *  - `description` : info panel content
 */
const MODES = {
  long_term: {
    id: "LONG_TERM",
    title: "Long-Term Investor",
    subtitle: "Build wealth over months and years. Focus on quality + valuation + dividends.",
    accent: "from-emerald-500 to-teal-500",
    pillTone: "emerald",
    description: [
      { h: "What it scans", p: "Strong fundamentals (ROE >15%, low debt, EPS/Revenue growth), price above SMA200, durable trends." },
      { h: "Hold horizon",  p: "6 months → 3 years. Re-evaluate quarterly on results." },
      { h: "Risk controls", p: "Max 10% per stock. Stop-loss on SMA200 break or quality drop." },
    ],
    buckets: [
      { key: "WEALTH_BUILDER",  label: "Wealth Builders",   tone: "emerald", desc: "Highest-quality compounders" },
      { key: "COMPOUNDER",      label: "Compounders",       tone: "emerald", desc: "Steady trend + good fundamentals" },
      { key: "DIVIDEND_KING",   label: "Dividend Kings",    tone: "blue",    desc: "Yield ≥ 2.5% with quality" },
      { key: "VALUE_PICK",      label: "Value Picks",       tone: "violet",  desc: "Quality at a discount" },
      { key: "AVOID",           label: "Avoid",             tone: "rose",    desc: "Weak fundamentals — stay away" },
    ],
  },
  swing: {
    id: "SWING",
    title: "Swing Trader",
    subtitle: "Catch 3-day to 4-week moves. EMA + MACD + Bollinger + ADX setups.",
    accent: "from-amber-500 to-orange-500",
    pillTone: "amber",
    description: [
      { h: "What it scans", p: "Breakouts above Bollinger upper, EMA20/50 trend continuation, MACD crossovers, mean reversion bounces." },
      { h: "Hold horizon",  p: "5 → 25 trading days. Exit on stop or target — whichever hits first." },
      { h: "Risk controls", p: "Stop-loss = 1.5×ATR. Risk:Reward must be ≥ 2:1. Avoid earnings week." },
    ],
    buckets: [
      { key: "BREAKOUT_LONG",       label: "Breakout Longs",     tone: "amber",   desc: "Above Bollinger upper + bullish MACD" },
      { key: "EMA_TREND_LONG",      label: "EMA Trend Longs",    tone: "amber",   desc: "Price > EMA20 > EMA50, MACD up" },
      { key: "MEAN_REVERSION_LONG", label: "Oversold Bounces",   tone: "fuchsia", desc: "Below Bollinger lower + RSI < 35" },
      { key: "SWING_SHORT",         label: "Swing Shorts",       tone: "rose",    desc: "Bearish trend setups" },
      { key: "RANGE_BOUND",         label: "Range / No Trade",   tone: "slate",   desc: "Low ADX — avoid" },
    ],
  },
  short_term: {
    id: "SHORT_TERM",
    title: "Short-Term / Intraday",
    subtitle: "Day-trade momentum. VWAP + EMA9/20 + RSI(14) on daily proxy.",
    accent: "from-fuchsia-500 to-pink-500",
    pillTone: "fuchsia",
    description: [
      { h: "What it scans", p: "Stocks with strong daily momentum, price above/below VWAP, EMA9 vs EMA20 alignment, ATR%>0.6." },
      { h: "Hold horizon",  p: "Same day → 2 days. Trail stops aggressively." },
      { h: "Risk controls", p: "Stop = 0.8×ATR. Max 2 losing trades per day. Book at 1.5–2× risk." },
      { h: "Note",          p: "Currently uses end-of-day yfinance data. For true intraday, plug in Kite/Upstox/Fyers/Dhan API." },
    ],
    buckets: [
      { key: "INTRADAY_LONG",  label: "Intraday Longs",  tone: "fuchsia", desc: "Above VWAP + EMA9 > EMA20 + RSI > 55" },
      { key: "INTRADAY_SHORT", label: "Intraday Shorts", tone: "rose",    desc: "Below VWAP + EMA9 < EMA20 + RSI < 45" },
      { key: "FLAT",           label: "Flat / Skip",     tone: "slate",   desc: "Low volatility — wait for setup" },
    ],
  },
};

const TONE_BG = {
  emerald: "bg-emerald-500/5 border-emerald-500/20",
  amber:   "bg-amber-500/5 border-amber-500/20",
  fuchsia: "bg-fuchsia-500/5 border-fuchsia-500/20",
  blue:    "bg-blue-500/5 border-blue-500/20",
  violet:  "bg-violet-500/5 border-violet-500/20",
  rose:    "bg-rose-500/5 border-rose-500/20",
  slate:   "bg-slate-500/5 border-slate-500/20",
};
const TONE_DOT = {
  emerald: "bg-emerald-400",
  amber:   "bg-amber-400",
  fuchsia: "bg-fuchsia-400",
  blue:    "bg-blue-400",
  violet:  "bg-violet-400",
  rose:    "bg-rose-400",
  slate:   "bg-slate-400",
};

export default function TraderModeView({ mode, onSelectStock, scanStatus, universe = "nifty50" }) {
  const cfg = MODES[mode];
  const [stocks, setStocks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [scanning, setScanning] = useState(false);

  const fetchStocks = useCallback(async () => {
    setLoading(true);
    try {
      // Prefer cached scan results for the chosen universe
      const res = await api.getScanResults(universe, { sort: "quality" });
      let results = res.data?.results || [];
      // Fall back to legacy in-memory if cache empty
      if (results.length === 0) {
        const legacy = await api.getStocks({ profile: cfg.id, sort: "quality" });
        results = legacy.data || [];
      }
      // Filter by profile-relevant regimes
      const myKeys = cfg.buckets.map(b => b.key);
      results = results.filter(s => myKeys.includes(s.regime) || s.profile === cfg.id);
      setStocks(results);
    } catch (e) {
      // silent
    } finally {
      setLoading(false);
    }
  }, [cfg.id, cfg.buckets, universe]);

  useEffect(() => {
    fetchStocks();
  }, [fetchStocks]);

  // Auto-refresh while a scan is running for THIS mode
  useEffect(() => {
    if (scanStatus?.running && scanStatus?.profile === cfg.id) {
      const t = setInterval(fetchStocks, 3500);
      return () => clearInterval(t);
    }
  }, [scanStatus?.running, scanStatus?.profile, cfg.id, fetchStocks]);

  const triggerScan = async () => {
    if (scanStatus?.running) {
      toast.info(`A scan is already running (${scanStatus.profile}).`);
      return;
    }
    setScanning(true);
    try {
      await api.startScan(universe, cfg.id);
      toast.success(`Scanning ${universe} in ${cfg.title} mode…`);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to start scan");
    } finally {
      setScanning(false);
    }
  };

  const grouped = cfg.buckets.map(b => ({
    ...b,
    items: stocks.filter(s => s.regime === b.key),
  }));

  const totalCount = stocks.length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className={`relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br ${cfg.accent} p-6 shadow-xl shadow-black/20`}>
        <div className="absolute inset-0 bg-slate-950/70" />
        <div className="relative flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Sparkles className="w-4 h-4 text-white/80" />
              <span className="text-[11px] uppercase tracking-widest text-white/70 font-semibold">{cfg.id.replace("_", " ")} MODE</span>
            </div>
            <h1 className="text-2xl md:text-3xl font-bold text-white tracking-tight">{cfg.title}</h1>
            <p className="text-sm text-white/70 mt-1 max-w-2xl">{cfg.subtitle}</p>
          </div>
          <div className="flex items-center gap-2">
            <div className="px-3 py-1.5 rounded-md bg-white/10 border border-white/10 text-white text-xs">
              <span className="text-white/60">Stocks scanned</span>
              <span className="ml-2 font-bold tabular-nums">{totalCount}</span>
            </div>
            <Button
              onClick={triggerScan}
              disabled={scanning || scanStatus?.running}
              className="bg-white text-slate-900 hover:bg-white/90 font-semibold"
            >
              {scanStatus?.running && scanStatus?.profile === cfg.id ? (
                <><Loader2 className="w-4 h-4 mr-2 animate-spin" />{scanStatus.progress}/{scanStatus.total}</>
              ) : (
                <><RefreshCw className="w-4 h-4 mr-2" />Scan Now</>
              )}
            </Button>
          </div>
        </div>
      </div>

      {/* Strategy info cards */}
      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-3">
        {cfg.description.map((d, i) => (
          <div key={i} className="bg-white/[0.03] border border-white/5 rounded-xl p-4">
            <div className="text-[10px] uppercase tracking-widest text-slate-500 font-semibold mb-1">{d.h}</div>
            <div className="text-sm text-slate-200 leading-relaxed">{d.p}</div>
          </div>
        ))}
      </div>

      {/* Buckets / regime columns */}
      {loading && stocks.length === 0 ? (
        <div className="text-center py-20 text-slate-400">
          <Loader2 className="w-8 h-8 animate-spin mx-auto mb-3" />
          Loading stocks…
        </div>
      ) : totalCount === 0 ? (
        <div className="bg-white/[0.03] border border-dashed border-white/10 rounded-2xl py-16 text-center">
          <div className="text-slate-300 font-medium mb-1">No stocks scanned for this mode yet</div>
          <div className="text-sm text-slate-500 mb-4">Click "Scan Now" above to analyze Nifty 50 in {cfg.title} mode.</div>
          <Button onClick={triggerScan} disabled={scanStatus?.running} className="bg-gradient-to-r from-emerald-500 to-cyan-500 text-slate-950">
            <RefreshCw className="w-4 h-4 mr-2" /> Run Scan
          </Button>
        </div>
      ) : (
        <div className={`grid gap-4 ${grouped.length <= 3 ? "md:grid-cols-3" : "md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-5"}`}>
          {grouped.map(b => (
            <div key={b.key} className={`rounded-xl p-3 border ${TONE_BG[b.tone] || TONE_BG.slate}`}>
              <div className="flex items-center justify-between mb-2 px-1">
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${TONE_DOT[b.tone] || TONE_DOT.slate}`} />
                  <h3 className="font-semibold text-white text-sm">{b.label}</h3>
                </div>
                <span className="text-xs text-slate-400 tabular-nums">{b.items.length}</span>
              </div>
              <p className="text-[11px] text-slate-500 px-1 mb-3">{b.desc}</p>
              <div className="space-y-2">
                {b.items.length === 0 ? (
                  <div className="text-xs text-slate-600 italic text-center py-6">— None —</div>
                ) : (
                  b.items.slice(0, 8).map(s => (
                    <StockCard key={s.ticker} stock={s} onClick={() => onSelectStock?.(s.ticker)} />
                  ))
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
