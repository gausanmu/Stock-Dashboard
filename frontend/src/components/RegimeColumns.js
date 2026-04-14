import { ScrollArea } from "@/components/ui/scroll-area";
import { formatPct } from "@/lib/format";

const REGIMES = [
  { key: "SPRINTER", label: "SPRINTERS", color: "#00E676", desc: "Momentum Breakout" },
  { key: "COMPOUNDER", label: "COMPOUNDERS", color: "#2979FF", desc: "Structural Trend" },
  { key: "REVERSAL", label: "REVERSALS", color: "#FFB300", desc: "Mean Reversion" },
];

export default function RegimeColumns({ stocks, onSelectStock }) {
  const grouped = {};
  for (const r of REGIMES) {
    grouped[r.key] = (stocks || []).filter((s) => s.regime === r.key);
  }

  return (
    <div
      data-testid="regime-columns"
      className="col-span-12 md:col-span-8 grid grid-cols-1 md:grid-cols-3 gap-4"
    >
      {REGIMES.map((r) => (
        <div
          key={r.key}
          data-testid={`regime-col-${r.key.toLowerCase()}`}
          className="bg-[#0C0C0C] border border-[#1F1F1F] p-4"
        >
          <div className="flex items-center gap-2 mb-1">
            <span
              className="w-2 h-2"
              style={{ backgroundColor: r.color }}
            />
            <span
              className="text-[10px] tracking-[0.15em] uppercase font-bold"
              style={{ color: r.color }}
            >
              {r.label}
            </span>
            <span className="ml-auto text-[10px] text-[#A1A1AA]">
              {grouped[r.key].length}
            </span>
          </div>
          <p className="text-[10px] text-[#555] mb-3">{r.desc}</p>
          <ScrollArea className="h-[180px]">
            {grouped[r.key].length === 0 ? (
              <p className="text-[11px] text-[#555] text-center py-6">
                No stocks found
              </p>
            ) : (
              grouped[r.key].slice(0, 10).map((s, i) => (
                <button
                  key={s.ticker}
                  data-testid={`regime-stock-${s.ticker}`}
                  onClick={() => onSelectStock(s)}
                  className={`w-full flex items-center justify-between py-1.5 px-2 hover:bg-[#1A1A1A] transition-colors text-left animate-fade-in stagger-${Math.min(i + 1, 5)}`}
                >
                  <div>
                    <span className="text-xs text-white font-medium">
                      {s.ticker}
                    </span>
                    <span className="text-[10px] text-[#555] ml-2">
                      Q{s.quality_score}
                    </span>
                  </div>
                  <span
                    className={`text-xs font-medium ${
                      s.change_pct >= 0 ? "text-[#00E676]" : "text-[#FF3D00]"
                    }`}
                  >
                    {formatPct(s.change_pct)}
                  </span>
                </button>
              ))
            )}
          </ScrollArea>
        </div>
      ))}
    </div>
  );
}
