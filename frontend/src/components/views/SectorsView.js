import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { BarChart3 } from "lucide-react";

export default function SectorsView() {
  const [sectors, setSectors] = useState([]);

  useEffect(() => {
    api.getSectorHeatmap().then(r => setSectors(r.data || [])).catch(() => {});
  }, []);

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-2">
        <BarChart3 className="w-5 h-5 text-violet-400" />
        <h1 className="text-2xl font-bold text-white">Sector Heatmap</h1>
      </div>

      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
        {sectors.length === 0 && (
          <div className="col-span-full bg-white/[0.03] border border-dashed border-white/10 rounded-xl py-10 text-center text-slate-400">
            Run a scan first to populate sectors.
          </div>
        )}
        {sectors.map(s => {
          const pos = (s.avg_change ?? 0) >= 0;
          return (
            <div key={s.sector} className={`rounded-xl p-4 border ${pos ? "bg-emerald-500/5 border-emerald-500/20" : "bg-rose-500/5 border-rose-500/20"}`}>
              <div className="flex items-start justify-between">
                <div>
                  <div className="text-white font-semibold">{s.sector}</div>
                  <div className="text-xs text-slate-400">{s.count} stocks · Avg Q={s.avg_quality}</div>
                </div>
                <div className={`text-lg font-bold tabular-nums ${pos ? "text-emerald-300" : "text-rose-300"}`}>
                  {pos ? "+" : ""}{s.avg_change}%
                </div>
              </div>
              <div className="flex gap-3 mt-3 text-xs">
                <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300">{s.compounders} compounders</span>
                <span className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-300">{s.sprinters} sprinters</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
