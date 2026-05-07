import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Globe, ChevronDown } from "lucide-react";

/**
 * Universe selector dropdown. Renders all available scan universes from /api/scan/levels.
 * Tier badge: fast | medium | deep — sets user expectation on how long a scan takes.
 */
const TIER_COLOR = {
  fast: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  medium: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  deep: "bg-fuchsia-500/15 text-fuchsia-300 border-fuchsia-500/30",
};

export default function UniverseSelector({ value, onChange, className = "" }) {
  const [levels, setLevels] = useState({});
  const [open, setOpen] = useState(false);

  useEffect(() => {
    api.getScanLevels().then(r => setLevels(r.data || {})).catch(() => {});
  }, []);

  const current = levels[value] || { label: "Nifty 50", count: 50, tier: "fast" };

  return (
    <div className={`relative ${className}`} data-testid="universe-selector">
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        className="h-10 px-3 inline-flex items-center gap-2 rounded-md bg-white/5 border border-white/10 hover:border-white/20 text-white text-sm transition-colors"
        data-testid="universe-selector-trigger"
      >
        <Globe className="w-4 h-4 text-slate-400" />
        <span className="font-medium">{current.label}</span>
        <span className="text-xs text-slate-500 tabular-nums">· {current.count}</span>
        <span className={`text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded border ${TIER_COLOR[current.tier] || TIER_COLOR.fast}`}>
          {current.tier}
        </span>
        <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-30" onClick={() => setOpen(false)} />
          <div className="absolute z-40 right-0 mt-1 w-72 max-h-96 overflow-y-auto rounded-lg bg-slate-900 border border-white/10 shadow-2xl shadow-black/50 p-1.5">
            {Object.entries(levels).map(([key, info]) => (
              <button
                key={key}
                onClick={() => { onChange?.(key); setOpen(false); }}
                data-testid={`universe-option-${key}`}
                className={`w-full flex items-center justify-between px-2.5 py-2 rounded-md text-sm transition-colors text-left ${
                  value === key ? "bg-emerald-500/10 text-emerald-200 border border-emerald-500/30" : "hover:bg-white/5 text-slate-300 border border-transparent"
                }`}
              >
                <div>
                  <div className="font-medium">{info.label}</div>
                  <div className="text-[11px] text-slate-500">{info.count} stocks · ~{info.est_minutes} min</div>
                </div>
                <span className={`text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded border ${TIER_COLOR[info.tier] || TIER_COLOR.fast}`}>
                  {info.tier}
                </span>
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
