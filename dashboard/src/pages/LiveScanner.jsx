import { useState, useEffect, useRef, useCallback } from "react";
import { api } from "@/lib/api";
import { formatCurrency, formatPct } from "@/lib/format";
import { cn } from "@/lib/utils";
import { Zap, Radio, TrendingUp, Volume2, Target, Clock, AlertTriangle, RefreshCw } from "lucide-react";

const INDEX_OPTIONS = [
  { value: "NIFTY 50", label: "Nifty 50" },
  { value: "NIFTY NEXT 50", label: "Nifty Next 50" },
  { value: "NIFTY MIDCAP 50", label: "Nifty Midcap 50" },
  { value: "NIFTY BANK", label: "Bank Nifty" },
];

const TAG_COLORS = {
  ROCKET: "bg-accent-red text-white",
  STRONG_BUY: "bg-accent-green text-bg-primary",
  BUILDING: "bg-accent-amber text-bg-primary",
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

function BullCard({ bull, index }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className={cn("bg-bg-card border border-border rounded-lg overflow-hidden animate-slide-up transition-all", expanded && "ring-1 ring-accent-blue/30")}
      style={{ animationDelay: `${index * 80}ms` }}
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

        <div className="flex items-center gap-4 text-xs text-text-secondary">
          <span className="flex items-center gap-1">
            <Target className="w-3 h-3" />
            Bull Score: <strong className="text-accent-blue mono-num">{(bull.bull_score * 100).toFixed(0)}/100</strong>
          </span>
          <span className="flex items-center gap-1">
            <Volume2 className="w-3 h-3" />
            Vol: <strong className="mono-num">{(bull.volume / 100000).toFixed(1)}L</strong>
          </span>
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
  const [index, setIndex] = useState("NIFTY 50");
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

  const startStreamingScan = useCallback(() => {
    if (scanning) return;
    setScanning(true);
    setBulls([]);
    setProgress({ current: 0, total: 0, found: 0 });
    setError("");

    const url = api.getLiveScanURL(index);
    const es = new EventSource(url);
    eventSourceRef.current = es;

    es.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);

        if (msg.type === "scan_start") {
          setProgress(prev => ({ ...prev, total: msg.total }));
        } else if (msg.type === "bull_detected") {
          setBulls(prev => {
            const updated = [...prev, msg.data];
            updated.sort((a, b) => b.bull_score - a.bull_score);
            return updated;
          });
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
      // If no bulls found and no error, try the snapshot API as fallback
      if (bulls.length === 0) {
        setError("SSE connection failed. Trying snapshot mode...");
        api.getLiveBulls(index)
          .then(res => {
            setBulls(res.data.bulls || []);
            setLastScan(new Date().toLocaleTimeString());
            setError("");
          })
          .catch(err => setError("Could not fetch live data. Market may be closed."));
      }
    };
  }, [scanning, index, bulls.length]);

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

        <div className="flex items-center gap-3">
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
              Scanning {index} live...
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
      {bulls.length > 0 ? (
        <div>
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-accent-green" />
              {bulls.length} Bull{bulls.length > 1 ? "s" : ""} Detected
            </h2>
            {lastScan && <span className="text-xs text-text-muted">Last scan: {lastScan}</span>}
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {bulls.map((bull, i) => (
              <BullCard key={bull.symbol} bull={bull} index={i} />
            ))}
          </div>
        </div>
      ) : !scanning && !error ? (
        <div className="flex-1 flex flex-col items-center justify-center text-center py-20">
          <Zap className="w-16 h-16 text-text-muted mb-4" />
          <h2 className="text-xl font-semibold text-text-secondary mb-2">No Scan Running</h2>
          <p className="text-sm text-text-muted max-w-md">
            Click "Scan Now" to fetch live data from NSE and detect intraday bull runs.
            Results appear instantly as each stock is analyzed.
          </p>
        </div>
      ) : null}
    </div>
  );
}
