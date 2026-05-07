import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { TrendingUp, Activity, Zap, Briefcase, Eye, ArrowRight } from "lucide-react";

const TILES = [
  { id: "long_term",  label: "Long-Term",  icon: TrendingUp,  color: "from-emerald-500 to-teal-500", desc: "Build wealth · 6m–3y horizon" },
  { id: "swing",      label: "Swing",      icon: Activity,    color: "from-amber-500 to-orange-500", desc: "Catch 5–25 day moves" },
  { id: "short_term", label: "Short-Term", icon: Zap,         color: "from-fuchsia-500 to-pink-500", desc: "Intraday · 1–2 days" },
];

export default function OverviewView({ onNavigate }) {
  const [counts, setCounts] = useState({ LONG_TERM: 0, SWING: 0, SHORT_TERM: 0 });
  const [portfolio, setPortfolio] = useState({ items: [], summary: {} });
  const [confidence, setConfidence] = useState({ score: 50, status: "CAUTIOUS" });

  useEffect(() => {
    Promise.all([
      api.getStocks({ profile: "LONG_TERM" }).then(r => r.data?.length || 0).catch(() => 0),
      api.getStocks({ profile: "SWING" }).then(r => r.data?.length || 0).catch(() => 0),
      api.getStocks({ profile: "SHORT_TERM" }).then(r => r.data?.length || 0).catch(() => 0),
    ]).then(([lt, sw, st]) => setCounts({ LONG_TERM: lt, SWING: sw, SHORT_TERM: st }));

    api.getPortfolio().then(r => setPortfolio(r.data || {})).catch(() => {});
    api.getConfidence().then(r => setConfidence({ score: r.data?.score, status: r.data?.status })).catch(() => {});
  }, []);

  return (
    <div className="space-y-6">
      {/* Welcome header */}
      <div className="bg-gradient-to-br from-slate-900 via-slate-900 to-emerald-950/40 border border-white/10 rounded-2xl p-6 shadow-xl">
        <div className="text-[10px] uppercase tracking-widest text-emerald-400/80 font-bold mb-1">Welcome back</div>
        <h1 className="text-3xl md:text-4xl font-black text-white tracking-tight">NSE Quant Console</h1>
        <p className="text-sm text-slate-400 mt-2 max-w-2xl">
          One dashboard, three trading personas. Pick a mode below to scan Nifty 50 with strategy-specific logic, then build a portfolio that auto-suggests targets and holding windows.
        </p>
        <div className="flex flex-wrap items-center gap-3 mt-4">
          <Stat label="Market Confidence" value={`${confidence.score ?? "-"} · ${confidence.status}`} />
          <Stat label="Portfolio Value"   value={`₹${(portfolio.summary?.total_current ?? 0).toLocaleString("en-IN")}`} />
          <Stat label="Holdings"          value={portfolio.items?.length || 0} />
        </div>
      </div>

      {/* Mode tiles */}
      <div className="grid md:grid-cols-3 gap-4">
        {TILES.map(t => {
          const Icon = t.icon;
          const count = counts[t.id.toUpperCase()];
          return (
            <button
              key={t.id}
              onClick={() => onNavigate?.(t.id)}
              className="group text-left relative overflow-hidden rounded-2xl border border-white/10 hover:border-white/20 transition-all p-5 bg-slate-900/50"
            >
              <div className={`absolute inset-0 bg-gradient-to-br ${t.color} opacity-10 group-hover:opacity-20 transition-opacity`} />
              <div className="relative">
                <div className={`inline-flex items-center justify-center w-10 h-10 rounded-lg bg-gradient-to-br ${t.color} mb-3 shadow-lg`}>
                  <Icon className="w-5 h-5 text-white" />
                </div>
                <div className="text-white font-bold text-lg">{t.label}</div>
                <div className="text-sm text-slate-400 mb-3">{t.desc}</div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-500"><span className="text-slate-200 font-semibold">{count}</span> stocks scanned</span>
                  <span className="text-emerald-400 text-sm font-medium flex items-center gap-1 group-hover:gap-2 transition-all">
                    Open <ArrowRight className="w-3.5 h-3.5" />
                  </span>
                </div>
              </div>
            </button>
          );
        })}
      </div>

      {/* Quick links */}
      <div className="grid md:grid-cols-2 gap-4">
        <QuickLink icon={Briefcase} label="Portfolio" desc="Track holdings + auto target & holding-time" onClick={() => onNavigate?.("portfolio")} />
        <QuickLink icon={Eye}       label="Watchlist" desc="Monitor stocks you don't own (yet)"        onClick={() => onNavigate?.("watchlist")} />
      </div>
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div className="px-3 py-2 rounded-md bg-white/5 border border-white/10">
      <div className="text-[10px] uppercase tracking-widest text-slate-400">{label}</div>
      <div className="text-sm font-bold text-white">{value}</div>
    </div>
  );
}

function QuickLink({ icon: Icon, label, desc, onClick }) {
  return (
    <button onClick={onClick} className="group flex items-center gap-4 bg-white/[0.04] hover:bg-white/[0.07] border border-white/10 rounded-xl p-4 transition-colors text-left w-full">
      <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-slate-700 to-slate-800 flex items-center justify-center">
        <Icon className="w-5 h-5 text-white" />
      </div>
      <div className="flex-1">
        <div className="text-white font-semibold">{label}</div>
        <div className="text-xs text-slate-400">{desc}</div>
      </div>
      <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-emerald-400 transition-colors" />
    </button>
  );
}
