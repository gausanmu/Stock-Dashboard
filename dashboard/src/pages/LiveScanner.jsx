import { useState, useEffect, useRef, useCallback } from "react";
import { api } from "@/lib/api";
import { formatCurrency, formatPct } from "@/lib/format";
import { cn } from "@/lib/utils";
import { Zap, Radio, TrendingUp, Volume2, Target, Clock, AlertTriangle, RefreshCw, ArrowUpDown, Shield, Crosshair } from "lucide-react";

const INDEX_OPTIONS = [
  { value: "ALL_NSE", label: "Entire Market (500+ stocks)" },
  { value: "NIFTY 50", label: "Nifty 50" },
  { value: "NIFTY NEXT 50", label: "Nifty Next 50" },
  { value: "NIFTY MIDCAP 50", label: "Nifty Midcap 50" },
  { value: "NIFTY SMLCAP 100", label: "Nifty Smallcap 100" },
  { value: "NIFTY BANK", label: "Bank Nifty" },
  { value: "NIFTY METAL", label: "Nifty Metal" },
  { value: "NIFTY PHARMA", label: "Nifty Pharma" },
  { value: "NIFTY AUTO", label: "Nifty Auto" },
  { value: "NIFTY ENERGY", label: "Nifty Energy" },
  { value: "NIFTY REALTY", label: "Nifty Realty" },
  { value: "SECURITIES IN F&O", label: "All F&O Stocks" },
];

const SORT_OPTIONS = [
  { value: "bull_score", label: "Bull Score" },
  { value: "change_pct", label: "% Change" },
  { value: "volume", label: "Volume" },
  { value: "risk_reward", label: "Risk:Reward" },
  { value: "ltp", label: "Price" },
];

const TAG_COLORS = {
  ROCKET: "bg-accent-red text-white",
  STRONG_BUY: "bg-accent-green text-bg-primary",
  BUILDING: "bg-accent-amber text-bg-primary",
};

const ACTION_COLORS = {
  ENTER: "text-accent-green",
  WATCH: "text-accent-blue",
  LATE_ENTRY: "text-accent-amber",
  RISKY: "text-accent-red",
};

function SignalBar({ signal }) {
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="w-28 text-text-secondary truncate">{signal.name}</span>
      <div className="flex-1 h-1.5 bg-bg-primary rounded-full overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all duration-500", signal.score >= 0.7 ? "bg-accent-green" : signal.score >= 0.4 ? "bg-accent-amber" : "bg-accent-red")}
          style={{ width: `${signal.score * 100}%` }}
        />
      </div>
      <span className="w-8 text-right mono-num font-medium">{(signal.score * 100).toFixed(0)}</span>
    </div>
  );
}

function ExitPanel({ exits }) {
  if (!exits) return null;
  return (
    <div className="mt-3 pt-3 border-t border-border">
      <div className="flex items-center gap-2 mb-3">
        <Crosshair className="w-3.5 h-3.5 text-accent-blue" />
        <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-wider">Exit Strategy</h4>
        <span className={cn("ml-auto text-xs font-bold", ACTION_COLORS[exits.action])}>
          {exits.action === "ENTER" && "✓ "}{exits.action}
        </span>
      </div>
      <p className="text-[10px] text-text-muted mb-3">{exits.action_reason}</p>

      <div className="grid grid-cols-3 gap-3 text-xs">
        <div className="bg-accent-red/10 border border-accent-red/20 rounded-md p-2">
          <div className="flex items-center gap-1 text-accent-red mb-1">
            <Shield className="w-3 h-3" />
            <span className="font-semibold">Stop Loss</span>
          </div>
          <p className="mono-num font-bold">{formatCurrency(exits.stop_loss)}</p>
          <p className="mono-num text-[10px] text-accent-red">-{exits.stop_loss_pct}%</p>
          {exits.trailing_active && <span className="text-[9px] text-accent-amber">⚡ trailing active</span>}
        </div>
        <div className="bg-accent-green/10 border border-accent-green/20 rounded-md p-2">
          <div className="flex items-center gap-1 text-accent-green mb-1">
            <Target className="w-3 h-3" />
            <span className="font-semibold">Target 1</span>
          </div>
          <p className="mono-num font-bold">{formatCurrency(exits.target_1)}</p>
          <p className="mono-num text-[10px] text-accent-green">+{exits.target_1_pct}%</p>
        </div>
        <div className="bg-accent-blue/10 border border-accent-blue/20 rounded-md p-2">
          <div className="flex items-center gap-1 text-accent-blue mb-1">
            <Target className="w-3 h-3" />
            <span className="font-semibold">Target 2</span>
          </div>
          <p className="mono-num font-bold">{formatCurrency(exits.target_2)}</p>
          <p className="mono-num text-[10px] text-accent-blue">+{exits.target_2_pct}%</p>
        </div>
      </div>

      <div className="mt-2 flex items-center gap-2 text-xs">
        <span className="text-text-secondary">R:R Ratio:</span>
        <span className={cn("font-bold mono-num", exits.risk_reward >= 2 ? "text-accent-green" : exits.risk_reward >= 1.5 ? "text-accent-amber" : "text-accent-red")}>
          {exits.risk_reward}:1
        </span>
      </div>
    </div>
  );
}

