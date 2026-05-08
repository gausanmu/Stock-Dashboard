import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export default function CorrelationMatrix() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getCorrelationMatrix()
      .then(res => setData(res.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-8 flex justify-center"><Loader2 className="animate-spin text-accent-blue" /></div>;
  if (!data || !data.matrix || data.matrix.length === 0) return <div className="p-8 text-center text-text-secondary">Not enough stocks for correlation matrix</div>;

  const getCellColor = (val) => {
    if (val === 1) return "bg-bg-elevated text-text-muted"; // Self
    if (val > 0.7) return "bg-accent-red/20 text-accent-red font-bold"; // High positive (Warning)
    if (val > 0.3) return "bg-accent-amber/20 text-accent-amber"; // Mild positive
    if (val < -0.3) return "bg-accent-green/20 text-accent-green font-bold"; // Negative (Good for hedge)
    return "bg-bg-primary text-text-secondary"; // Uncorrelated
  };

  return (
    <div className="bg-bg-card border border-border rounded-lg p-6 overflow-x-auto">
      <h3 className="text-lg font-bold mb-1">Correlation Matrix</h3>
      <p className="text-xs text-text-secondary mb-4">Values &gt; 0.7 indicate dangerous overlap.</p>
      
      <table className="w-full text-xs">
        <thead>
          <tr>
            <th className="p-2"></th>
            {data.tickers.map(t => <th key={t} className="p-2 font-medium text-text-secondary writing-vertical">{t}</th>)}
          </tr>
        </thead>
        <tbody>
          {data.tickers.map((t1, i) => (
            <tr key={t1}>
              <td className="p-2 font-medium text-text-secondary text-right">{t1}</td>
              {data.matrix[i].map((val, j) => (
                <td key={j} className="p-1">
                  <div className={cn("w-10 h-10 flex items-center justify-center rounded mono-num", getCellColor(val))}>
                    {val.toFixed(2)}
                  </div>
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
