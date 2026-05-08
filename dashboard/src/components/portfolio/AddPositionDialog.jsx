import { useState } from "react";
import { api } from "@/lib/api";
import { Plus, Loader2 } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";

export default function AddPositionDialog({ onAdded }) {
  const [open, setOpen] = useState(false);
  const [ticker, setTicker] = useState("");
  const [buyPrice, setBuyPrice] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [profile, setProfile] = useState("LONG_TERM");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    if (!ticker || !buyPrice || !quantity) {
      setError("Please fill all required fields");
      return;
    }

    setLoading(true);
    try {
      await api.addToPortfolio({
        ticker: ticker.toUpperCase(),
        buy_price: parseFloat(buyPrice),
        quantity: parseInt(quantity),
        profile: profile,
        tag: "STAYER"
      });
      setOpen(false);
      setTicker("");
      setBuyPrice("");
      setQuantity("1");
      if (onAdded) onAdded();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to add position");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <button className="flex items-center gap-2 bg-accent-blue hover:bg-accent-blue/90 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors">
          <Plus className="w-4 h-4" /> Add Position
        </button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md bg-bg-card border-border text-text-primary">
        <DialogHeader>
          <DialogTitle>Add to Portfolio</DialogTitle>
        </DialogHeader>
        
        <form onSubmit={handleSubmit} className="space-y-4 mt-4">
          {error && <div className="p-3 bg-accent-red/10 text-accent-red text-sm rounded border border-accent-red/20">{error}</div>}
          
          <div className="grid grid-cols-4 items-center gap-4">
            <label className="text-sm font-medium text-text-secondary">Ticker</label>
            <input 
              className="col-span-3 bg-bg-primary border border-border rounded px-3 py-2 text-sm uppercase"
              placeholder="e.g. RELIANCE"
              value={ticker}
              onChange={(e) => setTicker(e.target.value)}
            />
          </div>
          
          <div className="grid grid-cols-4 items-center gap-4">
            <label className="text-sm font-medium text-text-secondary">Avg Price</label>
            <input 
              type="number"
              step="0.05"
              className="col-span-3 bg-bg-primary border border-border rounded px-3 py-2 text-sm"
              placeholder="e.g. 2450.50"
              value={buyPrice}
              onChange={(e) => setBuyPrice(e.target.value)}
            />
          </div>

          <div className="grid grid-cols-4 items-center gap-4">
            <label className="text-sm font-medium text-text-secondary">Quantity</label>
            <input 
              type="number"
              min="1"
              className="col-span-3 bg-bg-primary border border-border rounded px-3 py-2 text-sm"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
            />
          </div>

          <div className="grid grid-cols-4 items-center gap-4">
            <label className="text-sm font-medium text-text-secondary">Strategy</label>
            <select 
              className="col-span-3 bg-bg-primary border border-border rounded px-3 py-2 text-sm"
              value={profile}
              onChange={(e) => setProfile(e.target.value)}
            >
              <option value="LONG_TERM">Long Term (6+ months)</option>
              <option value="SWING">Swing (5-25 days)</option>
              <option value="SHORT_TERM">Short Term (1-3 days)</option>
            </select>
          </div>

          <div className="flex justify-end pt-4 border-t border-border mt-6">
            <button 
              type="submit" 
              disabled={loading}
              className="flex items-center gap-2 bg-accent-blue hover:bg-accent-blue/90 disabled:opacity-50 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors"
            >
              {loading && <Loader2 className="w-4 h-4 animate-spin" />}
              Save Position
            </button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
