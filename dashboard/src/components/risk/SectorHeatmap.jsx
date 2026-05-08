import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { Loader2 } from "lucide-react";
import { formatPct } from "@/lib/format";
import { cn } from "@/lib/utils";

export default function SectorHeatmap() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getSectorHeatmap()
      .then(res => setData(res.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-8 flex justify-center"><Loader2 className="animate-spin text-accent-blue" /></div>;
  if (!data || data.length === 0) return <div className="p-8 text-center text-text-secondary">No sector data</div>;

  const maxCount = Math.max(...data.map(d => d.count));

  const getColor = (avgChange) => {
    if (avgChange > 2) return "bg-accent-green text-bg-primary font-medium";
    if (avgChange > 0) return "bg-accent-green/30 text-accent-green";
    if (avgChange > -2) return "bg-accent-red/30 text-accent-red";
    return "bg-accent-red text-bg-primary font-medium";
  };

  return (
    <div className="bg-bg-card border border-border rounded-lg p-6 flex flex-col h-full">
      <h3 className="text-lg font-bold mb-1">Sector Heatmap</h3>
      <p className="text-xs text-text-secondary mb-4">Size = Stock Count. Color = Avg Return.</p>
      
      <div className="flex-1 flex flex-wrap content-start gap-2">
        {data.map(sec => {
          // Simple treemap-like scaling
          const flexGrow = Math.max(1, (sec.count / maxCount) * 10);
          
          return (
            <div 
              key={sec.sector} 
              className={cn("p-3 rounded border border-border/50 flex flex-col justify-between transition-transform hover:scale-105", getColor(sec.avg_change))}
              style={{ flexGrow, flexBasis: `${Math.max(100, flexGrow * 20)}px` }}
            >
              <div className="font-bold text-sm mb-2">{sec.sector}</div>
              <div className="flex justify-between items-end">
                <span className="text-xs opacity-80">{sec.count} stocks</span>
                <span className="font-mono text-sm">{formatPct(sec.avg_change)}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
