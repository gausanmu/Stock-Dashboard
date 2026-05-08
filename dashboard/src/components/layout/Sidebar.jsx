import { NavLink } from "react-router-dom";
import { 
  LayoutDashboard, 
  Briefcase, 
  Search, 
  Radio,
  Moon,
  ShieldAlert, 
  LineChart, 
  Settings 
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { path: "/overview", label: "Overview", icon: LayoutDashboard },
  { path: "/portfolio", label: "Portfolio", icon: Briefcase },
  { path: "/scanner", label: "Scanner", icon: Search },
  { path: "/live", label: "Live Intraday", icon: Radio },
  { path: "/evening", label: "Evening Scanner", icon: Moon },
  { path: "/risk", label: "Risk Dashboard", icon: ShieldAlert },
  { path: "/backtest", label: "Backtester", icon: LineChart },
  { path: "/settings", label: "Settings", icon: Settings },
];

export default function Sidebar() {
  return (
    <aside className="w-64 flex-shrink-0 bg-bg-secondary border-r border-border h-full flex flex-col">
      <div className="p-6">
        <h1 className="text-xl font-bold text-text-primary tracking-tight">
          NSE<span className="text-accent-blue">Quant</span>
        </h1>
        <p className="text-xs text-text-secondary mt-1">Algorithmic Engine v2</p>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors",
                isActive 
                  ? "bg-bg-elevated text-text-primary border-l-2 border-accent-blue" 
                  : "text-text-secondary hover:bg-bg-hover hover:text-text-primary border-l-2 border-transparent"
              )
            }
          >
            <item.icon className="w-4 h-4" />
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="p-4 border-t border-border">
        <div className="flex items-center gap-2 text-xs text-text-secondary">
          <div className="w-2 h-2 rounded-full bg-accent-green"></div>
          <span>System Online</span>
        </div>
      </div>
    </aside>
  );
}
