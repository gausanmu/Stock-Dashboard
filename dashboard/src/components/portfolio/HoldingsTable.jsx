import React, { useState } from "react";
import { formatCurrency, formatPct } from "@/lib/format";
import { cn } from "@/lib/utils";
import { ChevronDown, ChevronRight, Trash2 } from "lucide-react";
import RecommendationCard from "./RecommendationCard";

export default function HoldingsTable({ items, onRemove }) {
  const [expanded, setExpanded] = useState({});

  const toggleRow = (ticker) => {
    setExpanded((prev) => ({ ...prev, [ticker]: !prev[ticker] }));
  };

  if (!items || items.length === 0) {
    return (
      <div className="text-center py-12 bg-bg-card border border-border rounded-lg text-text-secondary">
        No positions in your portfolio yet. Add one above.
      </div>
    );
  }

  return (
    <div className="bg-bg-card border border-border rounded-lg overflow-hidden">
      <table className="w-full text-sm text-left">
        <thead className="bg-bg-elevated border-b border-border text-text-secondary text-xs uppercase">
          <tr>
            <th className="px-4 py-3 font-medium w-10"></th>
            <th className="px-4 py-3 font-medium">Stock</th>
            <th className="px-4 py-3 font-medium text-right">Avg Price</th>
            <th className="px-4 py-3 font-medium text-right">LTP</th>
            <th className="px-4 py-3 font-medium text-right">Qty</th>
            <th className="px-4 py-3 font-medium text-right">P&L</th>
            <th className="px-4 py-3 font-medium text-center">Regime</th>
            <th className="px-4 py-3 font-medium text-center">Action</th>
            <th className="px-4 py-3 font-medium w-10"></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {items.map((item) => {
            const isExpanded = !!expanded[item.ticker];
            const isProfit = item.pnl >= 0;
            const regimeColor = 
              item.stock_data?.regime === "SPRINTER" || item.stock_data?.regime === "COMPOUNDER" ? "bg-accent-green/10 text-accent-green" :
              item.stock_data?.regime === "AVOID" ? "bg-accent-red/10 text-accent-red" :
              "bg-bg-elevated text-text-primary";

            return (
              <React.Fragment key={item.ticker}>
                <tr 
                  className={cn("hover:bg-bg-hover transition-colors cursor-pointer", isExpanded && "bg-bg-hover")}
                  onClick={() => toggleRow(item.ticker)}
                >
                  <td className="px-4 py-3 text-text-secondary">
                    {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                  </td>
                  <td className="px-4 py-3 font-medium text-text-primary">
                    <div>{item.ticker}</div>
                    <div className="text-xs text-text-secondary font-normal truncate max-w-[150px]">{item.name}</div>
                  </td>
                  <td className="px-4 py-3 text-right mono-num">{formatCurrency(item.buy_price)}</td>
                  <td className="px-4 py-3 text-right mono-num">{formatCurrency(item.current_price)}</td>
                  <td className="px-4 py-3 text-right mono-num">{item.quantity}</td>
                  <td className="px-4 py-3 text-right">
                    <div className={cn("mono-num font-medium", isProfit ? "text-bullish" : "text-bearish")}>
                      {formatCurrency(item.pnl)}
                    </div>
                    <div className={cn("mono-num text-xs", isProfit ? "text-bullish" : "text-bearish")}>
                      {formatPct(item.pnl_pct)}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={cn("px-2 py-1 rounded text-[10px] font-bold uppercase", regimeColor)}>
                      {item.stock_data?.regime || "UNKNOWN"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className="text-xs font-bold">{item.recommendation?.action || "-"}</span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button 
                      onClick={(e) => { e.stopPropagation(); onRemove(item.ticker); }}
                      className="p-1.5 text-text-muted hover:text-accent-red transition-colors rounded"
                      title="Remove from portfolio"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
                {isExpanded && (
                  <tr>
                    <td colSpan="9" className="p-0 border-b border-border bg-bg-primary/50">
                      <div className="p-4 grid grid-cols-1 lg:grid-cols-2 gap-4">
                        <RecommendationCard rec={{ ticker: item.ticker, stock: item.stock_data, holding: item, recommendation: item.recommendation }} />
                        <div className="bg-bg-elevated rounded-md border border-border p-4">
                          <h4 className="font-medium text-sm mb-3">Position Details</h4>
                          <div className="space-y-2 text-sm text-text-secondary">
                            <div className="flex justify-between"><span>Profile Strategy:</span> <span className="text-text-primary font-medium">{item.profile}</span></div>
                            <div className="flex justify-between"><span>Entry Date:</span> <span>{new Date(item.buy_date).toLocaleDateString()}</span></div>
                            <div className="flex justify-between"><span>Quality Score:</span> <span className="text-text-primary mono-num">{item.stock_data?.quality_score || '-'}/100</span></div>
                            <div className="flex justify-between"><span>Trend Score:</span> <span className="mono-num">{item.stock_data?.trend_score?.toFixed(2) || '-'}</span></div>
                          </div>
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
