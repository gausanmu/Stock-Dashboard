import { useState } from "react";
import { formatCurrency } from "@/lib/format";
import { Calculator } from "lucide-react";

export default function PositionSizer() {
  const [accountSize, setAccountSize] = useState(80000);
  const [riskPct, setRiskPct] = useState(2);
  const [entry, setEntry] = useState("");
  const [stop, setStop] = useState("");

  const calculate = () => {
    const e = parseFloat(entry);
    const s = parseFloat(stop);
    if (!e || !s || e <= s) return null;

    const maxLossPerShare = e - s;
    const maxAccountLoss = accountSize * (riskPct / 100);
    const shares = Math.floor(maxAccountLoss / maxLossPerShare);
    const capitalRequired = shares * e;

    return { shares, maxAccountLoss, capitalRequired };
  };

  const res = calculate();

  return (
    <div className="bg-bg-card border border-border rounded-lg p-6 flex flex-col h-full">
      <div className="flex items-center gap-2 mb-4">
        <Calculator className="w-5 h-5 text-accent-blue" />
        <h3 className="text-lg font-bold">Kelly Position Sizer</h3>
      </div>
      
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div>
          <label className="block text-xs text-text-secondary mb-1">Capital (₹)</label>
          <input type="number" className="w-full bg-bg-primary border border-border rounded px-3 py-2" value={accountSize} onChange={e => setAccountSize(e.target.value)} />
        </div>
        <div>
          <label className="block text-xs text-text-secondary mb-1">Max Risk (%)</label>
          <input type="number" step="0.5" className="w-full bg-bg-primary border border-border rounded px-3 py-2" value={riskPct} onChange={e => setRiskPct(e.target.value)} />
        </div>
        <div>
          <label className="block text-xs text-text-secondary mb-1">Entry Price</label>
          <input type="number" className="w-full bg-bg-primary border border-border rounded px-3 py-2" value={entry} onChange={e => setEntry(e.target.value)} />
        </div>
        <div>
          <label className="block text-xs text-text-secondary mb-1">Stop Loss</label>
          <input type="number" className="w-full bg-bg-primary border border-border rounded px-3 py-2" value={stop} onChange={e => setStop(e.target.value)} />
        </div>
      </div>

      <div className="mt-auto bg-bg-elevated rounded p-4 border border-border">
        {res ? (
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-sm text-text-secondary">Optimal Shares:</span>
              <span className="font-bold text-accent-blue text-lg">{res.shares}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-text-secondary">Capital Required:</span>
              <span className="font-mono">{formatCurrency(res.capitalRequired)}</span>
            </div>
            <div className="flex justify-between text-accent-red">
              <span className="text-sm">Max Loss if Hit:</span>
              <span className="font-mono">{formatCurrency(res.maxAccountLoss)}</span>
            </div>
          </div>
        ) : (
          <div className="text-sm text-text-muted text-center py-4">Enter valid prices to calculate optimal sizing.</div>
        )}
      </div>
    </div>
  );
}
