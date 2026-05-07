import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { Newspaper, Activity, RefreshCw, Loader2, ExternalLink, AlertTriangle, Info, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import SentimentBadge from "@/components/SentimentBadge";
import UniverseSelector from "@/components/UniverseSelector";

/**
 * News & Market Intelligence view
 *  - Two main toggles: Technical | Sentimental
 *  - Three asset class tabs: Stocks | F&O | Indices
 *  - Per-stock sentiment badges with explicit state handling (ok / unavailable / processing / stale)
 *  - F&O: shows futures-eligible underlyings + clear disclaimer about option chains
 */

const VIEW_MODES = [
  { id: "sentimental", label: "Sentimental", icon: Newspaper, desc: "News mood + LLM-classified headlines" },
  { id: "technical",   label: "Technical",   icon: Activity,  desc: "Regime, RSI, MACD, trend signals" },
];

const ASSET_TABS = [
  { id: "stocks",  label: "Stocks",   defaultUniverse: "nifty50" },
  { id: "fno",     label: "F&O",      defaultUniverse: "fno" },
  { id: "indices", label: "Indices",  defaultUniverse: null },
];

const REGIME_TONE = {
  WEALTH_BUILDER: "text-emerald-300 bg-emerald-500/10 border-emerald-500/30",
  COMPOUNDER: "text-emerald-300 bg-emerald-500/10 border-emerald-500/30",
  DIVIDEND_KING: "text-blue-300 bg-blue-500/10 border-blue-500/30",
  VALUE_PICK: "text-violet-300 bg-violet-500/10 border-violet-500/30",
  BREAKOUT_LONG: "text-amber-300 bg-amber-500/10 border-amber-500/30",
  EMA_TREND_LONG: "text-amber-300 bg-amber-500/10 border-amber-500/30",
  MEAN_REVERSION_LONG: "text-fuchsia-300 bg-fuchsia-500/10 border-fuchsia-500/30",
  AVOID: "text-rose-300 bg-rose-500/10 border-rose-500/30",
  RANGE_BOUND: "text-slate-400 bg-slate-700/30 border-slate-600/40",
  NO_TRADE: "text-slate-400 bg-slate-700/30 border-slate-600/40",
  FLAT: "text-slate-400 bg-slate-700/30 border-slate-600/40",
};

export default function NewsView({ onSelectStock }) {
  const [viewMode, setViewMode] = useState("sentimental");
  const [assetTab, setAssetTab] = useState("stocks");
  const [universe, setUniverse] = useState("nifty50");
  const [marketSentiment, setMarketSentiment] = useState(null);
  const [stocks, setStocks] = useState([]);
  const [sentiments, setSentiments] = useState({}); // ticker -> sentiment
  const [indices, setIndices] = useState([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  // Load stocks for the active universe (cached scan results)
  const loadStocks = useCallback(async (uni) => {
    setLoading(true);
    try {
      const res = await api.getScanResults(uni, { sort: "quality", limit: 30 });
      setStocks(res.data?.results || []);
    } catch (e) {
      setStocks([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadIndices = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.getFnoIndices();
      setIndices(res.data || []);
    } catch (e) {
      setIndices([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadMarketSentiment = useCallback(async (uni) => {
    try {
      const res = await api.getMarketSentiment(uni);
      setMarketSentiment(res.data);
    } catch (e) { /* silent */ }
  }, []);

  // Effect: load asset data when tab/universe changes
  useEffect(() => {
    if (assetTab === "indices") {
      loadIndices();
      setStocks([]);
      return;
    }
    const uni = assetTab === "fno" ? "fno" : universe;
    loadStocks(uni);
    loadMarketSentiment(uni);
  }, [assetTab, universe, loadStocks, loadIndices, loadMarketSentiment]);

  // Lazy-fetch sentiment per ticker as stocks load (only in sentimental mode)
  useEffect(() => {
    if (viewMode !== "sentimental" || stocks.length === 0) return;
    let cancelled = false;
    const tickers = stocks.slice(0, 12).map(s => s.ticker); // limit concurrent fetches
    (async () => {
      for (const t of tickers) {
        if (cancelled) return;
        if (sentiments[t]) continue;
        try {
          const res = await api.getTickerSentiment(t);
          if (!cancelled) setSentiments(prev => ({ ...prev, [t]: res.data }));
        } catch (e) { /* per-ticker silent */ }
      }
    })();
    return () => { cancelled = true; };
  }, [viewMode, stocks, sentiments]);

  const triggerSentimentRefresh = async () => {
    if (refreshing) return;
    setRefreshing(true);
    try {
      const uni = assetTab === "fno" ? "fno" : universe;
      await api.refreshMarketSentiment(uni, 20);
      toast.success(`Refreshing sentiment for top 20 ${uni} stocks…`);
      // Clear cached sentiments so we re-fetch
      setSentiments({});
      // Poll back in 8s
      setTimeout(() => {
        const tickers = stocks.slice(0, 12).map(s => s.ticker);
        Promise.all(tickers.map(t => api.getTickerSentiment(t).catch(() => null)))
          .then(rs => {
            const m = {};
            rs.forEach((r, i) => { if (r?.data) m[tickers[i]] = r.data; });
            setSentiments(m);
            loadMarketSentiment(uni);
          });
      }, 8000);
    } catch (e) {
      toast.error("Failed to refresh sentiment");
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <div className="space-y-6" data-testid="news-view">
      {/* Header */}
      <div className="bg-gradient-to-br from-slate-900 via-slate-900 to-blue-950/40 border border-white/10 rounded-2xl p-6 shadow-xl">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="text-[10px] uppercase tracking-widest text-blue-400/80 font-bold mb-1">News & Market Intelligence</div>
            <h1 className="text-2xl md:text-3xl font-black text-white tracking-tight">
              {viewMode === "sentimental" ? "Sentiment Window" : "Technical Window"}
            </h1>
            <p className="text-sm text-slate-400 mt-1.5 max-w-2xl">
              {viewMode === "sentimental"
                ? "Live news sentiment from Google News + Gemini 3 Flash classification. Scores update every hour during market hours."
                : "Technical regime + indicator snapshot from the latest cached scan."}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {assetTab !== "indices" && (
              <UniverseSelector value={universe} onChange={setUniverse} />
            )}
            {viewMode === "sentimental" && (
              <Button
                onClick={triggerSentimentRefresh}
                disabled={refreshing}
                data-testid="refresh-sentiment-btn"
                className="bg-blue-500 hover:bg-blue-400 text-white font-semibold"
              >
                {refreshing ? (
                  <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Refreshing</>
                ) : (
                  <><RefreshCw className="w-4 h-4 mr-2" />Refresh</>
                )}
              </Button>
            )}
          </div>
        </div>

        {/* Mode toggle */}
        <div className="mt-5 inline-flex items-center gap-1 p-1 rounded-lg bg-white/5 border border-white/10" data-testid="view-mode-toggle">
          {VIEW_MODES.map(m => {
            const Icon = m.icon;
            const active = viewMode === m.id;
            return (
              <button
                key={m.id}
                onClick={() => setViewMode(m.id)}
                data-testid={`view-mode-${m.id}`}
                className={`px-3.5 py-1.5 rounded-md text-sm font-medium transition-all flex items-center gap-1.5 ${
                  active
                    ? "bg-white text-slate-900 shadow-md"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                {m.label}
              </button>
            );
          })}
        </div>

        {/* Asset tabs */}
        <div className="mt-3 inline-flex items-center gap-1 p-1 rounded-lg bg-white/5 border border-white/10" data-testid="asset-tabs">
          {ASSET_TABS.map(t => (
            <button
              key={t.id}
              onClick={() => { setAssetTab(t.id); if (t.defaultUniverse) setUniverse(t.defaultUniverse); }}
              data-testid={`asset-tab-${t.id}`}
              className={`px-3 py-1 rounded-md text-xs font-semibold transition-all ${
                assetTab === t.id ? "bg-emerald-500 text-slate-900" : "text-slate-400 hover:text-white"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Market-wide sentiment summary (only sentimental + stocks/fno) */}
      {viewMode === "sentimental" && assetTab !== "indices" && marketSentiment && (
        <MarketSentimentBar data={marketSentiment} />
      )}

      {/* F&O disclaimer */}
      {assetTab === "fno" && (
        <div className="bg-amber-500/5 border border-amber-500/20 rounded-xl p-4 flex items-start gap-3" data-testid="fno-disclaimer">
          <Info className="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" />
          <div className="text-xs text-amber-100/80 leading-relaxed">
            <strong className="text-amber-200">F&O coverage note:</strong> Indian option chains require a paid broker API
            (Kite, Dhan, Upstox). This view shows sentiment & technicals for <strong>futures-eligible underlying stocks</strong>{" "}
            and major index proxies (NIFTY, BANKNIFTY, FINNIFTY) — sufficient for directional bias, not strike-by-strike OI analysis.
          </div>
        </div>
      )}

      {/* Asset list */}
      {assetTab === "indices" ? (
        <IndicesGrid indices={indices} loading={loading} />
      ) : loading && stocks.length === 0 ? (
        <div className="text-center py-20 text-slate-400">
          <Loader2 className="w-8 h-8 animate-spin mx-auto mb-3" />
          Loading…
        </div>
      ) : stocks.length === 0 ? (
        <EmptyState universe={universe} />
      ) : viewMode === "sentimental" ? (
        <SentimentalGrid stocks={stocks} sentiments={sentiments} onSelectStock={onSelectStock} />
      ) : (
        <TechnicalGrid stocks={stocks} onSelectStock={onSelectStock} />
      )}
    </div>
  );
}

// ── Market-wide sentiment bar ────────────────────────────────────
function MarketSentimentBar({ data }) {
  const { score = 0, label = "neutral", counts = {}, tickers_with_data = 0, tickers_total = 0 } = data || {};
  const total = (counts.bullish || 0) + (counts.neutral || 0) + (counts.bearish || 0);
  const pct = (n) => (total ? (n / total) * 100 : 0);

  const labelColor = label === "bullish" ? "text-emerald-300"
    : label === "bearish" ? "text-rose-300"
    : "text-slate-300";

  return (
    <div className="bg-white/[0.03] border border-white/10 rounded-2xl p-5" data-testid="market-sentiment-bar">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <div>
          <div className="text-[10px] uppercase tracking-widest text-slate-500 font-bold">Market-wide sentiment</div>
          <div className={`text-2xl font-black tracking-tight capitalize ${labelColor}`}>
            {label}
            <span className="text-sm font-normal text-slate-400 ml-2 tabular-nums">
              ({score > 0 ? "+" : ""}{score.toFixed(2)})
            </span>
          </div>
        </div>
        <div className="text-xs text-slate-400">
          {tickers_with_data} of {tickers_total} stocks analyzed
        </div>
      </div>
      <div className="flex h-2 rounded-full overflow-hidden bg-slate-800">
        <div className="bg-emerald-500 transition-all" style={{ width: `${pct(counts.bullish)}%` }} />
        <div className="bg-slate-600 transition-all" style={{ width: `${pct(counts.neutral)}%` }} />
        <div className="bg-rose-500 transition-all" style={{ width: `${pct(counts.bearish)}%` }} />
      </div>
      <div className="flex items-center justify-between mt-2 text-[11px] tabular-nums">
        <span className="text-emerald-400">▲ {counts.bullish || 0} bullish</span>
        <span className="text-slate-400">— {counts.neutral || 0} neutral</span>
        <span className="text-rose-400">▼ {counts.bearish || 0} bearish</span>
      </div>
    </div>
  );
}

// ── Sentimental grid ─────────────────────────────────────────────
function SentimentalGrid({ stocks, sentiments, onSelectStock }) {
  return (
    <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4" data-testid="sentimental-grid">
      {stocks.map(s => {
        const sent = sentiments[s.ticker];
        return (
          <button
            key={s.ticker}
            onClick={() => onSelectStock?.(s.ticker)}
            data-testid={`sentimental-card-${s.ticker}`}
            className="text-left bg-white/[0.03] hover:bg-white/[0.06] border border-white/10 hover:border-white/20 rounded-xl p-4 transition-all"
          >
            <div className="flex items-start justify-between gap-2 mb-2">
              <div>
                <div className="font-bold text-white text-sm">{s.ticker}</div>
                <div className="text-[11px] text-slate-500 line-clamp-1">{s.name}</div>
              </div>
              <SentimentBadge sentiment={sent} />
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-300 tabular-nums">₹{s.price?.toFixed?.(2) ?? "—"}</span>
              <span className={(s.change_pct ?? 0) >= 0 ? "text-emerald-400" : "text-rose-400"}>
                {(s.change_pct ?? 0) >= 0 ? "▲" : "▼"} {Math.abs(s.change_pct ?? 0).toFixed(2)}%
              </span>
            </div>
            {sent?.headline_count > 0 && (
              <div className="mt-2.5 pt-2.5 border-t border-white/5 text-[11px] text-slate-400 line-clamp-2">
                {sent.headlines?.[0]?.title || "Click to view headlines →"}
              </div>
            )}
          </button>
        );
      })}
    </div>
  );
}

// ── Technical grid ───────────────────────────────────────────────
function TechnicalGrid({ stocks, onSelectStock }) {
  return (
    <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4" data-testid="technical-grid">
      {stocks.map(s => {
        const regimeTone = REGIME_TONE[s.regime] || "text-slate-300 bg-slate-700/30 border-slate-600/40";
        return (
          <button
            key={s.ticker}
            onClick={() => onSelectStock?.(s.ticker)}
            data-testid={`technical-card-${s.ticker}`}
            className="text-left bg-white/[0.03] hover:bg-white/[0.06] border border-white/10 hover:border-white/20 rounded-xl p-4 transition-all"
          >
            <div className="flex items-start justify-between gap-2 mb-3">
              <div>
                <div className="font-bold text-white text-sm">{s.ticker}</div>
                <div className="text-[11px] text-slate-500 line-clamp-1">{s.name}</div>
              </div>
              <span className={`text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded border whitespace-nowrap ${regimeTone}`}>
                {s.regime?.replace(/_/g, " ")}
              </span>
            </div>
            <div className="grid grid-cols-3 gap-1.5 text-[11px]">
              <Metric label="₹" value={s.price?.toFixed?.(2)} />
              <Metric label="RSI" value={s.rsi?.toFixed?.(0)} highlight={s.rsi > 70 || s.rsi < 30} />
              <Metric label="MACD" value={(s.macd_hist ?? 0).toFixed(2)} positive={s.macd_hist > 0} />
              <Metric label="ADX" value={s.adx?.toFixed?.(0)} />
              <Metric label="ATR%" value={s.atr_pct?.toFixed?.(1)} />
              <Metric label="Q" value={s.quality_score} />
            </div>
          </button>
        );
      })}
    </div>
  );
}

function Metric({ label, value, highlight, positive }) {
  return (
    <div className="bg-white/5 rounded-md px-2 py-1.5">
      <div className="text-[9px] uppercase text-slate-500 tracking-wider">{label}</div>
      <div className={`tabular-nums font-medium ${
        highlight ? "text-amber-300" :
        positive === true ? "text-emerald-300" :
        positive === false ? "text-rose-300" :
        "text-white"
      }`}>{value ?? "—"}</div>
    </div>
  );
}

// ── Indices grid (F&O proxies) ───────────────────────────────────
function IndicesGrid({ indices, loading }) {
  if (loading) {
    return (
      <div className="text-center py-20 text-slate-400">
        <Loader2 className="w-8 h-8 animate-spin mx-auto mb-3" />
        Loading indices…
      </div>
    );
  }
  if (!indices || indices.length === 0) {
    return (
      <div className="text-center py-12 text-slate-400 bg-white/[0.03] border border-dashed border-white/10 rounded-2xl">
        <AlertTriangle className="w-6 h-6 mx-auto mb-2" />
        Index data temporarily unavailable
      </div>
    );
  }
  return (
    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="indices-grid">
      {indices.map(idx => (
        <div key={idx.symbol} className="bg-white/[0.03] border border-white/10 rounded-xl p-5" data-testid={`index-card-${idx.name}`}>
          <div className="text-[11px] uppercase tracking-widest text-slate-500 font-bold mb-1">{idx.symbol}</div>
          <div className="text-white text-xl font-black tracking-tight">{idx.name}</div>
          <div className="mt-3 flex items-baseline gap-3">
            <span className="text-2xl font-bold text-white tabular-nums">
              {idx.price?.toLocaleString?.("en-IN", { maximumFractionDigits: 2 }) || "—"}
            </span>
            <span className={`text-sm font-semibold ${idx.change_pct >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
              {idx.change_pct >= 0 ? "▲" : "▼"} {Math.abs(idx.change_pct).toFixed(2)}%
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Empty state ──────────────────────────────────────────────────
function EmptyState({ universe }) {
  return (
    <div className="text-center py-12 bg-white/[0.03] border border-dashed border-white/10 rounded-2xl">
      <AlertTriangle className="w-8 h-8 text-slate-500 mx-auto mb-3" />
      <div className="text-slate-300 font-medium">No cached data for {universe}</div>
      <div className="text-sm text-slate-500 mt-1">Run a scan from the top bar or wait for the next scheduled refresh.</div>
    </div>
  );
}
