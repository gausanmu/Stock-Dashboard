import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Plus, Trash2, Briefcase, Target, Clock, Shield, AlertTriangle, TrendingUp, TrendingDown } from "lucide-react";
import { toast } from "sonner";
import { formatPrice, formatPct } from "@/lib/format";

const ACTION_STYLES = {
  HOLD:          { color: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30", icon: Shield },
  BOOK_PROFIT:   { color: "bg-amber-500/15  text-amber-300  border-amber-500/30",  icon: TrendingUp },
  PARTIAL_BOOK:  { color: "bg-amber-500/15  text-amber-300  border-amber-500/30",  icon: TrendingUp },
  ADD:           { color: "bg-cyan-500/15   text-cyan-300   border-cyan-500/30",   icon: Plus },
  SELL:          { color: "bg-rose-500/15   text-rose-300   border-rose-500/30",   icon: TrendingDown },
  EXIT:          { color: "bg-rose-500/15   text-rose-300   border-rose-500/30",   icon: AlertTriangle },
};

export default function PortfolioView({ onSelectStock }) {
  const [data, setData] = useState({ items: [], summary: {}, risk: {} });
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState({
    ticker: "", buy_price: "", quantity: 1, profile: "LONG_TERM", buy_date: ""
  });
  const [loading, setLoading] = useState(true);

  const fetchPortfolio = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.getPortfolio();
      setData(res.data || { items: [], summary: {}, risk: {} });
    } catch (e) {
      toast.error("Could not load portfolio");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPortfolio();
    const t = setInterval(fetchPortfolio, 30000); // auto-refresh prices
    return () => clearInterval(t);
  }, [fetchPortfolio]);

  const handleAdd = async (e) => {
    e?.preventDefault?.();
    if (!form.ticker || !form.buy_price) {
      toast.error("Ticker and Buy Price are required");
      return;
    }
    try {
      await api.addToPortfolio({
        ticker: form.ticker.toUpperCase().replace(".NS", ""),
        buy_price: parseFloat(form.buy_price),
        quantity: parseInt(form.quantity) || 1,
        profile: form.profile,
        buy_date: form.buy_date ? new Date(form.buy_date).toISOString() : null,
        tag: "STAYER",
      });
      toast.success(`${form.ticker.toUpperCase()} added to portfolio`);
      setForm({ ticker: "", buy_price: "", quantity: 1, profile: "LONG_TERM", buy_date: "" });
      setAdding(false);
      fetchPortfolio();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to add");
    }
  };

  const handleRemove = async (ticker) => {
    if (!window.confirm(`Remove ${ticker} from portfolio?`)) return;
    try {
      await api.removeFromPortfolio(ticker);
      toast.success(`Removed ${ticker}`);
      fetchPortfolio();
    } catch (e) {
      toast.error("Failed to remove");
    }
  };

  const summary = data.summary || {};
  const totalPnlPositive = (summary.total_pnl ?? 0) >= 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Briefcase className="w-5 h-5 text-emerald-400" />
            <h1 className="text-2xl font-bold text-white tracking-tight">My Portfolio</h1>
          </div>
          <p className="text-sm text-slate-400">
            Persistently saved · Auto-refresh every 30s · Each holding gets profile-aware target & holding-period guidance.
          </p>
        </div>
        <Button onClick={() => setAdding(v => !v)} className="bg-gradient-to-r from-emerald-500 to-cyan-500 text-slate-950 font-semibold">
          <Plus className="w-4 h-4 mr-2" />
          Add Holding
        </Button>
      </div>

      {/* Add form */}
      {adding && (
        <form onSubmit={handleAdd} className="bg-white/[0.04] border border-white/10 rounded-xl p-4 grid md:grid-cols-6 gap-3">
          <div className="md:col-span-1">
            <label className="text-[10px] text-slate-400 uppercase tracking-wider">Ticker</label>
            <Input
              value={form.ticker}
              onChange={(e) => setForm({ ...form, ticker: e.target.value })}
              placeholder="RELIANCE"
              className="bg-white/5 border-white/10 text-white"
            />
          </div>
          <div className="md:col-span-1">
            <label className="text-[10px] text-slate-400 uppercase tracking-wider">Buy Price (₹)</label>
            <Input
              type="number" step="0.01"
              value={form.buy_price}
              onChange={(e) => setForm({ ...form, buy_price: e.target.value })}
              placeholder="1450.50"
              className="bg-white/5 border-white/10 text-white"
            />
          </div>
          <div className="md:col-span-1">
            <label className="text-[10px] text-slate-400 uppercase tracking-wider">Quantity</label>
            <Input
              type="number"
              value={form.quantity}
              onChange={(e) => setForm({ ...form, quantity: e.target.value })}
              className="bg-white/5 border-white/10 text-white"
            />
          </div>
          <div className="md:col-span-1">
            <label className="text-[10px] text-slate-400 uppercase tracking-wider">Trader Profile</label>
            <Select value={form.profile} onValueChange={(v) => setForm({ ...form, profile: v })}>
              <SelectTrigger className="bg-white/5 border-white/10 text-white"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="LONG_TERM">Long-Term</SelectItem>
                <SelectItem value="SWING">Swing</SelectItem>
                <SelectItem value="SHORT_TERM">Short-Term</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="md:col-span-1">
            <label className="text-[10px] text-slate-400 uppercase tracking-wider">Buy Date</label>
            <Input
              type="date"
              value={form.buy_date}
              onChange={(e) => setForm({ ...form, buy_date: e.target.value })}
              className="bg-white/5 border-white/10 text-white"
            />
          </div>
          <div className="md:col-span-1 flex items-end gap-2">
            <Button type="submit" className="flex-1 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-semibold">Save</Button>
            <Button type="button" variant="ghost" onClick={() => setAdding(false)} className="text-slate-400">Cancel</Button>
          </div>
        </form>
      )}

      {/* Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <SummaryCard label="Invested"     value={formatPrice(summary.total_invested)} />
        <SummaryCard label="Current Value" value={formatPrice(summary.total_current)} />
        <SummaryCard label="Unrealized P&L"
          value={formatPrice(summary.total_pnl)}
          tone={totalPnlPositive ? "good" : "bad"}
        />
        <SummaryCard label="Return"
          value={formatPct(summary.total_pnl_pct)}
          tone={totalPnlPositive ? "good" : "bad"}
        />
      </div>

      {/* Risk warnings */}
      {data.risk?.warnings?.length > 0 && (
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4">
          <div className="flex items-center gap-2 text-amber-300 font-semibold mb-2">
            <AlertTriangle className="w-4 h-4" />
            Risk warnings
          </div>
          <ul className="text-sm text-amber-200/90 space-y-1 list-disc pl-5">
            {data.risk.warnings.map((w, i) => <li key={i}>{w}</li>)}
          </ul>
        </div>
      )}

      {/* Holdings list */}
      {loading ? (
        <div className="text-center py-12 text-slate-400">Loading…</div>
      ) : data.items.length === 0 ? (
        <div className="bg-white/[0.03] border border-dashed border-white/10 rounded-2xl py-16 text-center">
          <Briefcase className="w-10 h-10 text-slate-600 mx-auto mb-3" />
          <div className="text-slate-300 font-medium mb-1">No holdings yet</div>
          <div className="text-sm text-slate-500 mb-4">Add your first stock — it'll be saved permanently and tracked with target + holding guidance.</div>
          <Button onClick={() => setAdding(true)} className="bg-emerald-500 text-slate-950">
            <Plus className="w-4 h-4 mr-2" /> Add Holding
          </Button>
        </div>
      ) : (
        <div className="grid lg:grid-cols-2 gap-3">
          {data.items.map(it => (
            <HoldingCard key={it.ticker} item={it} onSelect={() => onSelectStock?.(it.ticker)} onRemove={() => handleRemove(it.ticker)} />
          ))}
        </div>
      )}
    </div>
  );
}

