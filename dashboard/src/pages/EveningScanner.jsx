import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import {
  Moon, Rocket, Flame, Eye, Play, RefreshCw, Target,
  ShieldAlert, TrendingUp, BarChart3, Zap, ArrowUpRight,
  ArrowDownRight, Clock, ChevronDown, ChevronUp, Activity
} from "lucide-react";

const TIER_CONFIG = {
  ROCKET: { icon: Rocket, label: "Rocket", color: "accent-green", emoji: "🚀", desc: "3+ patterns aligned" },
  STRONG: { icon: Flame,  label: "Strong", color: "accent-amber", emoji: "💪", desc: "2 patterns firing" },
  WATCH:  { icon: Eye,    label: "Watch",  color: "text-secondary", emoji: "👁️", desc: "1 strong pattern" },
};

function PatternBar({ pattern }) {
  const pct = Math.round(pattern.score * 100);
  const barColor = pct >= 60 ? "bg-accent-green" : pct >= 30 ? "bg-accent-amber" : "bg-bg-hover";
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="w-5 text-center">{pattern.icon || "•"}</span>
      <span className="w-36 truncate text-text-secondary">{pattern.name}</span>
      <div className="flex-1 h-1.5 bg-bg-elevated rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-500 ${barColor}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-8 text-right mono-num text-text-muted">{pct}%</span>
    </div>
  );
}

