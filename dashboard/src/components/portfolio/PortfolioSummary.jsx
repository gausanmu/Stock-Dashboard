import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { formatCurrency, formatPct } from "@/lib/format";
import { cn } from "@/lib/utils";

export default function PortfolioSummary({ summary, risk }) {
  if (!summary) return null;

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
      <div className="bg-bg-card border border-border p-4 rounded-lg">
        <h3 className="text-text-secondary text-sm font-medium mb-1">Total Invested</h3>
        <p className="text-2xl font-bold mono-num">{formatCurrency(summary.total_invested)}</p>
      </div>
      
      <div className="bg-bg-card border border-border p-4 rounded-lg">
        <h3 className="text-text-secondary text-sm font-medium mb-1">Current Value</h3>
        <p className="text-2xl font-bold mono-num">{formatCurrency(summary.total_current)}</p>
      </div>

      <div className="bg-bg-card border border-border p-4 rounded-lg">
        <h3 className="text-text-secondary text-sm font-medium mb-1">Total P&L</h3>
        <div className="flex items-baseline gap-2">
          <p className={cn("text-2xl font-bold mono-num", summary.total_pnl >= 0 ? "text-bullish" : "text-bearish")}>
            {formatCurrency(summary.total_pnl)}
          </p>
          <span className={cn("text-sm font-medium", summary.total_pnl >= 0 ? "text-bullish" : "text-bearish")}>
            ({formatPct(summary.total_pnl_pct)})
          </span>
        </div>
      </div>

      <div className="bg-bg-card border border-border p-4 rounded-lg">
        <h3 className="text-text-secondary text-sm font-medium mb-1">Risk Status</h3>
        <div className="flex items-center gap-2">
          {risk?.drawdown_exceeded ? (
            <div className="px-2 py-1 bg-bearish text-xs font-bold rounded">HALT TRADING</div>
          ) : (
            <div className="px-2 py-1 bg-bullish text-xs font-bold rounded">SYSTEM OK</div>
          )}
          {risk?.concentration_warnings?.length > 0 && (
            <div className="px-2 py-1 bg-accent-amber/10 text-accent-amber text-xs font-bold rounded">
              SECTOR WARNING
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
