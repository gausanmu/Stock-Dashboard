import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import {
  Moon, Rocket, Flame, Eye, Play, RefreshCw, Target,
  ShieldAlert, TrendingUp, BarChart3, Zap, ArrowUpRight,
  ArrowDownRight, Clock, ChevronDown, ChevronUp, Activity
} from "lucide-react";

const TIER_CONFIG = {
  ROCKET: { icon: Rocket, label: "Rocket", color: "emerald", emoji: "🚀", desc: "3+ patterns aligned — highest conviction" },
  STRONG: { icon: Flame, label: "Strong", color: "amber", emoji: "💪", desc: "2 patterns firing — solid setup" },
  WATCH:  { icon: Eye,   label: "Watch",  color: "slate",  emoji: "👁️", desc: "1 strong pattern — monitor closely" },
};

const PATTERN_ICONS = {
  compression_breakout: "📊",
  volume_accumulation: "📈",
  seller_exhaustion: "🔄",
  breakout_retest: "🎯",
  ema_power: "⚡",
  sector_rotation: "🔀",
};

function PatternBar({ pattern }) {
  const pct = Math.round(pattern.score * 100);
  const colorClass = pct >= 60 ? "bg-emerald-500" : pct >= 30 ? "bg-amber-500" : "bg-slate-600";
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="w-5 text-center">{PATTERN_ICONS[pattern.id] || "•"}</span>
      <span className="w-36 truncate text-slate-300">{pattern.name}</span>
      <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${colorClass}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-8 text-right tabular-nums text-slate-400">{pct}%</span>
    </div>
  );
}