function SummaryCard({ label, value, tone }) {
  const toneClass = tone === "good" ? "text-emerald-300" : tone === "bad" ? "text-rose-300" : "text-white";
  return (
    <div className="bg-white/[0.04] border border-white/10 rounded-xl p-4">
      <div className="text-[10px] uppercase tracking-widest text-slate-400 font-semibold">{label}</div>
      <div className={`text-xl font-bold mt-1 tabular-nums ${toneClass}`}>{value}</div>
    </div>
  );
}

function HoldingCard({ item, onSelect, onRemove }) {
  const r = item.recommendation || {};
  const positive = (item.pnl ?? 0) >= 0;
  const ActionIcon = (ACTION_STYLES[r.action] || ACTION_STYLES.HOLD).icon;
  const actionStyle = (ACTION_STYLES[r.action] || ACTION_STYLES.HOLD).color;

  // progress: how close to target (0%=at buy, 100%=at target)
  const progress = item.buy_price && r.target_price
    ? Math.max(0, Math.min(100, ((item.current_price - item.buy_price) / (r.target_price - item.buy_price)) * 100))
    : 0;

  return (
    <div className="bg-gradient-to-br from-white/[0.05] to-white/[0.02] border border-white/10 rounded-xl p-4 hover:border-white/20 transition-colors">
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <button onClick={onSelect} className="text-left flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <div className="text-white font-bold text-lg tracking-tight">{item.ticker}</div>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/5 border border-white/10 text-slate-300 uppercase tracking-wider">
              {item.profile}
            </span>
          </div>
          <div className="text-xs text-slate-400 truncate">{item.name}</div>
        </button>
        <button onClick={onRemove} className="text-slate-500 hover:text-rose-400 p-1">
          <Trash2 className="w-4 h-4" />
        </button>
      </div>

      {/* Prices row */}
      <div className="grid grid-cols-3 gap-2 mb-3">
        <div className="bg-white/[0.03] rounded-md p-2">
          <div className="text-[9px] uppercase tracking-wider text-slate-500">Buy</div>
          <div className="text-white font-semibold tabular-nums">{formatPrice(item.buy_price)}</div>
        </div>
        <div className="bg-white/[0.03] rounded-md p-2">
          <div className="text-[9px] uppercase tracking-wider text-slate-500">LTP</div>
          <div className="text-white font-semibold tabular-nums">{formatPrice(item.current_price)}</div>
        </div>
        <div className={`rounded-md p-2 ${positive ? "bg-emerald-500/10" : "bg-rose-500/10"}`}>
          <div className="text-[9px] uppercase tracking-wider text-slate-500">P&L</div>
          <div className={`font-semibold tabular-nums ${positive ? "text-emerald-300" : "text-rose-300"}`}>
            {formatPct(item.pnl_pct)}
          </div>
        </div>
      </div>

      {/* Progress bar to target */}
      <div className="mb-3">
        <div className="flex items-center justify-between text-[10px] text-slate-400 mb-1">
          <span>Buy ₹{item.buy_price}</span>
          <span>Target ₹{r.target_price ?? "-"}</span>
        </div>
        <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-emerald-500 to-cyan-400 transition-all"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Recommendation card */}
      <div className="grid grid-cols-3 gap-2 mb-3">
        <RecCell icon={Target} label="Target"  value={formatPrice(r.target_price)} sub={`${r.target_gain_pct ?? 0}%`} tone="emerald" />
        <RecCell icon={Shield} label="Stop"    value={formatPrice(r.stop_price)}   sub={`${r.downside_pct_from_now ?? 0}%`} tone="rose" />
        <RecCell icon={Clock}  label="Hold"    value={r.holding_period?.split("•")[0] || `${r.hold_min}-${r.hold_max}`} sub={r.hold_unit} tone="blue" />
      </div>

      {/* Action + rationale */}
      <div className={`flex items-start gap-2 rounded-lg border px-3 py-2 ${actionStyle}`}>
        <ActionIcon className="w-4 h-4 mt-0.5 shrink-0" />
        <div className="text-xs">
          <div className="font-semibold">{r.action?.replace("_", " ") || "HOLD"}</div>
          <div className="opacity-80">{r.rationale || "Continue monitoring."}</div>
        </div>
      </div>

      {/* Days held */}
      {r.days_held !== null && r.days_held !== undefined && (
        <div className="mt-2 text-[11px] text-slate-500 flex items-center gap-3">
          <span>📅 Held {r.days_held} day{r.days_held !== 1 ? "s" : ""}</span>
          <span>⚖️ R:R {r.risk_reward}</span>
          <span>📦 Qty {item.quantity}</span>
        </div>
      )}
    </div>
  );
}

function RecCell({ icon: Icon, label, value, sub, tone }) {
  const toneText = {
    emerald: "text-emerald-300",
    rose:    "text-rose-300",
    blue:    "text-blue-300",
  }[tone] || "text-white";
  return (
    <div className="bg-white/[0.03] rounded-md p-2">
      <div className="flex items-center gap-1 text-[9px] uppercase tracking-wider text-slate-500 mb-0.5">
        <Icon className="w-3 h-3" /> {label}
      </div>
      <div className={`font-bold text-sm tabular-nums ${toneText}`}>{value}</div>
      {sub && <div className="text-[10px] text-slate-500">{sub}</div>}
    </div>
  );
}
