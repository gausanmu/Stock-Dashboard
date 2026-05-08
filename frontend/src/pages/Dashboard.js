import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import { Toaster } from "sonner";
import Sidebar from "@/components/layout/Sidebar";
import TopBar from "@/components/layout/TopBar";
import OverviewView from "@/components/views/OverviewView";
import TraderModeView from "@/components/views/TraderModeView";
import PortfolioView from "@/components/views/PortfolioView";
import WatchlistView from "@/components/views/WatchlistView";
import SectorsView from "@/components/views/SectorsView";
import AlertsView from "@/components/views/AlertsView";
import EveningScannerView from "@/components/views/EveningScannerView";
import NewsView from "@/components/views/NewsView";
import DeepDiveSheet from "@/components/DeepDiveSheet";
import { toast } from "sonner";

// Maps section id -> backend profile (used for the "Run Scan" button in TopBar)
const SECTION_TO_PROFILE = {
  long_term:  "LONG_TERM",
  swing:      "SWING",
  short_term: "SHORT_TERM",
};

export default function Dashboard() {
  const [section, setSection] = useState("overview");
  const [searchQuery, setSearchQuery] = useState("");
  const [scanStatus, setScanStatus] = useState({ running: false, progress: 0, total: 0, profile: "LONG_TERM" });
  const [macro, setMacro] = useState({});
  const [confidence, setConfidence] = useState({ score: 50, status: "CAUTIOUS" });
  const [selectedStock, setSelectedStock] = useState(null);
  const [selectedStockData, setSelectedStockData] = useState(null);
  const [universe, setUniverse] = useState("nifty50");

  // Fetch stock detail when a ticker is selected
  useEffect(() => {
    if (!selectedStock) {
      setSelectedStockData(null);
      return;
    }
    api.getStockDetail(selectedStock)
      .then(r => setSelectedStockData(r.data))
      .catch(() => {
        toast.error(`No data for ${selectedStock}. Run a scan first or check ticker.`);
        setSelectedStockData(null);
        setSelectedStock(null);
      });
  }, [selectedStock]);

  const handleAddToWatchlist = async (ticker) => {
    try {
      await api.addToWatchlist({ ticker, tag: "STAYER" });
      toast.success(`${ticker} added to watchlist`);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed");
    }
  };

  const handleAddToPortfolio = async (data) => {
    try {
      await api.addToPortfolio({ ...data, profile: activeProfile, buy_date: new Date().toISOString() });
      toast.success(`${data.ticker} added to portfolio`);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed");
    }
  };

  // Poll scan status whenever scanning
  const fetchScanStatus = useCallback(async () => {
    try {
      const res = await api.getScanStatus();
      setScanStatus(res.data || {});
    } catch (e) { /* silent */ }
  }, []);

  useEffect(() => {
    fetchScanStatus();
    const t = setInterval(fetchScanStatus, 2500);
    return () => clearInterval(t);
  }, [fetchScanStatus]);

  // Macro & confidence
  useEffect(() => {
    const load = () => {
      api.getConfidence().then(r => {
        setMacro(r.data?.macro || {});
        setConfidence({ score: r.data?.score, status: r.data?.status });
      }).catch(() => {});
    };
    load();
    const t = setInterval(load, 60000);
    return () => clearInterval(t);
  }, []);

  // Active profile for TopBar pill: derive from section, else fallback to current scan profile
  const activeProfile = SECTION_TO_PROFILE[section] || scanStatus.profile || "LONG_TERM";

  const handleScan = async () => {
    if (scanStatus.running) {
      toast.info(`Already scanning (${scanStatus.profile})`);
      return;
    }
    try {
      await api.startScan(universe, activeProfile);
      const label = universe.replace(/^./, c => c.toUpperCase());
      toast.success(`Scanning ${label} in ${activeProfile.replace("_", " ")} mode`);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to start");
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    const q = searchQuery.trim().toUpperCase().replace(".NS", "");
    setSelectedStock(q);
  };

  const renderSection = () => {
    switch (section) {
      case "overview":
        return <OverviewView onNavigate={setSection} />;
      case "long_term":
      case "swing":
      case "short_term":
        return (
          <TraderModeView
            mode={section}
            scanStatus={scanStatus}
            universe={universe}
            onSelectStock={(t) => setSelectedStock(t)}
          />
        );
      case "news":
        return <NewsView onSelectStock={(t) => setSelectedStock(t)} />;
      case "portfolio":
        return <PortfolioView onSelectStock={(t) => setSelectedStock(t)} />;
      case "watchlist":
        return <WatchlistView onSelectStock={(t) => setSelectedStock(t)} />;
      case "sectors":
        return <SectorsView />;
      case "alerts":
        return <AlertsView />;
      case "evening_scanner":
        return <EveningScannerView onSelectStock={(t) => setSelectedStock(t)} />;
      default:
        return <OverviewView onNavigate={setSection} />;
    }
  };

  return (
    <div className="flex flex-col md:flex-row h-screen bg-slate-950 text-white overflow-hidden" data-testid="dashboard-root">
      {/* Background layers */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-0 left-1/4 w-[600px] h-[600px] bg-emerald-500/10 rounded-full blur-3xl" />
        <div className="absolute bottom-0 right-1/4 w-[500px] h-[500px] bg-fuchsia-500/10 rounded-full blur-3xl" />
        <div
          className="absolute inset-0 opacity-[0.02]"
          style={{
            backgroundImage:
              "radial-gradient(circle at 1px 1px, white 1px, transparent 0)",
            backgroundSize: "32px 32px",
          }}
        />
      </div>

      <Sidebar active={section} onChange={setSection} />

      <div className="flex-1 flex flex-col min-w-0 relative">
        <TopBar
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          onSearch={handleSearch}
          profile={activeProfile}
          scanStatus={scanStatus}
          onScan={handleScan}
          macro={macro}
          confidence={confidence}
          universe={universe}
          onUniverseChange={setUniverse}
        />

        {/* Scan progress strip */}
        {scanStatus.running && (
          <div className="px-6 py-2 bg-emerald-500/10 border-b border-emerald-500/20 text-xs text-emerald-200 flex items-center gap-3" data-testid="scan-progress-strip">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span>Scanning {scanStatus.universe || scanStatus.profile?.replace("_", " ")} · {scanStatus.current_ticker}</span>
            <div className="flex-1 h-1 bg-emerald-900/40 rounded-full overflow-hidden">
              <div className="h-full bg-emerald-400 transition-all" style={{ width: `${(scanStatus.progress / Math.max(scanStatus.total, 1)) * 100}%` }} />
            </div>
            <span className="tabular-nums">{scanStatus.progress}/{scanStatus.total}</span>
          </div>
        )}

        <main className="flex-1 overflow-y-auto px-6 py-6">
          {renderSection()}
        </main>
      </div>

      <DeepDiveSheet
        stock={selectedStockData}
        onClose={() => setSelectedStock(null)}
        onAddToWatchlist={handleAddToWatchlist}
        onAddToPortfolio={handleAddToPortfolio}
      />

      <Toaster theme="dark" position="top-right" richColors />
    </div>
  );
}