function StockCard({ stock, onSelect, isExpanded, onToggle }) {
  const tierCfg = TIER_CONFIG[stock.conviction_tier] || TIER_CONFIG.WATCH;
  const plan = stock.trade_plan || {};
  const sizing = stock.position_sizing || {};
  const rrColor = plan.risk_reward >= 3 ? "text-emerald-400" : plan.risk_reward >= 2 ? "text-amber-400" : "text-red-400";

  const tierBorder = {
    ROCKET: "border-emerald-500/30 bg-emerald-500/5",
    STRONG: "border-amber-500/30 bg-amber-500/5",
    WATCH:  "border-slate-500/20 bg-slate-500/5",
  }[stock.conviction_tier] || "border-slate-500/20";

  const tierGlow = {
    ROCKET: "shadow-emerald-500/10",
    STRONG: "shadow-amber-500/10",
    WATCH: "",
  }[stock.conviction_tier] || "";

  return (
    <div className={`rounded-xl border ${tierBorder} ${tierGlow} shadow-lg transition-all hover:scale-[1.01]`}>
      {/* Header */}
      <div className="p-4 cursor-pointer" onClick={onToggle}>
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-lg
              ${stock.conviction_tier === "ROCKET" ? "bg-emerald-500/20" :
                stock.conviction_tier === "STRONG" ? "bg-amber-500/20" : "bg-slate-700"}`}>
              {tierCfg.emoji}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-white text-sm">{stock.ticker}</span>
                <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-semibold uppercase tracking-wider
                  ${stock.conviction_tier === "ROCKET" ? "bg-emerald-500/20 text-emerald-400" :
                    stock.conviction_tier === "STRONG" ? "bg-amber-500/20 text-amber-400" :
                    "bg-slate-700 text-slate-400"}`}>
                  {stock.conviction_tier}
                </span>
              </div>
              <div className="text-xs text-slate-400 truncate max-w-[180px]">{stock.name}</div>
            </div>
          </div>
          <div className="text-right">
            <div className="text-white font-semibold text-sm">₹{stock.price?.toLocaleString()}</div>
            <div className={`text-xs flex items-center justify-end gap-0.5 ${stock.change_pct >= 0 ? "text-emerald-400" : "text-red-400"}`}>
              {stock.change_pct >= 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
              {stock.change_pct?.toFixed(1)}%
            </div>
          </div>
        </div>

        {/* Quick Stats Row */}
        <div className="grid grid-cols-4 gap-2 text-[11px]">
          <div className="bg-slate-800/50 rounded-lg px-2 py-1.5 text-center">
            <div className="text-slate-500">Conviction</div>
            <div className="font-bold text-white">{Math.round(stock.conviction_score * 100)}%</div>
          </div>
          <div className="bg-slate-800/50 rounded-lg px-2 py-1.5 text-center">
            <div className="text-slate-500">R:R</div>
            <div className={`font-bold ${rrColor}`}>{plan.risk_reward?.toFixed(1)}:1</div>
          </div>
          <div className="bg-slate-800/50 rounded-lg px-2 py-1.5 text-center">
            <div className="text-slate-500">Patterns</div>
            <div className="font-bold text-white">{stock.patterns_firing}/6</div>
          </div>
          <div className="bg-slate-800/50 rounded-lg px-2 py-1.5 text-center">
            <div className="text-slate-500">RSI</div>
            <div className={`font-bold ${stock.rsi > 70 ? "text-red-400" : stock.rsi < 35 ? "text-emerald-400" : "text-white"}`}>
              {stock.rsi?.toFixed(0)}
            </div>
          </div>
        </div>

        {/* Expand indicator */}
        <div className="flex justify-center mt-2">
          {isExpanded ? <ChevronUp className="w-4 h-4 text-slate-500" /> : <ChevronDown className="w-4 h-4 text-slate-500" />}
        </div>
      </div>

      {/* Expanded Detail */}
      {isExpanded && (
        <div className="border-t border-white/5 p-4 space-y-4">
          {/* Trade Plan */}
          <div>
            <div className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold mb-2">Trade Plan</div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="bg-slate-800/60 rounded-lg p-2.5">
                <div className="text-slate-500 mb-0.5">Entry</div>
                <div className="text-white font-semibold">₹{plan.entry?.toLocaleString()}</div>
              </div>
              <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-2.5">
                <div className="text-red-400 mb-0.5 flex items-center gap-1">
                  <ShieldAlert className="w-3 h-3" /> Stop Loss
                </div>
                <div className="text-white font-semibold">₹{plan.stop_loss?.toLocaleString()} ({plan.stop_loss_pct}%)</div>
              </div>
              <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-2.5">
                <div className="text-emerald-400 mb-0.5 flex items-center gap-1">
                  <Target className="w-3 h-3" /> Target 1
                </div>
                <div className="text-white font-semibold">₹{plan.target_1?.toLocaleString()} (+{plan.target_1_pct}%)</div>
              </div>
              <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-2.5">
                <div className="text-emerald-400 mb-0.5 flex items-center gap-1">
                  <Target className="w-3 h-3" /> Target 2
                </div>
                <div className="text-white font-semibold">₹{plan.target_2?.toLocaleString()} (+{plan.target_2_pct}%)</div>
              </div>
            </div>
          </div>

          {/* Position Sizing */}
          <div>
            <div className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold mb-2">Position Sizing (₹80K Account)</div>
            <div className="grid grid-cols-3 gap-2 text-xs">
              <div className="bg-slate-800/60 rounded-lg p-2.5 text-center">
                <div className="text-slate-500">Qty</div>
                <div className="text-white font-bold text-base">{sizing.quantity}</div>
              </div>
              <div className="bg-slate-800/60 rounded-lg p-2.5 text-center">
                <div className="text-slate-500">Capital</div>
                <div className="text-white font-semibold">₹{sizing.capital_required?.toLocaleString()}</div>
              </div>
              <div className="bg-slate-800/60 rounded-lg p-2.5 text-center">
                <div className="text-slate-500">Max Risk</div>
                <div className="text-red-400 font-semibold">₹{sizing.risk_amount?.toLocaleString()}</div>
              </div>
            </div>
          </div>

          {/* Pattern Breakdown */}
          <div>
            <div className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold mb-2">Pattern Analysis</div>
            <div className="space-y-2">
              {(stock.patterns || []).map(p => (
                <div key={p.id}>
                  <PatternBar pattern={p} />
                  {p.score > 0.1 && (
                    <div className="ml-7 text-[10px] text-slate-500 mt-0.5">{p.reason}</div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Extra Info */}
          <div className="flex items-center justify-between text-[10px] text-slate-500 pt-2 border-t border-white/5">
            <span>{stock.sector} · {stock.industry}</span>
            <span>{stock.pct_from_52w_high?.toFixed(1)}% from 52W high</span>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-2">
            <button
              onClick={() => onSelect(stock.ticker)}
              className="flex-1 py-2 px-3 rounded-lg bg-gradient-to-r from-emerald-600 to-teal-600 text-white text-xs font-semibold hover:from-emerald-500 hover:to-teal-500 transition-all flex items-center justify-center gap-1.5"
            >
              <Activity className="w-3.5 h-3.5" /> Deep Dive
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function EveningScannerView({ onSelectStock }) {
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
    } catch (e) {
      /* silent */
    } finally {
      setLoading(false);
    }
  }, [activeTier]);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await api.getEveningScanStatus();
      setScanStatus(res.data || {});
      setScanning(res.data?.running || false);
    } catch (e) { /* silent */ }
  }, []);

  useEffect(() => {
    fetchResults();
    fetchStatus();
    const t = setInterval(() => {
      fetchStatus();
      if (scanning) fetchResults();
    }, 3000);
    return () => clearInterval(t);
  }, [fetchResults, fetchStatus, scanning]);

  useEffect(() => { fetchResults(); }, [activeTier, fetchResults]);

  const handleTriggerScan = async () => {
    try {
      await api.triggerEveningScan();
      setScanning(true);
      toast.success("Evening scan started — scanning ~300 stocks for pre-rally patterns");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to start scan");
    }
  };

  const totalSignals = tiers.ROCKET + tiers.STRONG + tiers.WATCH;
  const scanTime = timestamp ? new Date(timestamp).toLocaleString("en-IN", { timeZone: "Asia/Kolkata" }) : null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-violet-500/20">
              <Moon className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">Evening Scanner</h1>
              <p className="text-xs text-slate-400">Pre-rally detection · Tomorrow's movers identified tonight</p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {scanTime && (
            <div className="flex items-center gap-1.5 text-xs text-slate-400">
              <Clock className="w-3.5 h-3.5" />
              <span>Last scan: {scanTime}</span>
            </div>
          )}
          <button
            onClick={handleTriggerScan}
            disabled={scanning}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all
              ${scanning
                ? "bg-violet-500/20 text-violet-300 cursor-not-allowed"
                : "bg-gradient-to-r from-violet-600 to-indigo-600 text-white hover:from-violet-500 hover:to-indigo-500 shadow-lg shadow-violet-500/20"
              }`}
          >
            {scanning ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            {scanning ? "Scanning..." : "Run Evening Scan"}
          </button>
        </div>
      </div>

      {/* Scan Progress */}
      {scanning && scanStatus.running && (
        <div className="bg-violet-500/10 border border-violet-500/20 rounded-xl px-4 py-3 flex items-center gap-3 text-sm">
          <span className="w-2 h-2 rounded-full bg-violet-400 animate-pulse" />
          <span className="text-violet-200">
            Scanning {scanStatus.current_ticker} · {scanStatus.progress}/{scanStatus.total}
          </span>
          <div className="flex-1 h-1.5 bg-violet-900/40 rounded-full overflow-hidden">
            <div
              className="h-full bg-violet-400 rounded-full transition-all"
              style={{ width: `${(scanStatus.progress / Math.max(scanStatus.total, 1)) * 100}%` }}
            />
          </div>
        </div>
      )}

      {/* Tier Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
        {/* All */}
        <button
          onClick={() => setActiveTier("ALL")}
          className={`rounded-xl p-4 border transition-all text-left
            ${activeTier === "ALL"
              ? "border-violet-500/40 bg-violet-500/10 shadow-lg shadow-violet-500/10"
              : "border-white/5 bg-slate-900/50 hover:bg-slate-800/50"}`}
        >
          <div className="text-2xl font-black text-white">{totalSignals}</div>
          <div className="text-xs text-slate-400 mt-1">All Signals</div>
        </button>
        {Object.entries(TIER_CONFIG).map(([tier, cfg]) => {
          const TierIcon = cfg.icon;
          const isActive = activeTier === tier;
          const count = tiers[tier] || 0;
          return (
            <button
              key={tier}
              onClick={() => setActiveTier(tier)}
              className={`rounded-xl p-4 border transition-all text-left
                ${isActive
                  ? `border-${cfg.color}-500/40 bg-${cfg.color}-500/10 shadow-lg`
                  : "border-white/5 bg-slate-900/50 hover:bg-slate-800/50"}`}
            >
              <div className="flex items-center justify-between">
                <div className="text-2xl font-black text-white">{count}</div>
                <TierIcon className={`w-5 h-5 ${isActive ? `text-${cfg.color}-400` : "text-slate-500"}`} />
              </div>
              <div className="text-xs text-slate-400 mt-1">{cfg.emoji} {cfg.label}</div>
              <div className="text-[10px] text-slate-500 mt-0.5">{cfg.desc}</div>
            </button>
          );
        })}
      </div>

      {/* Results Grid */}
      {loading ? (
        <div className="flex flex-col items-center justify-center py-20 text-slate-500">
          <RefreshCw className="w-8 h-8 animate-spin mb-3" />
          <span className="text-sm">Loading evening scan results...</span>
        </div>
      ) : results.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-slate-500">
          <Moon className="w-12 h-12 mb-4 opacity-30" />
          <h3 className="text-lg font-semibold text-slate-400 mb-2">No Evening Scan Results Yet</h3>
          <p className="text-sm text-center max-w-md">
            {scanStatus.status === "no_db"
              ? "MongoDB not connected. Evening scan results require a database."
              : 'Click "Run Evening Scan" to analyze ~300 stocks for pre-rally patterns. The scanner also runs automatically at 3:45 PM IST on trading days.'}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {results.map((stock) => (
            <StockCard
              key={stock.ticker}
              stock={stock}
              onSelect={(t) => onSelectStock?.(t)}
              isExpanded={expandedCard === stock.ticker}
              onToggle={() => setExpandedCard(expandedCard === stock.ticker ? null : stock.ticker)}
            />
          ))}
        </div>
      )}

      {/* Methodology Footer */}
      {results.length > 0 && (
        <div className="bg-slate-900/50 border border-white/5 rounded-xl p-4 text-xs text-slate-500">
          <div className="font-semibold text-slate-400 mb-1">How it works</div>
          <p>
            The Evening Scanner analyzes 6 statistically-proven pre-rally patterns: Compression Breakout,
            Volume Accumulation, Seller Exhaustion, Breakout Retest, EMA Power Alignment, and Sector Rotation.
            Each pattern is scored 0-100% and weighted to produce a conviction score. Only signals with R:R ≥ 2:1
            are shown. Position sizing uses Kelly Criterion capped at 2% account risk per trade.
          </p>
        </div>
      )}
    </div>
  );
}
