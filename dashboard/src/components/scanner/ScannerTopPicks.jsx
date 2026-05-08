import { TrendingUp, AlertTriangle } from "lucide-react";
import { formatCurrency, formatPct } from "@/lib/format";
import { cn } from "@/lib/utils";

export default function ScannerTopPicks({ items }) {
  if (!items || items.length === 0) return null;

  // Take top 3
  const topPicks = items.slice(0, 3);

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
      {topPicks.map((stock, i) => (
        <div key={stock.ticker} className="bg-bg-card border border-border rounded-lg p-4 flex flex-col relative overflow-hidden">
          <div className="absolute top-0 right-0 w-16 h-16 bg-accent-blue/10 rounded-bl-full -z-10"></div>
          
          <div className="flex justify-between items-start mb-3">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-accent-blue/80">#{i + 1} PICK</span>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-accent-green/10 text-accent-green uppercase">
                  {stock.regime}
                </span>
              </div>
              <h3 className="text-xl font-bold mt-1 text-text-primary">{stock.ticker}</h3>
              <p className="text-xs text-text-secondary truncate max-w-[150px]">{stock.name}</p>
            </div>
            <div className="text-right">
              <p className="font-medium mono-num">{formatCurrency(stock.price)}</p>
              <p className={cn("text-xs font-medium mono-num", stock.change_pct >= 0 ? "text-bullish" : "text-bearish")}>
                {formatPct(stock.change_pct)}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2 mt-auto pt-4 border-t border-border/50 text-xs">
            <div>
              <span className="text-text-secondary block mb-0.5">Quality</span>
              <span className="font-medium">{stock.quality_score}/100</span>
            </div>
            <div>
              <span className="text-text-secondary block mb-0.5">Trend</span>
              <span className="font-medium mono-num">{(stock.trend_score * 100).toFixed(0)}%</span>
            </div>
            <div>
              <span className="text-text-secondary block mb-0.5">RSI</span>
              <span className="font-medium mono-num">{stock.rsi?.toFixed(1)}</span>
            </div>
            <div>
              <span className="text-text-secondary block mb-0.5">Momentum</span>
              <span className="font-medium mono-num">{(stock.momentum_score * 100).toFixed(0)}%</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
