import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { Eye, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { formatPrice, formatPct } from "@/lib/format";

export default function WatchlistView({ onSelectStock }) {
  const [items, setItems] = useState([]);
  const [t, setT] = useState("");

  const fetchData = useCallback(async () => {
    try {
      const res = await api.getWatchlist();
      setItems(res.data || []);
    } catch (e) { /* silent */ }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const add = async () => {
    if (!t) return;
    try {
      await api.addToWatchlist({ ticker: t.toUpperCase().replace(".NS", ""), tag: "STAYER" });
      setT("");
      toast.success("Added to watchlist");
      fetchData();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to add");
    }
  };

  const remove = async (ticker) => {
    try {
      await api.removeFromWatchlist(ticker);
      fetchData();
    } catch (e) { /* silent */ }
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-2 mb-1">
        <Eye className="w-5 h-5 text-cyan-400" />
        <h1 className="text-2xl font-bold text-white">Watchlist</h1>
      </div>

      <div className="flex gap-2 max-w-md">
        <Input
          value={t}
          onChange={(e) => setT(e.target.value)}
          placeholder="Add ticker e.g. RELIANCE"
          className="bg-white/5 border-white/10 text-white"
        />
        <Button onClick={add} className="bg-emerald-500 text-slate-950"><Plus className="w-4 h-4" /></Button>
      </div>

      {items.length === 0 ? (
        <div className="bg-white/[0.03] border border-dashed border-white/10 rounded-xl py-12 text-center text-slate-400">
          Your watchlist is empty. Add tickers above.
        </div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
          {items.map(it => {
            const sd = it.stock_data || {};
            const pos = (sd.change_pct ?? 0) >= 0;
            return (
              <div key={it.ticker} className="bg-white/[0.04] border border-white/10 rounded-xl p-4 flex items-center justify-between">
                <button onClick={() => onSelectStock?.(it.ticker)} className="text-left flex-1 min-w-0">
                  <div className="text-white font-semibold">{it.ticker}</div>
                  <div className="text-xs text-slate-400 truncate">{sd.name || "—"}</div>
                  <div className="flex items-center gap-3 mt-1 text-xs">
                    <span className="text-white tabular-nums">{formatPrice(sd.price)}</span>
                    <span className={pos ? "text-emerald-400" : "text-rose-400"}>{formatPct(sd.change_pct)}</span>
                  </div>
                </button>
                <button onClick={() => remove(it.ticker)} className="text-slate-500 hover:text-rose-400 p-2"><Trash2 className="w-4 h-4" /></button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
