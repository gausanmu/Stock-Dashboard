import { CheckCircle2, TrendingUp, AlertTriangle, ArrowRight, Activity } from "lucide-react";
import { formatCurrency, formatPct } from "@/lib/format";
import { cn } from "@/lib/utils";

export default function RecommendationCard({ rec, className }) {
  if (!rec || !rec.recommendation) return null;

  const { target_price, stop_price, risk_reward, action, rationale, target_gain_pct, downside_pct, hold_max, hold_unit } = rec.recommendation;
  const current_price = rec.stock?.price || rec.holding?.buy_price;
  
  const getActionColor = (act) => {
    switch (act) {
      case "ADD": return "text-accent-blue bg-accent-blue/10";
      case "BOOK_PROFIT": return "text-accent-green bg-accent-green/10";
      case "PARTIAL_BOOK": return "text-accent-amber bg-accent-amber/10";
      case "SELL":
      case "EXIT": return "text-accent-red bg-accent-red/10";
      default: return "text-text-primary bg-bg-elevated";
    }
  };

  // Progress calculation
  const totalRange = target_price - stop_price;
  const currentProgress = current_price - stop_price;
  const progressPct = totalRange > 0 ? Math.max(0, Math.min(100, (currentProgress / totalRange) * 100)) : 0;

  return (
    <div className={cn("bg-bg-elevated rounded-md border border-border overflow-hidden", className)}>
      <div className="p-4 border-b border-border flex justify-between items-center bg-bg-card">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-accent-blue" />
          <h4 className="font-medium text-sm">Engine Recommendation</h4>
        </div>
        <div className={cn("px-2.5 py-1 text-xs font-bold rounded-sm uppercase tracking-wider", getActionColor(action))}>
          {action}
        </div>
      </div>
      
      <div className="p-4 space-y-4">
        {/* Price Targets */}
        <div className="grid grid-cols-3 gap-4">
          <div>
            <p className="text-xs text-text-secondary mb-1">Stop Loss</p>
            <p className="font-medium text-accent-red mono-num">{formatCurrency(stop_price)}</p>
            <p className="text-xs text-accent-red/80 mono-num mt-0.5">{downside_pct}%</p>
          </div>
          <div>
            <p className="text-xs text-text-secondary mb-1">Current</p>
            <p className="font-medium mono-num">{formatCurrency(current_price)}</p>
          </div>
          <div className="text-right">
            <p className="text-xs text-text-secondary mb-1">Target</p>
            <p className="font-medium text-accent-green mono-num">{formatCurrency(target_price)}</p>
            <p className="text-xs text-accent-green/80 mono-num mt-0.5">+{target_gain_pct}%</p>
          </div>
        </div>

        {/* Visual Progress Bar */}
        <div className="relative h-1.5 w-full bg-accent-red/20 rounded-full overflow-hidden">
          <div className="absolute top-0 left-0 h-full bg-accent-green/20 w-full" style={{ left: `${100 - (target_gain_pct / (target_gain_pct + Math.abs(downside_pct))) * 100}%` }}></div>
          <div 
            className="absolute top-0 left-0 h-full bg-accent-blue transition-all duration-500 rounded-full"
            style={{ width: `${progressPct}%` }}
          />
        </div>

        {/* Meta Stats */}
        <div className="flex justify-between items-center text-xs pt-2">
          <div className="flex items-center gap-1.5 text-text-secondary">
            <TrendingUp className="w-3.5 h-3.5" />
            <span>R:R <strong className="text-text-primary mono-num">{risk_reward}</strong></span>
          </div>
          <div className="text-text-secondary">
            Est. Hold: <strong className="text-text-primary">{hold_max} {hold_unit}</strong>
          </div>
        </div>

        {/* Rationale */}
        <div className="bg-bg-primary p-3 rounded text-sm text-text-secondary border border-border">
          {rationale}
        </div>
      </div>
    </div>
  );
}
