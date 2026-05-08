import { LayoutDashboard, TrendingUp, Activity, Zap, Briefcase, Eye, BarChart3, Bell, Newspaper, Settings, Moon } from "lucide-react";

const NAV_ITEMS = [
  { id: "overview",   label: "Overview",        icon: LayoutDashboard, group: "Dashboard" },
  { id: "long_term",  label: "Long-Term",       icon: TrendingUp,      group: "Trader Modes", color: "from-emerald-500 to-teal-500" },
  { id: "swing",      label: "Swing Trading",   icon: Activity,        group: "Trader Modes", color: "from-amber-500 to-orange-500" },
  { id: "short_term", label: "Short-Term",      icon: Zap,             group: "Trader Modes", color: "from-fuchsia-500 to-pink-500" },
  { id: "evening_scanner", label: "Evening Scanner", icon: Moon,        group: "Trader Modes", color: "from-violet-500 to-indigo-500" },
  { id: "news",       label: "News & Sentiment", icon: Newspaper,      group: "Markets" },
  { id: "sectors",    label: "Sectors",         icon: BarChart3,       group: "Markets" },
  { id: "alerts",     label: "Alerts",          icon: Bell,            group: "Markets" },
  { id: "portfolio",  label: "Portfolio",       icon: Briefcase,       group: "Personal" },
  { id: "watchlist",  label: "Watchlist",       icon: Eye,             group: "Personal" },
];

export default function Sidebar({ active, onChange }) {
  const groups = NAV_ITEMS.reduce((acc, item) => {
    (acc[item.group] = acc[item.group] || []).push(item);
    return acc;
  }, {});

  return (
    <aside className="w-full md:w-64 shrink-0 h-[200px] md:h-full bg-slate-950/80 backdrop-blur-xl border-b md:border-r border-white/5 flex flex-col z-50">
      {/* Logo */}
      <div className="px-6 py-5 border-b border-white/5">
        <div className="flex items-center gap-2.5">
          <div className="relative">
            <div className="absolute inset-0 bg-gradient-to-br from-emerald-400 to-cyan-400 blur-md opacity-60" />
            <div className="relative w-9 h-9 rounded-lg bg-gradient-to-br from-emerald-400 to-cyan-500 flex items-center justify-center text-slate-950 font-black text-sm">
              NQ
            </div>
          </div>
          <div>
            <div className="text-white font-bold tracking-tight">NSE Quant</div>
            <div className="text-[10px] text-slate-400 uppercase tracking-widest">Trader Console</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-6">
        {Object.entries(groups).map(([group, items]) => (
          <div key={group}>
            <div className="px-3 mb-2 text-[10px] font-semibold tracking-widest text-slate-500 uppercase">
              {group}
            </div>
            <div className="space-y-1">
              {items.map(item => {
                const Icon = item.icon;
                const isActive = active === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => onChange(item.id)}
                    data-testid={`sidebar-${item.id}`}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all
                      ${isActive
                        ? "bg-gradient-to-r from-white/10 to-white/5 text-white shadow-lg shadow-black/20 border border-white/10"
                        : "text-slate-400 hover:text-white hover:bg-white/5"
                      }`}
                  >
                    <Icon className={`w-4 h-4 ${isActive ? "text-white" : ""}`} />
                    <span className="flex-1 text-left">{item.label}</span>
                    {item.color && (
                      <span className={`w-1.5 h-1.5 rounded-full bg-gradient-to-r ${item.color}`} />
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-white/5">
        <button className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-slate-400 hover:text-white hover:bg-white/5 transition-colors">
          <Settings className="w-4 h-4" />
          <span>Settings</span>
        </button>
      </div>
    </aside>
  );
}
