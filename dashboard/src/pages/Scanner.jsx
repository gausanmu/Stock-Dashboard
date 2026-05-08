import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import { Loader2, RefreshCw, Play } from "lucide-react";
import ScannerTopPicks from "@/components/scanner/ScannerTopPicks";
import ScannerResultsTable from "@/components/scanner/ScannerResultsTable";
import { cn } from "@/lib/utils";

const PROFILES = [
  { id: "LONG_TERM", label: "Long Term (6+ months)" },
  { id: "SWING", label: "Swing (5-25 days)" },
  { id: "SHORT_TERM", label: "Short Term (1-3 days)" },
];

export default function Scanner() {
  const [activeProfile, setActiveProfile] = useState("LONG_TERM");
  const [universe, setUniverse] = useState("nifty500");
  const [levels, setLevels] = useState({});
  const [data, setData] = useState({ results: [], timestamp: null, status: null });
  const [loading, setLoading] = useState(true);
  const [scanStatus, setScanStatus] = useState({ running: false, progress: 0, total: 0 });

  // Load available universes
  useEffect(() => {
    api.getScanLevels().then(res => setLevels(res.data)).catch(console.error);
  }, []);

  const loadResults = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.getScanResults(universe);
      // Filter results down to the active profile in the frontend to avoid multiple backend calls
      // if we only have one massive DB collection. Wait, the backend already filters? 
      // Actually, the scan is run per profile. We should re-fetch.
      setData(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [universe]); // We reload results when universe changes

  // Poll scan status
  useEffect(() => {
    let interval;
    const checkStatus = async () => {
      try {
        const res = await api.getScanStatus();
        setScanStatus(res.data);
        if (res.data.running) {
          if (!interval) interval = setInterval(checkStatus, 2000);
        } else {
          if (interval) {
            clearInterval(interval);
            loadResults(); // Scan finished, reload
          }
        }
      } catch (e) {
        console.error(e);
      }
    };
    checkStatus();
    return () => { if (interval) clearInterval(interval); };
  }, [loadResults]);

  useEffect(() => {
    loadResults();
  }, [loadResults, activeProfile]);

  const handleStartScan = async () => {
    try {
      await api.startScan(universe, activeProfile);
      setScanStatus({ running: true, progress: 0, total: 100 });
    } catch (e) {
      alert("Failed to start scan: " + (e.response?.data?.detail || e.message));
    }
  };

  // The backend scan_results collection holds results for the specific profile.
  // Wait, if we switch tabs, we need to trigger a fetch.

  return (
    <div className="h-full flex flex-col space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-text-primary">Scanner</h1>
          <p className="text-sm text-text-secondary mt-1">
            Algorithmic screening across {levels[universe]?.label || "the market"}.
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          <select 
            className="bg-bg-card border border-border text-sm rounded-md px-3 py-2 text-text-primary outline-none focus:border-accent-blue"
            value={universe}
            onChange={(e) => setUniverse(e.target.value)}
            disabled={scanStatus.running}
          >
            {Object.entries(levels).map(([key, info]) => (
              <option key={key} value={key}>{info.label} ({info.count})</option>
            ))}
          </select>

          <button 
            onClick={handleStartScan}
            disabled={scanStatus.running}
            className="flex items-center gap-2 bg-accent-blue hover:bg-accent-blue/90 disabled:opacity-50 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors"
          >
            {scanStatus.running ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            {scanStatus.running ? "Scanning..." : "Run Scan"}
          </button>
        </div>
      </div>

      {scanStatus.running && (
        <div className="bg-bg-card border border-border rounded-lg p-4">
          <div className="flex justify-between text-xs text-text-secondary mb-2">
            <span>Scanning {scanStatus.universe} for {scanStatus.profile}...</span>
            <span>{scanStatus.progress} / {scanStatus.total} ({scanStatus.fail_count} failed)</span>
          </div>
          <div className="h-2 w-full bg-bg-elevated rounded-full overflow-hidden">
            <div 
              className="h-full bg-accent-blue transition-all duration-300"
              style={{ width: `${(scanStatus.progress / Math.max(scanStatus.total, 1)) * 100}%` }}
            />
          </div>
          <div className="text-xs text-text-muted mt-2 truncate">Current: {scanStatus.current_ticker}</div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-border">
        {PROFILES.map(p => (
          <button
            key={p.id}
            onClick={() => setActiveProfile(p.id)}
            className={cn(
              "px-6 py-3 text-sm font-medium border-b-2 transition-colors",
              activeProfile === p.id 
                ? "border-accent-blue text-accent-blue bg-accent-blue/5" 
                : "border-transparent text-text-secondary hover:text-text-primary hover:bg-bg-hover"
            )}
          >
            {p.label}
          </button>
        ))}
      </div>

      {loading && data.results.length === 0 ? (
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="w-8 h-8 text-accent-blue animate-spin" />
        </div>
      ) : (
        <div className="flex-1 flex flex-col min-h-0">
          <ScannerTopPicks items={data.results.filter(r => r.profile === activeProfile || r.regime !== 'UNKNOWN')} />
          <div className="flex-1 min-h-0">
            <ScannerResultsTable items={data.results} />
          </div>
          
          <div className="mt-4 text-xs text-text-muted text-right">
            Last updated: {data.timestamp ? new Date(data.timestamp).toLocaleString() : "Never"}
          </div>
        </div>
      )}
    </div>
  );
}
