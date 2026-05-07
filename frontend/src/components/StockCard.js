import { TrendingUp, TrendingDown } from "lucide-react";
import { formatPrice, formatPct } from "@/lib/format";

const REGIME_STYLES = {
  WEALTH_BUILDER:      "from-emerald-500/20 to-teal-500/10 border-emerald-400/30 text-emerald-300",
  COMPOUNDER:          "from-emerald-500/20 to-teal-500/10 border-emerald-400/30 text-emerald-300",
  DIVIDEND_KING:       "from-blue-500/20 to-cyan-500/10 border-blue-400/30 text-blue-300",
  VALUE_PICK:          "from-violet-500/20 to-purple-500/10 border-violet-400/30 text-violet-300",
  SPRINTER:            "from-amber-500/20 to-orange-500/10 border-amber-400/30 text-amber-300",
  BREAKOUT_LONG:       "from-amber-500/20 to-orange-500/10 border-amber-400/30 text-amber-300",
  EMA_TREND_LONG:      "from-amber-500/20 to-orange-500/10 border-amber-400/30 text-amber-300",
  MEAN_REVERSION_LONG: "from-fuchsia-500/20 to-pink-500/10 border-fuchsia-400/30 text-fuchsia-300",
  REVERSAL:            "from-fuchsia-500/20 to-pink-500/10 border-fuchsia-400/30 text-fuchsia-300",
  INTRADAY_LONG:       "from-fuchsia-500/20 to-pink-500/10 border-fuchsia-400/30 text-fuchsia-300",
  INTRADAY_SHORT:      "from-rose-500/20 to-red-500/10 border-rose-400/30 text-rose-300",
  SWING_SHORT:         "from-rose-500/20 to-red-500/10 border-rose-400/30 text-rose-300",
  RANGE_BOUND:         "from-slate-500/20 to-slate-700/10 border-slate-400/30 text-slate-300",
  NO_TRADE:            "from-slate-500/20 to-slate-700/10 border-slate-400/30 text-slate-300",
  FLAT:                "from-slate-500/20 to-slate-700/10 border-slate-400/30 text-slate-300",
  NEUTRAL:             "from-slate-500/20 to-slate-700/10 border-slate-400/30 text-slate-300",
  AVOID:               "from-rose-500/20 to-red-500/10 border-rose-400/30 text-rose-300",
};

export default function StockCard({ stock, onClick, extraTags = [] }) {
  const positive = (stock.change_pct ?? 0) >= 0;
  const regimeClass = REGIME_STYLES[stock.regime] || REGIME_STYLES.NEUTRAL;

  return (
    <button
      onClick={onClick}
      className="group text-left w-full bg-gradient-to-br from-white/[0.04] to-white/[0.01] hover:from-white/[0.08] hover:to-white/[0.03] border border-white/5 hover:border-white/10 rounded-xl p-4 transition-all"
    >
      <div className="flex items-start justify-between mb-2">
        <div className="min-w-0 flex-1">
          <div className="text-white font-semibold tracking-tight truncate">{stock.ticker}</div>
          <div className="text-xs text-slate-400 truncate">{stock.name}</div>
        </div>
        <span className={`shrink-0 text-[10px] font-bold px-2 py-1 rounded border bg-gradient-to-br ${regimeClass} uppercase tracking-wider`}>
          {stock.regime}
        </span>
      </div>

      <div className="flex items-end justify-between mb-3">
        <div className="text-xl font-bold text-white tabular-nums">{formatPrice(stock.price)}</div>
        <div className={`flex items-center gap-1 text-sm font-semibold ${positive ? "text-emerald-400" : "text-rose-400"}`}>
          {positive ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
          {formatPct(stock.change_pct)}
        </div>
      </div>

      {/* Mini stats grid */}
      <div className="grid grid-cols-3 gap-2 text-[11px]">
        <Stat label="RSI"   value={stock.rsi?.toFixed(0)}   tone={stock.rsi > 70 ? "danger" : stock.rsi < 30 ? "warn" : "neutral"} />
        <Stat label="ADX"   value={stock.adx?.toFixed(0)}   tone={stock.adx > 25 ? "good" : "neutral"} />
        <Stat label="Q"     value={stock.quality_score}     tone={stock.quality_score >= 70 ? "good" : stock.quality_score >= 50 ? "neutral" : "warn"} />
      </div>

      {extraTags.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-3">
          {extraTags.map((t, i) => (
            <span key={i} className="text-[10px] px-2 py-0.5 rounded bg-white/5 text-slate-300 border border-white/5">
              {t}
            </span>
          ))}
        </div>
      )}

      {stock.setups?.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {stock.setups.slice(0, 3).map((s, i) => (
            <span key={i} className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">
              {s.replace(/_/g, " ")}
            </span>
          ))}
        </div>
      )}
    </button>
  );
}

function Stat({ label, value, tone }) {
  const toneClass = {
    good:    "text-emerald-300 bg-emerald-500/10",
    warn:    "text-amber-300  bg-amber-500/10",
    danger:  "text-rose-300   bg-rose-500/10",
    neutral: "text-slate-300  bg-white/5",
  }[tone || "neutral"];
  return (
    <div className={`rounded px-2 py-1 ${toneClass}`}>
      <div className="text-[9px] uppercase tracking-wider opacity-70">{label}</div>
      <div className="font-bold tabular-nums">{value ?? "-"}</div>
    </div>
  );
}