function StockCard({ stock, isExpanded, onToggle }) {
  const plan = stock.trade_plan || {};
  const sizing = stock.position_sizing || {};
  const rrColor = plan.risk_reward >= 3 ? "text-accent-green" : plan.risk_reward >= 2 ? "text-accent-amber" : "text-accent-red";

  const borderMap = {
    ROCKET: "border-accent-green/30",
    STRONG: "border-accent-amber/30",
    WATCH:  "border-border",
  };
  const bgMap = {
    ROCKET: "bg-accent-green/5",
    STRONG: "bg-accent-amber/5",
    WATCH:  "bg-bg-card",
  };

  return (
    <div className={`rounded-xl border ${borderMap[stock.conviction_tier] || "border-border"} ${bgMap[stock.conviction_tier] || "bg-bg-card"} transition-all animate-fade-in`}>
      {/* Header */}
      <button className="w-full p-4 text-left" onClick={onToggle}>
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-lg ${
              stock.conviction_tier === "ROCKET" ? "bg-accent-green/20" :
              stock.conviction_tier === "STRONG" ? "bg-accent-amber/20" : "bg-bg-elevated"
            }`}>
              {TIER_CONFIG[stock.conviction_tier]?.emoji || "👁️"}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-text-primary text-sm">{stock.ticker}</span>
                <span className={`text-2xs px-1.5 py-0.5 rounded-full font-semibold uppercase tracking-wider ${
                  stock.conviction_tier === "ROCKET" ? "bg-accent-green/20 text-accent-green" :
                  stock.conviction_tier === "STRONG" ? "bg-accent-amber/20 text-accent-amber" :
                  "bg-bg-elevated text-text-secondary"
                }`}>
                  {stock.conviction_tier}
                </span>
              </div>
              <div className="text-xs text-text-muted truncate max-w-[180px]">{stock.name}</div>
            </div>
          </div>
          <div className="text-right">
            <div className="text-text-primary font-semibold text-sm mono-num">₹{stock.price?.toLocaleString()}</div>
            <div className={`text-xs flex items-center justify-end gap-0.5 ${stock.change_pct >= 0 ? "text-accent-green" : "text-accent-red"}`}>
              {stock.change_pct >= 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
              <span className="mono-num">{stock.change_pct?.toFixed(1)}%</span>
            </div>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-4 gap-2 text-2xs">
          <div className="bg-bg-elevated rounded-lg px-2 py-1.5 text-center">
            <div className="text-text-muted">Conviction</div>
            <div className="font-bold text-text-primary mono-num">{Math.round(stock.conviction_score * 100)}%</div>
          </div>
          <div className="bg-bg-elevated rounded-lg px-2 py-1.5 text-center">
            <div className="text-text-muted">R:R</div>
            <div className={`font-bold mono-num ${rrColor}`}>{plan.risk_reward?.toFixed(1)}:1</div>
          </div>
          <div className="bg-bg-elevated rounded-lg px-2 py-1.5 text-center">
            <div className="text-text-muted">Patterns</div>
            <div className="font-bold text-text-primary mono-num">{stock.patterns_firing}/6</div>
          </div>
          <div className="bg-bg-elevated rounded-lg px-2 py-1.5 text-center">
            <div className="text-text-muted">RSI</div>
            <div className={`font-bold mono-num ${stock.rsi > 70 ? "text-accent-red" : stock.rsi < 35 ? "text-accent-green" : "text-text-primary"}`}>
              {stock.rsi?.toFixed(0)}
            </div>
          </div>
        </div>

        <div className="flex justify-center mt-2">
          {isExpanded ? <ChevronUp className="w-4 h-4 text-text-muted" /> : <ChevronDown className="w-4 h-4 text-text-muted" />}
        </div>
      </button>

      {/* Expanded */}
      {isExpanded && (
        <div className="border-t border-border p-4 space-y-4 animate-slide-up">
          {/* Trade Plan */}
          <div>
            <div className="text-2xs text-text-muted uppercase tracking-wider font-semibold mb-2">Trade Plan</div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="bg-bg-elevated rounded-lg p-2.5">
                <div className="text-text-muted mb-0.5">Entry</div>
                <div className="text-text-primary font-semibold mono-num">₹{plan.entry?.toLocaleString()}</div>
              </div>
              <div className="bg-accent-red/10 border border-accent-red/20 rounded-lg p-2.5">
                <div className="text-accent-red mb-0.5 flex items-center gap-1">
                  <ShieldAlert className="w-3 h-3" /> Stop Loss
                </div>
                <div className="text-text-primary font-semibold mono-num">₹{plan.stop_loss?.toLocaleString()} <span className="text-accent-red text-2xs">({plan.stop_loss_pct}%)</span></div>
              </div>
              <div className="bg-accent-green/10 border border-accent-green/20 rounded-lg p-2.5">
                <div className="text-accent-green mb-0.5 flex items-center gap-1">
                  <Target className="w-3 h-3" /> Target 1
                </div>
                <div className="text-text-primary font-semibold mono-num">₹{plan.target_1?.toLocaleString()} <span className="text-accent-green text-2xs">(+{plan.target_1_pct}%)</span></div>
              </div>
              <div className="bg-accent-green/10 border border-accent-green/20 rounded-lg p-2.5">
                <div className="text-accent-green mb-0.5 flex items-center gap-1">
                  <Target className="w-3 h-3" /> Target 2
                </div>
                <div className="text-text-primary font-semibold mono-num">₹{plan.target_2?.toLocaleString()} <span className="text-accent-green text-2xs">(+{plan.target_2_pct}%)</span></div>
              </div>
            </div>
          </div>

          {/* Position Sizing */}
          <div>
            <div className="text-2xs text-text-muted uppercase tracking-wider font-semibold mb-2">Position Sizing (₹80K Account)</div>
            <div className="grid grid-cols-3 gap-2 text-xs">
              <div className="bg-bg-elevated rounded-lg p-2.5 text-center">
                <div className="text-text-muted">Qty</div>
                <div className="text-text-primary font-bold text-base mono-num">{sizing.quantity}</div>
              </div>
              <div className="bg-bg-elevated rounded-lg p-2.5 text-center">
                <div className="text-text-muted">Capital</div>
                <div className="text-text-primary font-semibold mono-num">₹{sizing.capital_required?.toLocaleString()}</div>
              </div>
              <div className="bg-bg-elevated rounded-lg p-2.5 text-center">
                <div className="text-text-muted">Max Risk</div>
                <div className="text-accent-red font-semibold mono-num">₹{sizing.risk_amount?.toLocaleString()}</div>
              </div>
            </div>
          </div>

          {/* Pattern Breakdown */}
          <div>
            <div className="text-2xs text-text-muted uppercase tracking-wider font-semibold mb-2">Pattern Analysis</div>
            <div className="space-y-2">
              {(stock.patterns || []).map(p => (
                <div key={p.id}>
                  <PatternBar pattern={p} />
                  {p.score > 0.1 && (
                    <div className="ml-7 text-2xs text-text-muted mt-0.5">{p.reason}</div>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="flex items-center justify-between text-2xs text-text-muted pt-2 border-t border-border">
            <span>{stock.sector}</span>
            <span className="mono-num">{stock.pct_from_52w_high?.toFixed(1)}% from 52W high</span>
          </div>
        </div>
      )}
    </div>
  );
}

export default function EveningScanner() {
  const [results, setResults] = useState([]);
  const [tiers, setTiers] = useState({ ROCKET: 0, STRONG: 0, WATCH: 0 });
  const [activeTier, setActiveTier] = useState("ALL");
  const [scanStatus, setScanStatus] = useState({});
  const [timestamp, setTimestamp] = useState(null);
  const [loading, setLoading] = useState(true);
  const [expandedCard, setExpandedCard] = useState(null);
  const [scanning, setScanning] = useState(false);

  const fetchResults = useCallback(async () => {
    try {
      const params = {};
      if (activeTier !== "ALL") params.tier = activeTier;
      const res = await api.getEveningResults(params);
      setResults(res.data?.results || []);
      setTiers(res.data?.tiers || { ROCKET: 0, STRONG: 0, WATCH: 0 });
      setTimestamp(res.data?.timestamp);
    } catch (e) { /* silent */ }
    finally { setLoading(false); }
  }, [activeTier]);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await api.getEveningScanStatus();
      setScanStatus(res.data || {});
      const wasScanning = scanning;
      const nowRunning = res.data?.running || false;
      setScanning(nowRunning);
      // Refresh results when scan completes
      if (wasScanning && !nowRunning) fetchResults();
    } catch (e) { /* silent */ }
  }, [scanning, fetchResults]);

  useEffect(() => {
    fetchResults();
    fetchStatus();
    const t = setInterval(fetchStatus, 3000);
    return () => clearInterval(t);
  }, []);  // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { fetchResults(); }, [activeTier]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleTriggerScan = async () => {
    try {
      await api.triggerEveningScan();
      setScanning(true);
    } catch (e) {
      alert(e?.response?.data?.detail || "Failed to start scan");
    }
  };

  const totalSignals = tiers.ROCKET + tiers.STRONG + tiers.WATCH;
  const scanTime = timestamp ? new Date(timestamp).toLocaleString("en-IN", { timeZone: "Asia/Kolkata" }) : null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center shadow-lg">
            <Moon className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-text-primary">Evening Scanner</h1>
            <p className="text-xs text-text-muted">Pre-rally detection · Tomorrow's movers identified tonight</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {scanTime && (
            <div className="flex items-center gap-1.5 text-xs text-text-muted">
              <Clock className="w-3.5 h-3.5" />
              <span>{scanTime}</span>
            </div>
          )}
          <button
            onClick={handleTriggerScan}
            disabled={scanning}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all ${
              scanning
                ? "bg-accent-purple/20 text-accent-purple cursor-not-allowed"
                : "bg-gradient-to-r from-purple-600 to-indigo-600 text-white hover:from-purple-500 hover:to-indigo-500 shadow-lg"
            }`}
          >
            {scanning ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            {scanning ? "Scanning..." : "Run Evening Scan"}
          </button>
        </div>
      </div>

      {/* Scan Progress */}
      {scanning && scanStatus.running && (
        <div className="bg-accent-purple/10 border border-accent-purple/20 rounded-xl px-4 py-3 flex items-center gap-3 text-sm animate-fade-in">
          <span className="w-2 h-2 rounded-full bg-accent-purple animate-pulse" />
          <span className="text-text-secondary">
            Scanning <span className="text-text-primary font-medium">{scanStatus.current_ticker}</span> · {scanStatus.progress}/{scanStatus.total}
          </span>
          <div className="flex-1 h-1.5 bg-bg-elevated rounded-full overflow-hidden">
            <div
              className="h-full bg-accent-purple rounded-full transition-all"
              style={{ width: `${(scanStatus.progress / Math.max(scanStatus.total, 1)) * 100}%` }}
            />
          </div>
        </div>
      )}

      {/* Tier Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <button
          onClick={() => setActiveTier("ALL")}
          className={`rounded-xl p-4 border transition-all text-left ${
            activeTier === "ALL"
              ? "border-accent-blue/40 bg-accent-blue/10"
              : "border-border bg-bg-card hover:bg-bg-elevated"
          }`}
        >
          <div className="text-2xl font-black text-text-primary mono-num">{totalSignals}</div>
          <div className="text-xs text-text-muted mt-1">All Signals</div>
        </button>
        {Object.entries(TIER_CONFIG).map(([tier, cfg]) => {
          const TierIcon = cfg.icon;
          const isActive = activeTier === tier;
          const count = tiers[tier] || 0;
          return (
            <button
              key={tier}
              onClick={() => setActiveTier(tier)}
              className={`rounded-xl p-4 border transition-all text-left ${
                isActive
                  ? `border-${cfg.color}/40 bg-${cfg.color}/10`
                  : "border-border bg-bg-card hover:bg-bg-elevated"
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="text-2xl font-black text-text-primary mono-num">{count}</div>
                <TierIcon className={`w-5 h-5 ${isActive ? `text-${cfg.color}` : "text-text-muted"}`} />
              </div>
              <div className="text-xs text-text-muted mt-1">{cfg.emoji} {cfg.label}</div>
            </button>
          );
        })}
      </div>

      {/* Results */}
      {loading ? (
        <div className="flex flex-col items-center justify-center py-20 text-text-muted">
          <RefreshCw className="w-8 h-8 animate-spin mb-3" />
          <span className="text-sm">Loading results...</span>
        </div>
      ) : results.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-text-muted">
          <Moon className="w-12 h-12 mb-4 opacity-30" />
          <h3 className="text-lg font-semibold text-text-secondary mb-2">No Evening Scan Results Yet</h3>
          <p className="text-sm text-center max-w-md">
            Click "Run Evening Scan" to analyze ~300 stocks for pre-rally patterns.
            The scanner also runs automatically at 3:45 PM IST on trading days.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {results.map((stock) => (
            <StockCard
              key={stock.ticker}
              stock={stock}
              isExpanded={expandedCard === stock.ticker}
              onToggle={() => setExpandedCard(expandedCard === stock.ticker ? null : stock.ticker)}
            />
          ))}
        </div>
      )}

      {/* Footer */}
      {results.length > 0 && (
        <div className="bg-bg-card border border-border rounded-xl p-4 text-xs text-text-muted">
          <div className="font-semibold text-text-secondary mb-1">How it works</div>
          <p>
            6 patterns analyzed: Compression Breakout, Volume Accumulation, Seller Exhaustion,
            Breakout Retest, EMA Power Alignment, Sector Rotation. Only signals with R:R ≥ 2:1 shown.
            Position sizing: Kelly Criterion capped at 2% account risk per trade.
          </p>
        </div>
      )}
    </div>
  );
}
