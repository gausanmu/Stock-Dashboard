import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import HoldingsTable from "@/components/portfolio/HoldingsTable";
import PortfolioSummary from "@/components/portfolio/PortfolioSummary";
import AddPositionDialog from "@/components/portfolio/AddPositionDialog";
import { Loader2 } from "lucide-react";

export default function Portfolio() {
  const [data, setData] = useState({ items: [], summary: null, risk: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadPortfolio = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.getPortfolio();
      setData(res.data);
      setError("");
    } catch (err) {
      console.error(err);
      setError("Failed to load portfolio. Make sure the backend is running.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPortfolio();
    const interval = setInterval(loadPortfolio, 60000); // refresh every minute
    return () => clearInterval(interval);
  }, [loadPortfolio]);

  const handleRemove = async (ticker) => {
    if (!window.confirm(`Remove ${ticker} from portfolio?`)) return;
    try {
      await api.removeFromPortfolio(ticker);
      loadPortfolio();
    } catch (err) {
      alert("Failed to remove position");
    }
  };

  return (
    <div className="h-full flex flex-col space-y-6">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-text-primary">Portfolio</h1>
          <p className="text-sm text-text-secondary mt-1">
            Live holdings, P&L, and algorithmic recommendations based on your entry price.
          </p>
        </div>
        <AddPositionDialog onAdded={loadPortfolio} />
      </div>

      {error ? (
        <div className="bg-accent-red/10 border border-accent-red/20 text-accent-red p-4 rounded-md">
          {error}
        </div>
      ) : loading && !data.summary ? (
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="w-8 h-8 text-accent-blue animate-spin" />
        </div>
      ) : (
        <>
          <PortfolioSummary summary={data.summary} risk={data.risk} />
          
          <div className="flex-1 overflow-hidden flex flex-col">
            <h3 className="text-lg font-semibold mb-4 text-text-primary">Holdings</h3>
            <div className="flex-1 overflow-y-auto pr-2 pb-10">
              <HoldingsTable items={data.items} onRemove={handleRemove} />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
