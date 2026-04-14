import { useState, useMemo } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ScrollArea } from "@/components/ui/scroll-area";
import { formatPrice, formatPct, formatMarketCap } from "@/lib/format";
import { ChevronUp, ChevronDown, Plus } from "lucide-react";

const REGIME_CLASS = {
  SPRINTER: "regime-badge regime-sprinter",
  COMPOUNDER: "regime-badge regime-compounder",
  REVERSAL: "regime-badge regime-reversal",
  NEUTRAL: "regime-badge regime-neutral",
  AVOID: "regime-badge regime-avoid",
};

const GSQ_CLASS = {
  GAINER: "regime-badge gsq-gainer",
  STAYER: "regime-badge gsq-stayer",
  QUITTER: "regime-badge gsq-quitter",
};

export default function StockTable({
  stocks,
  onSelectStock,
  onAddToWatchlist,
  watchlistTickers,
}) {
  const [sortCol, setSortCol] = useState("quality_score");
  const [sortDir, setSortDir] = useState("desc");

  const sorted = useMemo(() => {
    if (!stocks?.length) return [];
    return [...stocks].sort((a, b) => {
      const aVal = a[sortCol] ?? 0;
      const bVal = b[sortCol] ?? 0;
      if (typeof aVal === "string") {
        return sortDir === "asc"
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal);
      }
      return sortDir === "asc" ? aVal - bVal : bVal - aVal;
    });
  }, [stocks, sortCol, sortDir]);

  const toggleSort = (col) => {
    if (sortCol === col) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortCol(col);
      setSortDir("desc");
    }
  };

  const SortIcon = ({ col }) => {
    if (sortCol !== col) return null;
    return sortDir === "asc" ? (
      <ChevronUp className="inline w-3 h-3" />
    ) : (
      <ChevronDown className="inline w-3 h-3" />
    );
  };

  if (!sorted.length) {
    return (
      <div className="py-16 text-center text-[#555] text-sm">
        No stocks to display. Start a scan to populate data.
      </div>
    );
  }

  return (
    <ScrollArea className="mt-4">
      <Table data-testid="stock-table">
        <TableHeader>
          <TableRow className="border-b border-[#1F1F1F] hover:bg-transparent">
            {[
              { key: "ticker", label: "TICKER", align: "left" },
              { key: "price", label: "PRICE", align: "right" },
              { key: "change_pct", label: "CHG%", align: "right" },
              { key: "regime", label: "REGIME", align: "center" },
              { key: "quality_score", label: "QUALITY", align: "right" },
              { key: "rsi", label: "RSI", align: "right" },
              { key: "vol_ratio", label: "VOL", align: "right" },
              { key: "trade_types", label: "TRADE", align: "center" },
              { key: "gsq_tag", label: "TAG", align: "center" },
              { key: "target_pct", label: "TARGET", align: "right" },
              { key: "_action", label: "", align: "center" },
            ].map((h) => (
              <TableHead
                key={h.key}
                className={`text-[10px] tracking-[0.1em] uppercase font-bold text-[#A1A1AA] cursor-pointer select-none whitespace-nowrap ${
                  h.align === "right"
                    ? "text-right"
                    : h.align === "center"
                    ? "text-center"
                    : "text-left"
                }`}
                onClick={() => h.key !== "_action" && toggleSort(h.key)}
              >
                {h.label} <SortIcon col={h.key} />
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {sorted.map((s) => {
            const inWatchlist = watchlistTickers?.has(s.ticker);
            return (
              <TableRow
                key={s.ticker}
                data-testid={`stock-row-${s.ticker}`}
                className="border-b border-[#1F1F1F] hover:bg-[#111111] cursor-pointer transition-colors"
                onClick={() => onSelectStock(s)}
              >
                <TableCell className="py-2.5">
                  <div>
                    <span className="text-xs text-white font-medium">
                      {s.ticker}
                    </span>
                    <p className="text-[10px] text-[#555] truncate max-w-[120px]">
                      {s.name}
                    </p>
                  </div>
                </TableCell>
                <TableCell className="text-right text-xs text-white">
                  {formatPrice(s.price)}
                </TableCell>
                <TableCell
                  className={`text-right text-xs font-medium ${
                    s.change_pct >= 0 ? "text-[#00E676]" : "text-[#FF3D00]"
                  }`}
                >
                  {formatPct(s.change_pct)}
                </TableCell>
                <TableCell className="text-center">
                  <span className={REGIME_CLASS[s.regime] || REGIME_CLASS.NEUTRAL}>
                    {s.regime}
                  </span>
                </TableCell>
                <TableCell className="text-right">
                  <span
                    className={`text-xs font-bold ${
                      s.quality_score >= 70
                        ? "text-[#00E676]"
                        : s.quality_score >= 50
                        ? "text-[#FFB300]"
                        : "text-[#FF3D00]"
                    }`}
                  >
                    {s.quality_score}
                  </span>
                </TableCell>
                <TableCell className="text-right text-xs text-[#A1A1AA]">
                  {s.rsi?.toFixed(1)}
                </TableCell>
                <TableCell className="text-right text-xs text-[#A1A1AA]">
                  {s.vol_ratio?.toFixed(2)}x
                </TableCell>
                <TableCell className="text-center">
                  <div className="flex gap-0.5 justify-center flex-wrap">
                    {(s.trade_types || []).map((t) => (
                      <span key={t} className={`regime-badge trade-${t.toLowerCase()}`}>{t}</span>
                    ))}
                  </div>
                </TableCell>
                <TableCell className="text-center">
                  <span className={GSQ_CLASS[s.gsq_tag] || GSQ_CLASS.STAYER}>
                    {s.gsq_tag}
                  </span>
                </TableCell>
                <TableCell className="text-right text-xs text-[#A1A1AA]">
                  {s.target_pct > 0 ? `${s.target_pct}%` : "-"}
                </TableCell>
                <TableCell className="text-center">
                  {!inWatchlist && (
                    <button
                      data-testid={`add-watchlist-${s.ticker}`}
                      onClick={(e) => {
                        e.stopPropagation();
                        onAddToWatchlist(s.ticker);
                      }}
                      className="p-1 hover:bg-[#1A1A1A] text-[#A1A1AA] hover:text-white transition-colors"
                      title="Add to Watchlist"
                    >
                      <Plus className="w-3.5 h-3.5" />
                    </button>
                  )}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </ScrollArea>
  );
}
