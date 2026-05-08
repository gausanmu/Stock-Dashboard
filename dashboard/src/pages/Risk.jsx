import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import DrawdownGauge from "@/components/risk/DrawdownGauge";
import CorrelationMatrix from "@/components/risk/CorrelationMatrix";
import SectorHeatmap from "@/components/risk/SectorHeatmap";
import PositionSizer from "@/components/risk/PositionSizer";
import { Loader2 } from "lucide-react";

export default function Risk() {
  const [data, setData] = useState({ summary: null, risk: null });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getPortfolio()
      .then(res => setData({ summary: res.data.summary, risk: res.data.risk }))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-accent-blue animate-spin" />
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col space-y-6 overflow-y-auto pb-10">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-text-primary">Risk Dashboard</h1>
        <p className="text-sm text-text-secondary mt-1">
          Monitor portfolio exposure, correlation overlap, and size new positions mathematically.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <DrawdownGauge summary={data.summary} risk={data.risk} />
        </div>
        <div className="lg:col-span-2">
          <SectorHeatmap />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <CorrelationMatrix />
        </div>
        <div className="lg:col-span-1">
          <PositionSizer />
        </div>
      </div>
    </div>
  );
}
