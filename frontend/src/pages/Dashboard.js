import { useState, useEffect, useCallback, useMemo } from "react";
import { api } from "@/lib/api";
import { formatPrice, formatPct } from "@/lib/format";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Toaster, toast } from "sonner";
import { Search, Zap, RefreshCw, Trash2 } from "lucide-react";
import MacroTicker from "@/components/MacroTicker";
import ConfidenceWidget from "@/components/ConfidenceWidget";
import RegimeColumns from "@/components/RegimeColumns";
import StockTable from "@/components/StockTable";
import DeepDiveSheet from "@/components/DeepDiveSheet";

const BG_URL =
  "https://static.prod-images.emergentagent.com/jobs/3c68d8fc-9668-415d-a584-88ba9543e01c/images/57253c15b4486be9a987376253f6a2b340e5b3635b30147c600dbce901365f55.png";

export default function Dashboard() {
  const [stocks, setStocks] = useState([]);
  const [macro, setMacro] = useState({});
  const [confidence, setConfidence] = useState({ score: 50, status: "CAUTIOUS" });
  const [watchlist, setWatchlist] = useState([]);
  const [portfolio, setPortfolio] = useState({ items: [], summary: {} });
  const [selectedStock, setSelectedStock] = useState(null);
  const [activeTab, setActiveTab] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [scanStatus, setScanStatus] = useState({ running: false, progress: 0, total: 0 });
  const [loading, setLoading] = useState(true);
  const [sectors, setSectors] = useState([]);
  const [regimeChanges, setRegimeChanges] = useState([]);

  const fetchStocks = useCallback(async () => {
    try {
      const res = await api.getStocks();
      setStocks(res.data || []);
    } catch (e) { /* silent */ }
  }, []);

  const fetchMacro = useCallback(async () => {
    try {
      const res = await api.getConfidence();
      setMacro(res.data?.macro || {});
      setConfidence({ score: res.data?.score, status: res.data?.status });
    } catch (e) { /* silent */ }
  }, []);

  const fetchWatchlist = useCallback(async () => {
    try {
      const res = await api.getWatchlist();
      setWatchlist(res.data || []);
    } catch (e) { /* silent */ }
  }, []);

  const fetchPortfolio = useCallback(async () => {
    try {
      const res = await api.getPortfolio();
      setPortfolio(res.data || { items: [], summary: {} });
    } catch (e) { /* silent */ }
  }, []);

  const fetchSectors = useCallback(async () => {
    try {
      const res = await api.getSectorHeatmap();
      setSectors(res.data || []);
    } catch (e) { /* silent */ }
  }, []);

  const fetchRegimeChanges = useCallback(async () => {
    try {
      const res = await api.getRegimeChanges(20);
      setRegimeChanges(res.data || []);
    } catch (e) { /* silent */ }
  }, []);

  const fetchScanStatus = useCallback(async () => {
    try {
      const res = await api.getScanStatus();
      const prev = scanStatus.running;
      setScanStatus(res.data);
      if (prev && !res.data.running) {
        toast.success(`Scan complete! ${res.data.progress} stocks analyzed.`);
        fetchStocks();
      }
    } catch (e) { /* silent */ }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scanStatus.running, fetchStocks]);

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      await Promise.all([fetchStocks(), fetchMacro(), fetchWatchlist(), fetchPortfolio(), fetchSectors(), fetchRegimeChanges()]);
      const ss = await api.getScanStatus().catch(() => ({ data: {} }));
      setScanStatus(ss.data || {});
      setLoading(false);
    };
    init();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!scanStatus.running) return;
    const id = setInterval(() => {
      fetchScanStatus();
      fetchStocks();
    }, 5000);
    return () => clearInterval(id);
  }, [scanStatus.running, fetchScanStatus, fetchStocks]);

  const handleStartScan = async (universe = "nifty50") => {
    try {
      await api.startScan(universe);
      setScanStatus({ running: true, progress: 0, total: universe === "nifty50" ? 50 : 100 });
      toast.info("Scan started! Analyzing stocks...");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to start scan");
    }
  };

  const handleAddToWatchlist = async (ticker, tag = "STAYER") => {
    try {
      await api.addToWatchlist({ ticker: ticker.toUpperCase(), tag });
      toast.success(`${ticker} added to watchlist`);
      fetchWatchlist();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to add");
    }
  };

  const handleRemoveWatchlist = async (ticker) => {
    try {
      await api.removeFromWatchlist(ticker);
      toast.success(`${ticker} removed`);
      fetchWatchlist();
    } catch (e) {
      toast.error("Failed to remove");
    }
  };

  const handleAddToPortfolio = async (data) => {
    try {
      await api.addToPortfolio(data);
      toast.success(`${data.ticker} added to portfolio`);
      fetchPortfolio();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to add");
    }
  };

  const handleRemovePortfolio = async (ticker) => {
    try {
      await api.removeFromPortfolio(ticker);
      toast.success(`${ticker} removed`);
      fetchPortfolio();
    } catch (e) {
      toast.error("Failed to remove");
    }
  };

  const watchlistTickers = useMemo(
    () => new Set(watchlist.map((w) => w.ticker)),
    [watchlist]
  );

  const filteredStocks = useMemo(() => {
    let list = stocks;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      list = list.filter(
        (s) =>
          s.ticker?.toLowerCase().includes(q) ||
          s.name?.toLowerCase().includes(q) ||
          s.sector?.toLowerCase().includes(q)
      );
    }
    return list;
  }, [stocks, searchQuery]);

  const tabStocks = useMemo(() => {
    switch (activeTab) {
      case "sprinters":
        return filteredStocks.filter((s) => s.regime === "SPRINTER");
      case "compounders":
        return filteredStocks.filter((s) => s.regime === "COMPOUNDER");
      case "reversals":
        return filteredStocks.filter((s) => s.regime === "REVERSAL");
      default:
        return filteredStocks;
    }
  }, [filteredStocks, activeTab]);

  const regimeCounts = useMemo(() => {
    const c = { SPRINTER: 0, COMPOUNDER: 0, REVERSAL: 0 };
    stocks.forEach((s) => {
      if (c[s.regime] !== undefined) c[s.regime]++;
    });
    return c;
  }, [stocks]);

  return (
    <div className="min-h-screen bg-[#050505] text-white">
      <Toaster theme="dark" richColors position="top-right" />
      <MacroTicker data={macro} />

      <div className="max-w-[1920px] mx-auto px-4 md:px-6 pb-16">
        {/* Header */}
        <header className="flex flex-col md:flex-row items-start md:items-center justify-between py-6 gap-4">
          <div>
            <h1 className="font-display text-3xl sm:text-4xl tracking-tighter font-black uppercase">
              NSE Quant Engine
            </h1>
            <p className="text-[#A1A1AA] text-[10px] tracking-[0.15em] uppercase mt-1">
              Autonomous Investment Intelligence
            </p>
          </div>
          <div className="flex items-center gap-3 w-full md:w-auto">
            <div className="relative flex-1 md:w-72">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#555]" />
              <Input
                data-testid="scanner-input"
                placeholder="Search ticker, name, sector..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 bg-[#0C0C0C] border-[#1F1F1F] text-white placeholder:text-[#555] rounded-none h-9 text-xs"
              />
            </div>
            <Button
              data-testid="scan-nifty50-btn"
              onClick={() => handleStartScan("nifty50")}
              disabled={scanStatus.running}
              className="bg-white text-black hover:bg-zinc-200 rounded-none h-9 font-display font-bold uppercase tracking-wider text-[10px] px-3"
            >
              {scanStatus.running ? (
                <><RefreshCw className="w-3.5 h-3.5 mr-1.5 animate-spin" /> Scanning</>
              ) : (
                <><Zap className="w-3.5 h-3.5 mr-1.5" /> Nifty 50</>
              )}
            </Button>
            <Button
              data-testid="scan-nifty100-btn"
              onClick={() => handleStartScan("nifty100")}
              disabled={scanStatus.running}
              variant="outline"
              className="bg-transparent border-[#1F1F1F] text-white hover:border-[#A1A1AA] hover:text-white rounded-none h-9 font-display font-bold uppercase tracking-wider text-[10px] px-3"
            >
              100
            </Button>
            <Button
              data-testid="scan-nifty200-btn"
              onClick={() => handleStartScan("nifty200")}
              disabled={scanStatus.running}
              variant="outline"
              className="bg-transparent border-[#1F1F1F] text-white hover:border-[#A1A1AA] hover:text-white rounded-none h-9 font-display font-bold uppercase tracking-wider text-[10px] px-3"
            >
              200+
            </Button>
            <Button
              data-testid="scan-full-btn"
              onClick={() => handleStartScan("full")}
              disabled={scanStatus.running}
              variant="outline"
              className="bg-transparent border-[#1F1F1F] text-[#FFB300] hover:border-[#FFB300] hover:text-[#FFB300] rounded-none h-9 font-display font-bold uppercase tracking-wider text-[10px] px-3"
            >
              Full Market
            </Button>
          </div>
        </header>

        {/* Scan Progress */}
        {scanStatus.running && (
          <div data-testid="scan-progress" className="mb-6 p-4 bg-[#0C0C0C] border border-[#1F1F1F] animate-fade-in">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] tracking-[0.1em] uppercase text-[#A1A1AA]">
                Scanning: <span className="text-white">{scanStatus.current_ticker}</span>
              </span>
              <span className="text-xs text-white">
                {scanStatus.progress}/{scanStatus.total}
              </span>
            </div>
            <Progress
              value={scanStatus.total > 0 ? (scanStatus.progress / scanStatus.total) * 100 : 0}
              className="h-1"
            />
          </div>
        )}

        {/* Empty State */}
        {!loading && stocks.length === 0 && !scanStatus.running && (
          <div data-testid="empty-state" className="py-20 text-center animate-fade-in">
            <div className="inline-block p-8 bg-[#0C0C0C] border border-[#1F1F1F]">
              <Zap className="w-8 h-8 text-[#A1A1AA] mx-auto mb-4" />
              <h2 className="font-display text-xl font-bold mb-2">No Data Yet</h2>
              <p className="text-xs text-[#A1A1AA] max-w-md mb-6">
                Start your first scan to analyze NSE stocks. The engine will fetch
                live data, calculate technical indicators, score fundamentals, and
                classify each stock into regimes.
              </p>
              <Button
                data-testid="empty-start-scan-btn"
                onClick={() => handleStartScan("nifty50")}
                className="bg-white text-black hover:bg-zinc-200 rounded-none font-display font-bold uppercase tracking-wider text-xs px-8 h-10"
              >
                <Zap className="w-4 h-4 mr-2" />
                Start Nifty 50 Scan
              </Button>
            </div>
          </div>
        )}

        {/* Main Content */}
        {(stocks.length > 0 || loading) && (
          <>
            {/* Grid: Confidence + Regimes */}
            <div className="grid grid-cols-12 gap-4 md:gap-6 mb-6">
              <ConfidenceWidget data={confidence} backgroundUrl={BG_URL} />
              <RegimeColumns stocks={stocks} onSelectStock={setSelectedStock} />
            </div>

            {/* Tabs & Table */}
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList className="bg-[#0C0C0C] border border-[#1F1F1F] rounded-none h-9 p-0.5 flex-wrap">
                <TabsTrigger data-testid="tab-all" value="all" className="rounded-none data-[state=active]:bg-white data-[state=active]:text-black text-[#A1A1AA] text-[10px] uppercase tracking-wider font-bold h-7 px-3">
                  All ({stocks.length})
                </TabsTrigger>
                <TabsTrigger data-testid="tab-sprinters" value="sprinters" className="rounded-none data-[state=active]:bg-[#00E676] data-[state=active]:text-black text-[#A1A1AA] text-[10px] uppercase tracking-wider font-bold h-7 px-3">
                  Sprinters ({regimeCounts.SPRINTER})
                </TabsTrigger>
                <TabsTrigger data-testid="tab-compounders" value="compounders" className="rounded-none data-[state=active]:bg-[#2979FF] data-[state=active]:text-black text-[#A1A1AA] text-[10px] uppercase tracking-wider font-bold h-7 px-3">
                  Compounders ({regimeCounts.COMPOUNDER})
                </TabsTrigger>
                <TabsTrigger data-testid="tab-reversals" value="reversals" className="rounded-none data-[state=active]:bg-[#FFB300] data-[state=active]:text-black text-[#A1A1AA] text-[10px] uppercase tracking-wider font-bold h-7 px-3">
                  Reversals ({regimeCounts.REVERSAL})
                </TabsTrigger>
                <TabsTrigger data-testid="tab-sectors" value="sectors" className="rounded-none data-[state=active]:bg-white data-[state=active]:text-black text-[#A1A1AA] text-[10px] uppercase tracking-wider font-bold h-7 px-3">
                  Sectors ({sectors.length})
                </TabsTrigger>
                <TabsTrigger data-testid="tab-watchlist" value="watchlist" className="rounded-none data-[state=active]:bg-white data-[state=active]:text-black text-[#A1A1AA] text-[10px] uppercase tracking-wider font-bold h-7 px-3">
                  Watchlist ({watchlist.length})
                </TabsTrigger>
                <TabsTrigger data-testid="tab-portfolio" value="portfolio" className="rounded-none data-[state=active]:bg-white data-[state=active]:text-black text-[#A1A1AA] text-[10px] uppercase tracking-wider font-bold h-7 px-3">
                  Portfolio ({portfolio.items?.length || 0})
                </TabsTrigger>
                <TabsTrigger data-testid="tab-alerts" value="alerts" className="rounded-none data-[state=active]:bg-white data-[state=active]:text-black text-[#A1A1AA] text-[10px] uppercase tracking-wider font-bold h-7 px-3">
                  Alerts
                </TabsTrigger>
              </TabsList>

              {/* Stock tabs */}
              {["all", "sprinters", "compounders", "reversals"].map((tab) => (
                <TabsContent key={tab} value={tab} className="mt-0">
                  <StockTable
                    stocks={tabStocks}
                    onSelectStock={setSelectedStock}
                    onAddToWatchlist={handleAddToWatchlist}
                    watchlistTickers={watchlistTickers}
                  />
                </TabsContent>
              ))}

              {/* Watchlist Tab */}
              <TabsContent value="watchlist" className="mt-4">

              {/* Sectors Tab */}
              </TabsContent>
              <TabsContent value="sectors" className="mt-4">
                {sectors.length === 0 ? (
                  <p className="text-center text-[#555] text-xs py-12">No sector data. Run a scan first.</p>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    {sectors.map((sec) => (
                      <div key={sec.sector} data-testid={`sector-card-${sec.sector}`} className="bg-[#0C0C0C] border border-[#1F1F1F] p-4">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs text-white font-medium">{sec.sector}</span>
                          <span className={`text-xs font-bold ${sec.avg_change >= 0 ? "text-[#00E676]" : "text-[#FF3D00]"}`}>
                            {sec.avg_change >= 0 ? "+" : ""}{sec.avg_change}%
                          </span>
                        </div>
                        <div className="w-full h-1.5 bg-[#1F1F1F] mb-3">
                          <div
                            className="h-full"
                            style={{
                              width: `${Math.min(Math.abs(sec.avg_change) * 10, 100)}%`,
                              backgroundColor: sec.avg_change >= 0 ? "#00E676" : "#FF3D00",
                            }}
                          />
                        </div>
                        <div className="grid grid-cols-4 gap-2 text-[10px]">
                          <div><span className="text-[#555]">Stocks</span><p className="text-white">{sec.count}</p></div>
                          <div><span className="text-[#555]">Quality</span><p className="text-white">{sec.avg_quality}</p></div>
                          <div><span className="text-[#00E676]">Sprint</span><p className="text-white">{sec.sprinters}</p></div>
                          <div><span className="text-[#2979FF]">Comp</span><p className="text-white">{sec.compounders}</p></div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </TabsContent>

              <TabsContent value="watchlist" className="mt-4">
                {watchlist.length === 0 ? (
                  <p className="text-center text-[#555] text-xs py-12">
                    Watchlist is empty. Add stocks from the scanner.
                  </p>
                ) : (
                  <Table data-testid="watchlist-table">
                    <TableHeader>
                      <TableRow className="border-b border-[#1F1F1F] hover:bg-transparent">
                        <TableHead className="text-[10px] tracking-[0.1em] uppercase text-[#A1A1AA]">Ticker</TableHead>
                        <TableHead className="text-[10px] tracking-[0.1em] uppercase text-[#A1A1AA] text-right">Price</TableHead>
                        <TableHead className="text-[10px] tracking-[0.1em] uppercase text-[#A1A1AA] text-right">Chg%</TableHead>
                        <TableHead className="text-[10px] tracking-[0.1em] uppercase text-[#A1A1AA] text-center">Regime</TableHead>
                        <TableHead className="text-[10px] tracking-[0.1em] uppercase text-[#A1A1AA] text-right">Quality</TableHead>
                        <TableHead className="text-[10px] tracking-[0.1em] uppercase text-[#A1A1AA] text-center">Tag</TableHead>
                        <TableHead className="text-[10px] tracking-[0.1em] uppercase text-[#A1A1AA] text-center"></TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {watchlist.map((w) => {
                        const sd = w.stock_data || {};
                        return (
                          <TableRow
                            key={w.ticker}
                            data-testid={`watchlist-row-${w.ticker}`}
                            className="border-b border-[#1F1F1F] hover:bg-[#111111] cursor-pointer"
                            onClick={() => sd.ticker && setSelectedStock(sd)}
                          >
                            <TableCell className="text-xs text-white font-medium">{w.ticker}</TableCell>
                            <TableCell className="text-right text-xs text-white">{formatPrice(sd.price)}</TableCell>
                            <TableCell className={`text-right text-xs ${sd.change_pct >= 0 ? "text-[#00E676]" : "text-[#FF3D00]"}`}>
                              {formatPct(sd.change_pct)}
                            </TableCell>
                            <TableCell className="text-center">
                              <span className={`regime-badge regime-${(sd.regime || "neutral").toLowerCase()}`}>{sd.regime || "-"}</span>
                            </TableCell>
                            <TableCell className="text-right text-xs text-white">{sd.quality_score ?? "-"}</TableCell>
                            <TableCell className="text-center">
                              <span className={`regime-badge gsq-${(w.tag || "stayer").toLowerCase()}`}>{w.tag}</span>
                            </TableCell>
                            <TableCell className="text-center">
                              <button
                                data-testid={`remove-watchlist-${w.ticker}`}
                                onClick={(e) => { e.stopPropagation(); handleRemoveWatchlist(w.ticker); }}
                                className="p-1 hover:bg-[#1A1A1A] text-[#555] hover:text-[#FF3D00]"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                )}
              </TabsContent>

              {/* Portfolio Tab */}
              <TabsContent value="portfolio" className="mt-4">
                {portfolio.summary && portfolio.items?.length > 0 && (
                  <div data-testid="portfolio-summary" className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                    {[
                      { label: "Invested", value: formatPrice(portfolio.summary.total_invested) },
                      { label: "Current", value: formatPrice(portfolio.summary.total_current) },
                      {
                        label: "P&L",
                        value: formatPrice(portfolio.summary.total_pnl),
                        color: portfolio.summary.total_pnl >= 0 ? "text-[#00E676]" : "text-[#FF3D00]",
                      },
                      {
                        label: "P&L %",
                        value: formatPct(portfolio.summary.total_pnl_pct),
                        color: portfolio.summary.total_pnl_pct >= 0 ? "text-[#00E676]" : "text-[#FF3D00]",
                      },
                    ].map((m) => (
                      <div key={m.label} className="bg-[#0C0C0C] border border-[#1F1F1F] p-3">
                        <p className="text-[10px] tracking-[0.1em] uppercase text-[#A1A1AA] mb-1">{m.label}</p>
                        <p className={`text-sm font-medium ${m.color || "text-white"}`}>{m.value}</p>
                      </div>
                    ))}
                  </div>
                )}
                {(!portfolio.items || portfolio.items.length === 0) ? (
                  <p className="text-center text-[#555] text-xs py-12">
                    Portfolio is empty. Add stocks from the deep dive panel.
                  </p>
                ) : (
                  <Table data-testid="portfolio-table">
                    <TableHeader>
                      <TableRow className="border-b border-[#1F1F1F] hover:bg-transparent">
                        <TableHead className="text-[10px] tracking-[0.1em] uppercase text-[#A1A1AA]">Ticker</TableHead>
                        <TableHead className="text-[10px] tracking-[0.1em] uppercase text-[#A1A1AA] text-right">Buy Price</TableHead>
                        <TableHead className="text-[10px] tracking-[0.1em] uppercase text-[#A1A1AA] text-right">Current</TableHead>
                        <TableHead className="text-[10px] tracking-[0.1em] uppercase text-[#A1A1AA] text-right">Qty</TableHead>
                        <TableHead className="text-[10px] tracking-[0.1em] uppercase text-[#A1A1AA] text-right">P&L %</TableHead>
                        <TableHead className="text-[10px] tracking-[0.1em] uppercase text-[#A1A1AA] text-center">Tag</TableHead>
                        <TableHead className="text-[10px] tracking-[0.1em] uppercase text-[#A1A1AA] text-center"></TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {portfolio.items.map((p) => (
                        <TableRow
                          key={p.ticker}
                          data-testid={`portfolio-row-${p.ticker}`}
                          className="border-b border-[#1F1F1F] hover:bg-[#111111] cursor-pointer"
                          onClick={() => p.stock_data && setSelectedStock(p.stock_data)}
                        >
                          <TableCell className="text-xs text-white font-medium">{p.ticker}</TableCell>
                          <TableCell className="text-right text-xs text-[#A1A1AA]">{formatPrice(p.buy_price)}</TableCell>
                          <TableCell className="text-right text-xs text-white">{formatPrice(p.current_price)}</TableCell>
                          <TableCell className="text-right text-xs text-[#A1A1AA]">{p.quantity}</TableCell>
                          <TableCell className={`text-right text-xs font-medium ${p.pnl_pct >= 0 ? "text-[#00E676]" : "text-[#FF3D00]"}`}>
                            {formatPct(p.pnl_pct)}
                          </TableCell>
                          <TableCell className="text-center">
                            <span className={`regime-badge gsq-${(p.tag || "stayer").toLowerCase()}`}>{p.tag}</span>
                          </TableCell>
                          <TableCell className="text-center">
                            <button
                              data-testid={`remove-portfolio-${p.ticker}`}
                              onClick={(e) => { e.stopPropagation(); handleRemovePortfolio(p.ticker); }}
                              className="p-1 hover:bg-[#1A1A1A] text-[#555] hover:text-[#FF3D00]"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </TabsContent>

              {/* Alerts Tab */}
              <TabsContent value="alerts" className="mt-4">
                <div className="space-y-4">
                  <div className="bg-[#0C0C0C] border border-[#1F1F1F] p-4">
                    <p className="text-[10px] tracking-[0.15em] uppercase font-bold text-[#A1A1AA] mb-3">
                      Email Alerts Configuration
                    </p>
                    <div className="flex items-center gap-3 text-xs">
                      <span className="text-[#A1A1AA]">Alerts will be sent to:</span>
                      <span className="text-white font-medium">gauravmusale.gm.18@gmail.com</span>
                    </div>
                    <p className="text-[10px] text-[#555] mt-2">
                      Add your Resend API key in backend .env to activate email alerts for regime changes.
                    </p>
                  </div>
                  <div>
                    <p className="text-[10px] tracking-[0.15em] uppercase font-bold text-[#A1A1AA] mb-3">
                      Recent Regime Changes ({regimeChanges.length})
                    </p>
                    {regimeChanges.length === 0 ? (
                      <p className="text-center text-[#555] text-xs py-8">No regime changes detected yet. Run a scan to track changes.</p>
                    ) : (
                      <div className="space-y-2">
                        {regimeChanges.map((rc, i) => (
                          <div key={i} data-testid={`regime-change-${i}`} className="bg-[#0C0C0C] border border-[#1F1F1F] p-3 flex items-center justify-between">
                            <div>
                              <span className="text-xs text-white font-medium">{rc.ticker}</span>
                              <span className="text-[10px] text-[#555] ml-2">{rc.name}</span>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className={`regime-badge regime-${(rc.old_regime || "").toLowerCase()}`}>{rc.old_regime}</span>
                              <span className="text-[#555] text-xs">&rarr;</span>
                              <span className={`regime-badge regime-${(rc.new_regime || "").toLowerCase()}`}>{rc.new_regime}</span>
                              <span className="text-[9px] text-[#555] ml-2">{rc.timestamp?.slice(0, 16)}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </TabsContent>
            </Tabs>
          </>
        )}
      </div>

      <DeepDiveSheet
        stock={selectedStock}
        onClose={() => setSelectedStock(null)}
        onAddToWatchlist={handleAddToWatchlist}
        onAddToPortfolio={handleAddToPortfolio}
      />
    </div>
  );
}
