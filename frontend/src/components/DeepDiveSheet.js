import { useState, useEffect } from "react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { api } from "@/lib/api";
import { formatPrice, formatPct, formatMarketCap, formatNum } from "@/lib/format";
import { X, BookmarkPlus, Briefcase } from "lucide-react";

const REGIME_COLORS = {
  SPRINTER: "#00E676",
  COMPOUNDER: "#2979FF",
  REVERSAL: "#FFB300",
  NEUTRAL: "#A1A1AA",
  AVOID: "#FF3D00",
};

function MetricRow({ label, value, color }) {
  return (
    <div className="flex items-center justify-between py-1.5">
      <span className="text-[10px] tracking-[0.1em] uppercase text-[#A1A1AA]">
        {label}
      </span>
      <span className={`text-xs font-medium ${color || "text-white"}`}>
        {value}
      </span>
    </div>
  );
}

function QualityBar({ score }) {
  const color =
    score >= 70 ? "#00E676" : score >= 50 ? "#FFB300" : "#FF3D00";
  return (
    <div className="mt-1">
      <div className="flex items-center justify-between mb-1">
        <span className="text-[10px] tracking-[0.1em] uppercase text-[#A1A1AA]">
          Quality Score
        </span>
        <span className="text-lg font-display font-black" style={{ color }}>
          {score}
        </span>
      </div>
      <div className="w-full h-1.5 bg-[#1F1F1F]">
        <div
          className="h-full transition-all duration-500"
          style={{ width: `${score}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

export default function DeepDiveSheet({
  stock,
  onClose,
  onAddToWatchlist,
  onAddToPortfolio,
}) {
  const [history, setHistory] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [news, setNews] = useState(null);
  const [loadingNews, setLoadingNews] = useState(false);
  const [showPortfolioForm, setShowPortfolioForm] = useState(false);
  const [buyPrice, setBuyPrice] = useState("");
  const [quantity, setQuantity] = useState("1");

  useEffect(() => {
    if (stock?.ticker) {
      setLoadingHistory(true);
      setShowPortfolioForm(false);
      setNews(null);
      api
        .getStockHistory(stock.ticker)
        .then((res) => setHistory(res.data || []))
        .catch(() => setHistory([]))
        .finally(() => setLoadingHistory(false));
      setLoadingNews(true);
      api
        .getStockNews(stock.ticker)
        .then((res) => setNews(res.data))
        .catch(() => setNews(null))
        .finally(() => setLoadingNews(false));
    }
  }, [stock?.ticker]);

  const s = stock;
  if (!s) return null;

  const regimeColor = REGIME_COLORS[s.regime] || "#A1A1AA";

  const handleAddPortfolio = () => {
    if (onAddToPortfolio && buyPrice) {
      onAddToPortfolio({
        ticker: s.ticker,
        buy_price: parseFloat(buyPrice),
        quantity: parseInt(quantity) || 1,
        tag: s.gsq_tag || "STAYER",
      });
      setShowPortfolioForm(false);
      setBuyPrice("");
      setQuantity("1");
    }
  };

  return (
    <Sheet open={!!stock} onOpenChange={() => onClose()}>
      <SheetContent
        side="right"
        className="w-[92vw] md:w-[42vw] bg-[#0A0A0A] border-l border-[#1F1F1F] p-0"
      >
        <div className="h-full flex flex-col">
          <SheetHeader className="p-6 pb-4 border-b border-[#1F1F1F]">
            <div className="flex items-start justify-between">
              <div>
                <SheetTitle className="text-white font-display text-2xl font-black tracking-tight">
                  {s.ticker}
                </SheetTitle>
                <p className="text-xs text-[#A1A1AA] mt-0.5">{s.name}</p>
                <p className="text-[10px] text-[#555] mt-0.5">
                  {s.sector} / {s.industry}
                </p>
              </div>
              <button
                data-testid="deep-dive-close"
                onClick={onClose}
                className="p-1 hover:bg-[#1A1A1A] text-[#A1A1AA] hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="flex items-end gap-3 mt-3">
              <span className="text-3xl font-display font-black text-white tracking-tighter">
                {formatPrice(s.price)}
              </span>
              <span
                className={`text-sm font-medium mb-0.5 ${
                  s.change_pct >= 0 ? "text-[#00E676]" : "text-[#FF3D00]"
                }`}
              >
                {formatPct(s.change_pct)}
              </span>
            </div>
            <div className="flex gap-2 mt-3">
              <span
                className="regime-badge"
                style={{
                  color: regimeColor,
                  borderColor: `${regimeColor}40`,
                  backgroundColor: `${regimeColor}15`,
                }}
              >
                {s.regime}
              </span>
              {s.target_pct > 0 && (
                <span className="regime-badge text-[#A1A1AA] border-[#A1A1AA]/30 bg-[#A1A1AA]/10">
                  TARGET {s.target_pct}%
                </span>
              )}
            </div>
          </SheetHeader>

          <ScrollArea className="flex-1 px-6">
            <div className="py-4 space-y-5">
              {/* Chart */}
              <div>
                <p className="text-[10px] tracking-[0.15em] uppercase font-bold text-[#A1A1AA] mb-2">
                  Price History (6M)
                </p>
                {loadingHistory ? (
                  <div className="h-[160px] bg-[#0C0C0C] border border-[#1F1F1F] flex items-center justify-center">
                    <span className="text-[10px] text-[#555]">
                      Loading chart...
                    </span>
                  </div>
                ) : history.length > 0 ? (
                  <div className="h-[160px] bg-[#0C0C0C] border border-[#1F1F1F] p-2">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={history}>
                        <XAxis dataKey="date" hide />
                        <YAxis hide domain={["auto", "auto"]} />
                        <Tooltip
                          contentStyle={{
                            background: "#0C0C0C",
                            border: "1px solid #1F1F1F",
                            borderRadius: 0,
                            fontSize: 11,
                          }}
                          labelStyle={{ color: "#A1A1AA" }}
                          itemStyle={{ color: "#fff" }}
                        />
                        <Line
                          type="monotone"
                          dataKey="close"
                          stroke={regimeColor}
                          strokeWidth={1.5}
                          dot={false}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <div className="h-[80px] bg-[#0C0C0C] border border-[#1F1F1F] flex items-center justify-center">
                    <span className="text-[10px] text-[#555]">
                      No chart data
                    </span>
                  </div>
                )}
              </div>

              {/* Quality */}
              <QualityBar score={s.quality_score} />

              <Separator className="bg-[#1F1F1F]" />

              {/* Fundamentals */}
              <div>
                <p className="text-[10px] tracking-[0.15em] uppercase font-bold text-[#A1A1AA] mb-2">
                  Fundamentals
                </p>
                <MetricRow label="Market Cap" value={formatMarketCap(s.market_cap)} />
                <MetricRow label="P/E Ratio" value={formatNum(s.pe_ratio)} />
                <MetricRow label="P/B Ratio" value={formatNum(s.pb_ratio)} />
                <MetricRow label="PEG Ratio" value={formatNum(s.peg_ratio)} />
                <MetricRow
                  label="ROE"
                  value={`${formatNum(s.roe)}%`}
                  color={s.roe > 15 ? "text-[#00E676]" : s.roe > 10 ? "text-[#FFB300]" : "text-[#FF3D00]"}
                />
                <MetricRow
                  label="Debt/Equity"
                  value={formatNum(s.de_ratio)}
                  color={s.de_ratio < 0.5 ? "text-[#00E676]" : s.de_ratio < 1 ? "text-[#FFB300]" : "text-[#FF3D00]"}
                />
                <MetricRow label="Profit Margin" value={`${formatNum(s.profit_margin)}%`} />
                <MetricRow label="Earnings Growth" value={`${formatNum(s.earnings_growth)}%`} />
                <MetricRow label="Revenue Growth" value={`${formatNum(s.revenue_growth)}%`} />
                <MetricRow label="Dividend Yield" value={`${formatNum(s.dividend_yield)}%`} />
              </div>

              <Separator className="bg-[#1F1F1F]" />

              {/* Technicals */}
              <div>
                <p className="text-[10px] tracking-[0.15em] uppercase font-bold text-[#A1A1AA] mb-2">
                  Technicals
                </p>
                <MetricRow label="RSI (14)" value={formatNum(s.rsi)} />
                <MetricRow label="SMA 50" value={formatPrice(s.sma50)} />
                <MetricRow label="SMA 200" value={formatPrice(s.sma200)} />
                <MetricRow label="ATR (14)" value={`${formatNum(s.atr)} (${formatNum(s.atr_pct)}%)`} />
                <MetricRow label="Volume Ratio" value={`${formatNum(s.volume_ratio)}x`} />
                <MetricRow label="52W High" value={formatPrice(s.week52_high)} />
                <MetricRow label="52W Low" value={formatPrice(s.week52_low)} />
              </div>

              {/* Trade Types */}
              {s.trade_types?.length > 0 && (
                <div>
                  <p className="text-[10px] tracking-[0.15em] uppercase font-bold text-[#A1A1AA] mb-2">
                    Recommended Action
                  </p>
                  <div className="flex gap-2 flex-wrap">
                    {s.trade_types.map((t) => (
                      <span key={t} className={`regime-badge trade-${t.toLowerCase()} px-3 py-1`}>
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              <Separator className="bg-[#1F1F1F]" />

              {/* News Sentiment */}
              <div>
                <p className="text-[10px] tracking-[0.15em] uppercase font-bold text-[#A1A1AA] mb-2">
                  News Sentiment
                </p>
                {loadingNews ? (
                  <div className="h-[50px] bg-[#0C0C0C] border border-[#1F1F1F] flex items-center justify-center">
                    <span className="text-[10px] text-[#555]">Analyzing news...</span>
                  </div>
                ) : news?.articles?.length > 0 ? (
                  <div className="space-y-2">
                    {news.overall && (
                      <div
                        data-testid="news-sentiment-badge"
                        className={`inline-flex items-center gap-2 px-2 py-1 border text-[10px] uppercase font-bold ${
                          news.overall.sentiment === "BULLISH"
                            ? "text-[#00E676] border-[#00E676]/30 bg-[#00E676]/10"
                            : news.overall.sentiment === "BEARISH"
                            ? "text-[#FF3D00] border-[#FF3D00]/30 bg-[#FF3D00]/10"
                            : "text-[#A1A1AA] border-[#A1A1AA]/30 bg-[#A1A1AA]/10"
                        }`}
                      >
                        {news.overall.sentiment} ({news.overall.score}/100)
                      </div>
                    )}
                    {news.articles.slice(0, 5).map((a, i) => (
                      <a
                        key={i}
                        href={a.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        data-testid={`news-article-${i}`}
                        className="block p-2 bg-[#0C0C0C] border border-[#1F1F1F] hover:bg-[#111] transition-colors"
                      >
                        <p className="text-[11px] text-white leading-tight">{a.title}</p>
                        <p className="text-[9px] text-[#555] mt-1">{a.source}</p>
                      </a>
                    ))}
                  </div>
                ) : (
                  <p className="text-[10px] text-[#555]">No recent news found</p>
                )}
              </div>

              <Separator className="bg-[#1F1F1F]" />

              {/* Actions */}
              <div className="flex gap-2">
                <Button
                  data-testid="add-to-watchlist-btn"
                  onClick={() => onAddToWatchlist(s.ticker)}
                  className="flex-1 bg-transparent border border-[#1F1F1F] text-white hover:border-[#A1A1AA] rounded-none text-xs uppercase tracking-wider font-bold h-9"
                >
                  <BookmarkPlus className="w-3.5 h-3.5 mr-2" />
                  Watchlist
                </Button>
                <Button
                  data-testid="add-to-portfolio-btn"
                  onClick={() => setShowPortfolioForm(!showPortfolioForm)}
                  className="flex-1 bg-white text-black hover:bg-zinc-200 rounded-none text-xs uppercase tracking-wider font-bold h-9"
                >
                  <Briefcase className="w-3.5 h-3.5 mr-2" />
                  Portfolio
                </Button>
              </div>

              {showPortfolioForm && (
                <div className="p-3 bg-[#0C0C0C] border border-[#1F1F1F] space-y-2 animate-fade-in">
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="text-[10px] text-[#A1A1AA] uppercase tracking-wider">
                        Buy Price
                      </label>
                      <Input
                        data-testid="portfolio-buy-price"
                        type="number"
                        value={buyPrice}
                        onChange={(e) => setBuyPrice(e.target.value)}
                        placeholder={s.price?.toString()}
                        className="bg-[#050505] border-[#1F1F1F] text-white text-xs h-8 rounded-none"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] text-[#A1A1AA] uppercase tracking-wider">
                        Quantity
                      </label>
                      <Input
                        data-testid="portfolio-quantity"
                        type="number"
                        value={quantity}
                        onChange={(e) => setQuantity(e.target.value)}
                        className="bg-[#050505] border-[#1F1F1F] text-white text-xs h-8 rounded-none"
                      />
                    </div>
                  </div>
                  <Button
                    data-testid="confirm-add-portfolio"
                    onClick={handleAddPortfolio}
                    disabled={!buyPrice}
                    className="w-full bg-white text-black hover:bg-zinc-200 rounded-none text-xs uppercase h-8"
                  >
                    Confirm Add
                  </Button>
                </div>
              )}

              <div className="h-8" />
            </div>
          </ScrollArea>
        </div>
      </SheetContent>
    </Sheet>
  );
}
