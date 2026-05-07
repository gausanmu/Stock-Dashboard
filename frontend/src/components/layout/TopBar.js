import { Search, RefreshCw, Zap } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import UniverseSelector from "@/components/UniverseSelector";

const PROFILE_BADGE = {
  LONG_TERM:  { label: "Long-Term",  color: "from-emerald-500 to-teal-500"   },
  SWING:      { label: "Swing",      color: "from-amber-500 to-orange-500"   },
  SHORT_TERM: { label: "Short-Term", color: "from-fuchsia-500 to-pink-500"   },
};

export default function TopBar({
  searchQuery, onSearchChange, onSearch,
  profile, scanStatus, onScan, macro, confidence,
  universe, onUniverseChange,
}) {
  const profMeta = PROFILE_BADGE[profile] || PROFILE_BADGE.LONG_TERM;

  return (
    <header className="sticky top-0 z-30 bg-slate-950/70 backdrop-blur-xl border-b border-white/5">
      <div className="flex items-center gap-3 px-6 py-3 flex-wrap">
        {/* Search */}
        <form onSubmit={(e) => { e.preventDefault(); onSearch?.(); }} className="flex-1 min-w-[240px] max-w-xl relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <Input
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search NSE ticker, company, or sector…"
            data-testid="search-input"
            className="pl-10 h-10 bg-white/5 border-white/10 text-white placeholder:text-slate-500 focus-visible:ring-emerald-500/50"
          />
        </form>

        {/* Macro / confidence chips */}
        <div className="hidden xl:flex items-center gap-2">
          {macro?.nifty && (
            <Chip label="NIFTY" value={macro.nifty.price} change={macro.nifty.change} />
          )}
          {macro?.bank && (
            <Chip label="BANKNIFTY" value={macro.bank.price} change={macro.bank.change} />
          )}
          {confidence && (
            <div className="px-3 py-1.5 rounded-md bg-white/5 border border-white/10 text-xs">
              <span className="text-slate-400">Confidence</span>
              <span className="ml-2 font-semibold text-white">{confidence.score ?? "-"}</span>
              <span className="ml-1 text-slate-500">/ {confidence.status}</span>
            </div>
          )}
        </div>

        {/* Universe selector */}
        {onUniverseChange && (
          <UniverseSelector value={universe} onChange={onUniverseChange} />
        )}

        {/* Active profile badge */}
        <div className={`hidden md:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-gradient-to-r ${profMeta.color} text-white text-xs font-semibold shadow-lg`}>
          <span className="w-1.5 h-1.5 rounded-full bg-white/80 animate-pulse" />
          {profMeta.label} Mode
        </div>

        {/* Scan button */}
        <Button
          onClick={onScan}
          disabled={scanStatus?.running}
          data-testid="run-scan-btn"
          className="h-10 bg-gradient-to-r from-emerald-500 to-cyan-500 hover:from-emerald-400 hover:to-cyan-400 text-slate-950 font-semibold border-0 shadow-lg shadow-emerald-500/20"
        >
          {scanStatus?.running ? (
            <>
              <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
              {scanStatus.progress}/{scanStatus.total}
            </>
          ) : (
            <>
              <Zap className="w-4 h-4 mr-2" />
              Run Scan
            </>
          )}
        </Button>
      </div>
    </header>
  );
}

function Chip({ label, value, change }) {
  const positive = (change ?? 0) >= 0;
  return (
    <div className="px-3 py-1.5 rounded-md bg-white/5 border border-white/10 text-xs flex items-center gap-2">
      <span className="text-slate-400">{label}</span>
      <span className="font-semibold text-white">{Number(value).toLocaleString("en-IN", { maximumFractionDigits: 2 })}</span>
      <span className={positive ? "text-emerald-400" : "text-rose-400"}>
        {positive ? "▲" : "▼"} {Math.abs(Number(change ?? 0)).toFixed(2)}%
      </span>
    </div>
  );
}