function BullCard({ bull, index }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className={cn("bg-bg-card border border-border rounded-lg overflow-hidden animate-slide-up transition-all", expanded && "ring-1 ring-accent-blue/30")}
      style={{ animationDelay: `${Math.min(index * 60, 600)}ms` }}
    >
      <div className="p-4 cursor-pointer" onClick={() => setExpanded(!expanded)}>
        <div className="flex justify-between items-start mb-2">
          <div className="flex items-center gap-3">
            <div className={cn("px-2 py-1 text-[10px] font-black rounded tracking-wider", TAG_COLORS[bull.bull_tag])}>
              {bull.bull_tag === "ROCKET" && <Zap className="inline w-3 h-3 mr-0.5 -mt-0.5" />}
              {bull.bull_tag}
            </div>
            <div>
              <h3 className="font-bold text-text-primary">{bull.symbol}</h3>
              <p className="text-[10px] text-text-secondary truncate max-w-[200px]">{bull.name}</p>
            </div>
          </div>
          <div className="text-right">
            <p className="font-bold mono-num text-lg">{formatCurrency(bull.ltp)}</p>
            <p className={cn("text-sm font-medium mono-num", bull.change_pct >= 0 ? "text-bullish" : "text-bearish")}>
              {formatPct(bull.change_pct)}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4 text-xs text-text-secondary flex-wrap">
          <span className="flex items-center gap-1">
            <Target className="w-3 h-3" />
            Score: <strong className="text-accent-blue mono-num">{(bull.bull_score * 100).toFixed(0)}</strong>
          </span>
          <span className="flex items-center gap-1">
            <Volume2 className="w-3 h-3" />
            {(bull.volume / 100000).toFixed(1)}L
          </span>
          {bull.exits && (
            <>
              <span className={cn("flex items-center gap-1 font-medium", ACTION_COLORS[bull.exits.action])}>
                {bull.exits.action}
              </span>
              <span className="flex items-center gap-1">
                R:R <strong className={cn("mono-num", bull.exits.risk_reward >= 2 ? "text-accent-green" : "text-accent-amber")}>{bull.exits.risk_reward}:1</strong>
              </span>
              <span className="flex items-center gap-1 text-accent-red">
                SL: <strong className="mono-num">{formatCurrency(bull.exits.stop_loss)}</strong>
              </span>
            </>
          )}
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {bull.detected_at}
          </span>
        </div>
      </div>

      {expanded && (
        <div className="px-4 pb-4 pt-2 border-t border-border space-y-2 bg-bg-primary/30">
          <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">Signal Breakdown</h4>
          {bull.signals.map((sig, i) => (
            <div key={i}>
              <SignalBar signal={sig} />
              <p className="text-[10px] text-text-muted ml-[7.5rem] mt-0.5">{sig.reason}</p>
            </div>
          ))}

          <ExitPanel exits={bull.exits} />

          <div className="grid grid-cols-4 gap-3 mt-3 pt-3 border-t border-border text-xs">
            <div>
              <span className="text-text-secondary block">Open</span>
              <span className="mono-num">{formatCurrency(bull.open)}</span>
            </div>
            <div>
              <span className="text-text-secondary block">High</span>
              <span className="mono-num text-bullish">{formatCurrency(bull.high)}</span>
            </div>
            <div>
              <span className="text-text-secondary block">Low</span>
              <span className="mono-num text-bearish">{formatCurrency(bull.low)}</span>
            </div>
            <div>
              <span className="text-text-secondary block">52W High</span>
              <span className="mono-num">{formatCurrency(bull.year_high)}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function LiveScanner() {
  const [bulls, setBulls] = useState([]);
  const [scanning, setScanning] = useState(false);
  const [index, setIndex] = useState("ALL_NSE");
  const [sortBy, setSortBy] = useState("bull_score");
  const [progress, setProgress] = useState({ current: 0, total: 0, found: 0 });
  const [marketStatus, setMarketStatus] = useState(null);
  const [lastScan, setLastScan] = useState(null);
  const [error, setError] = useState("");
  const eventSourceRef = useRef(null);

  // Check market status
  useEffect(() => {
    api.getLiveMarketStatus()
      .then(res => setMarketStatus(res.data))
      .catch(() => setMarketStatus({ is_open: false, status: "unknown" }));
  }, []);

  // Sort bulls whenever sortBy changes
  const sortedBulls = [...bulls].sort((a, b) => {
    switch (sortBy) {
      case "change_pct": return b.change_pct - a.change_pct;
      case "volume": return b.volume - a.volume;
      case "risk_reward": return (b.exits?.risk_reward || 0) - (a.exits?.risk_reward || 0);
      case "ltp": return b.ltp - a.ltp;
      case "bull_score":
      default: return b.bull_score - a.bull_score;
    }
  });

  const startStreamingScan = useCallback(() => {
    if (scanning) return;
    setScanning(true);
    setBulls([]);
    setProgress({ current: 0, total: 0, found: 0 });
    setError("");

    // Use deep-scan for entire market, regular scan for single index
    const isDeep = index === "ALL_NSE";
    const url = isDeep ? api.getLiveDeepScanURL() : api.getLiveScanURL(index);
    const es = new EventSource(url);
    eventSourceRef.current = es;

    es.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);

        if (msg.type === "scan_start") {
          setProgress(prev => ({ ...prev, total: msg.total }));
        } else if (msg.type === "bull_detected") {
          setBulls(prev => [...prev, msg.data]);
          setProgress(prev => ({ ...prev, current: msg.progress, found: prev.found + 1 }));
        } else if (msg.type === "progress") {
          setProgress(prev => ({ ...prev, current: msg.progress, found: msg.found }));
        } else if (msg.type === "scan_complete") {
          setLastScan(msg.timestamp);
          setScanning(false);
          es.close();
        } else if (msg.type === "error") {
          setError(msg.message);
          setScanning(false);
          es.close();
        }
      } catch (e) {
        console.error("SSE parse error:", e);
      }
    };

    es.onerror = () => {
      setScanning(false);
      es.close();
      // Fallback to snapshot API
      setError("SSE connection ended. Trying snapshot mode...");
      const fallback = isDeep ? api.getLiveDeepBulls() : api.getLiveBulls(index);
      fallback
        .then(res => {
          setBulls(res.data.bulls || []);
          setLastScan(new Date().toLocaleTimeString());
          setProgress(prev => ({ ...prev, total: res.data.total_scanned || 0, found: (res.data.bulls || []).length }));
          setError("");
        })
        .catch(() => setError("Could not fetch live data. Market may be closed."));
    };
  }, [scanning, index]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) eventSourceRef.current.close();
    };
  }, []);

  return (
    <div className="h-full flex flex-col space-y-6 overflow-y-auto pb-10">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-text-primary flex items-center gap-2">
            <Radio className={cn("w-6 h-6", scanning ? "text-accent-red animate-pulse" : "text-accent-blue")} />
            Live Intraday Scanner
          </h1>
          <p className="text-sm text-text-secondary mt-1">
            Detects bull runs in real-time from NSE live data. Results stream as they are found.
          </p>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          {marketStatus && (
            <div className={cn("flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border", marketStatus.is_open ? "border-accent-green/30 text-accent-green bg-accent-green/5" : "border-accent-amber/30 text-accent-amber bg-accent-amber/5")}>
              <div className={cn("w-2 h-2 rounded-full", marketStatus.is_open ? "bg-accent-green animate-pulse" : "bg-accent-amber")} />
              {marketStatus.is_open ? "Market Open" : "Market Closed"}
            </div>
          )}

          <select
            className="bg-bg-card border border-border text-sm rounded-md px-3 py-2 text-text-primary outline-none focus:border-accent-blue"
            value={index}
            onChange={(e) => setIndex(e.target.value)}
            disabled={scanning}
          >
            {INDEX_OPTIONS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>

          <button
            onClick={startStreamingScan}
            disabled={scanning}
            className="flex items-center gap-2 bg-accent-green hover:bg-accent-green/90 disabled:opacity-50 text-bg-primary px-5 py-2 rounded-md text-sm font-bold transition-colors"
          >
            {scanning ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
            {scanning ? "Scanning..." : "Scan Now"}
          </button>
        </div>
      </div>

      {/* Progress bar */}
      {scanning && (
        <div className="bg-bg-card border border-border rounded-lg p-4">
          <div className="flex justify-between text-xs text-text-secondary mb-2">
            <span className="flex items-center gap-1">
              <Radio className="w-3 h-3 text-accent-red animate-pulse" />
              Scanning {index === "ALL_NSE" ? "entire NSE market" : index} live...
            </span>
            <span>
              {progress.current}/{progress.total} checked | <strong className="text-accent-green">{progress.found} bulls found</strong>
            </span>
          </div>
          <div className="h-2 w-full bg-bg-elevated rounded-full overflow-hidden">
            <div
              className="h-full bg-accent-green transition-all duration-300"
              style={{ width: `${(progress.current / Math.max(progress.total, 1)) * 100}%` }}
            />
          </div>
        </div>
      )}

      {error && (
        <div className="bg-accent-amber/10 border border-accent-amber/20 text-accent-amber p-4 rounded-md flex items-center gap-2 text-sm">
          <AlertTriangle className="w-4 h-4" />
          {error}
        </div>
      )}

      {/* Results */}
      {sortedBulls.length > 0 ? (
        <div>
          <div className="flex justify-between items-center mb-4 flex-wrap gap-3">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-accent-green" />
              {sortedBulls.length} Bull{sortedBulls.length > 1 ? "s" : ""} Detected
              {lastScan && <span className="text-xs text-text-muted font-normal ml-2">at {lastScan}</span>}
            </h2>
            <div className="flex items-center gap-2">
              <ArrowUpDown className="w-4 h-4 text-text-secondary" />
              <span className="text-xs text-text-secondary">Sort:</span>
              {SORT_OPTIONS.map(opt => (
                <button
                  key={opt.value}
                  onClick={() => setSortBy(opt.value)}
                  className={cn("text-xs px-2.5 py-1 rounded-md border transition-colors", sortBy === opt.value ? "bg-accent-blue/20 border-accent-blue/40 text-accent-blue font-medium" : "border-border text-text-secondary hover:border-text-muted")}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {sortedBulls.map((bull, i) => (
              <BullCard key={bull.symbol} bull={bull} index={i} />
            ))}
          </div>
        </div>
      ) : !scanning && !error ? (
        <div className="flex-1 flex flex-col items-center justify-center text-center py-20">
          <Zap className="w-16 h-16 text-text-muted mb-4" />
          <h2 className="text-xl font-semibold text-text-secondary mb-2">No Scan Running</h2>
          <p className="text-sm text-text-muted max-w-md">
            Select "Entire Market" to scan 500+ NSE stocks, or pick a specific index.
            Click "Scan Now" — results appear live as each stock is analyzed.
          </p>
        </div>
      ) : null}
    </div>
  );
}
