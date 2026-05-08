import { useState, useMemo } from "react";
import { formatCurrency, formatPct, formatCompactNum } from "@/lib/format";
import { cn } from "@/lib/utils";
import { ArrowUpDown } from "lucide-react";

export default function ScannerResultsTable({ items }) {
  const [sortConfig, setSortConfig] = useState({ key: "master_score", direction: "desc" });

  const sortedItems = useMemo(() => {
    if (!items) return [];
    let sortableItems = [...items];
    sortableItems.sort((a, b) => {
      let aVal = a[sortConfig.key] || 0;
      let bVal = b[sortConfig.key] || 0;
      if (aVal < bVal) return sortConfig.direction === "asc" ? -1 : 1;
      if (aVal > bVal) return sortConfig.direction === "asc" ? 1 : -1;
      return 0;
    });
    return sortableItems;
  }, [items, sortConfig]);

  const requestSort = (key) => {
    let direction = "desc";
    if (sortConfig.key === key && sortConfig.direction === "desc") direction = "asc";
    setSortConfig({ key, direction });
  };

  const SortIcon = ({ columnKey }) => (
    <ArrowUpDown className={cn("inline ml-1 w-3 h-3 cursor-pointer", sortConfig.key === columnKey ? "text-accent-blue" : "text-text-muted hover:text-text-secondary")} onClick={() => requestSort(columnKey)} />
  );

  return (
    <div className="bg-bg-card border border-border rounded-lg overflow-hidden flex flex-col h-full">
      <div className="overflow-auto flex-1 relative">
        <table className="w-full text-sm text-left">
          <thead className="bg-bg-elevated border-b border-border text-text-secondary text-xs uppercase sticky top-0 z-10 shadow-sm">
            <tr>
              <th className="px-4 py-3 font-medium">Stock</th>
              <th className="px-4 py-3 font-medium text-right">LTP</th>
              <th className="px-4 py-3 font-medium text-right">Chg% <SortIcon columnKey="change_pct" /></th>
              <th className="px-4 py-3 font-medium text-right">Vol <SortIcon columnKey="volume" /></th>
              <th className="px-4 py-3 font-medium text-center">Regime</th>
              <th className="px-4 py-3 font-medium text-right">Score <SortIcon columnKey="master_score" /></th>
              <th className="px-4 py-3 font-medium text-right">Qual <SortIcon columnKey="quality_score" /></th>
              <th className="px-4 py-3 font-medium text-right">RSI <SortIcon columnKey="rsi" /></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {sortedItems.map((item) => {
              const regimeColor = 
                item.regime === "SPRINTER" || item.regime === "COMPOUNDER" || item.regime?.includes("LONG") ? "bg-accent-green/10 text-accent-green border border-accent-green/20" :
                item.regime === "AVOID" || item.regime?.includes("SHORT") ? "bg-accent-red/10 text-accent-red border border-accent-red/20" :
                "bg-bg-elevated text-text-secondary border border-border";

              return (
                <tr key={item.ticker} className="hover:bg-bg-hover transition-colors">
                  <td className="px-4 py-3 font-medium text-text-primary">
                    <div>{item.ticker}</div>
                    <div className="text-[10px] text-text-secondary font-normal truncate max-w-[120px]">{item.sector || 'General'}</div>
                  </td>
                  <td className="px-4 py-3 text-right mono-num">{formatCurrency(item.price)}</td>
                  <td className={cn("px-4 py-3 text-right mono-num font-medium", item.change_pct >= 0 ? "text-bullish" : "text-bearish")}>
                    {formatPct(item.change_pct)}
                  </td>
                  <td className="px-4 py-3 text-right mono-num text-text-secondary">
                    {formatCompactNum(item.volume)}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={cn("px-2 py-0.5 rounded text-[10px] font-bold uppercase", regimeColor)}>
                      {item.regime || "UNKNOWN"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right font-medium mono-num text-accent-blue">
                    {(item.master_score * 100).toFixed(0)}
                  </td>
                  <td className="px-4 py-3 text-right mono-num">
                    {item.quality_score}/100
                  </td>
                  <td className="px-4 py-3 text-right mono-num text-text-secondary">
                    {item.rsi?.toFixed(1)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {sortedItems.length === 0 && (
          <div className="text-center py-12 text-text-secondary">No stocks found for this profile.</div>
        )}
      </div>
    </div>
  );
}
