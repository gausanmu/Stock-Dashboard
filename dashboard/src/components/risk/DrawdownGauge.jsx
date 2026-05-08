import { formatCurrency, formatPct } from "@/lib/format";
import { cn } from "@/lib/utils";

export default function DrawdownGauge({ summary, risk }) {
  if (!summary || !risk) return <div className="bg-bg-card p-6 rounded-lg animate-pulse h-48"></div>;

  const maxDrawdownPct = risk.max_drawdown_limit * 100 || 15;
  const currentDrawdownPct = risk.current_drawdown * 100 || 0;
  const pctOfLimit = Math.min(100, (currentDrawdownPct / maxDrawdownPct) * 100);

  const getStatus = () => {
    if (risk.drawdown_exceeded) return { label: "HALTED", color: "bg-accent-red" };
    if (pctOfLimit > 80) return { label: "DANGER", color: "bg-accent-amber" };
    return { label: "SAFE", color: "bg-accent-green" };
  };
  const status = getStatus();

  return (
    <div className="bg-bg-card border border-border rounded-lg p-6 flex flex-col items-center justify-center text-center h-full">
      <h3 className="text-sm font-medium text-text-secondary w-full text-left mb-6">Portfolio Drawdown</h3>
      
      {/* Semi-circle Gauge */}
      <div className="relative w-48 h-24 overflow-hidden mb-2">
        <div className="absolute top-0 left-0 w-48 h-48 rounded-full border-[12px] border-bg-elevated box-border"></div>
        <div 
          className={cn("absolute top-0 left-0 w-48 h-48 rounded-full border-[12px] border-b-transparent border-r-transparent box-border transform rotate-45 transition-transform duration-1000", status.color.replace('bg-', 'border-'))}
          style={{ transform: `rotate(${45 + (pctOfLimit / 100) * 180}deg)` }}
        ></div>
        
        <div className="absolute bottom-0 left-0 w-full text-center pb-2">
          <span className="text-3xl font-bold mono-num">{currentDrawdownPct.toFixed(1)}%</span>
        </div>
      </div>
      
      <div className="flex items-center gap-2 mb-2 mt-2">
        <span className={cn("px-2 py-0.5 text-xs font-bold rounded text-bg-primary", status.color)}>
          {status.label}
        </span>
      </div>
      
      <p className="text-xs text-text-muted">Max Limit: {maxDrawdownPct.toFixed(1)}%</p>
    </div>
  );
}
