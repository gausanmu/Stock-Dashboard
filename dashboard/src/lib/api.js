import axios from "axios";

// Using Vite's proxy instead of hardcoded localhost
const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "";
const API = BACKEND_URL ? `${BACKEND_URL}/api` : "/api";

export const api = {
  getMacro: () => axios.get(`${API}/market/macro`),
  getConfidence: () => axios.get(`${API}/market/confidence`),
  
  // Scans
  startScan: (universe = "nifty50", profile = "LONG_TERM") => axios.post(`${API}/scan/start`, { universe, profile }),
  refreshScan: (universe = "nifty50", profile = "LONG_TERM") => axios.post(`${API}/scan/refresh`, { universe, profile }),
  getScanStatus: () => axios.get(`${API}/scan/status`),
  getScanLevels: () => axios.get(`${API}/scan/levels`),
  getScanResults: (universe = "nifty50", params = {}) => axios.get(`${API}/scan/results`, { params: { universe, ...params } }),

  // Stocks
  getStocks: (params) => axios.get(`${API}/stocks`, { params }),
  searchStocks: (q) => axios.get(`${API}/stocks/search`, { params: { q } }),
  getStockDetail: (ticker) => axios.get(`${API}/stocks/${ticker}`),
  getStockHistory: (ticker, period = "6mo") => axios.get(`${API}/stocks/${ticker}/history`, { params: { period } }),
  getRegimes: () => axios.get(`${API}/stocks/regimes`),

  // Watchlist
  getWatchlist: () => axios.get(`${API}/watchlist`),
  addToWatchlist: (data) => axios.post(`${API}/watchlist`, data),
  removeFromWatchlist: (ticker) => axios.delete(`${API}/watchlist/${ticker}`),
  updateWatchlistTag: (ticker, tag) => axios.put(`${API}/watchlist/${ticker}/tag`, null, { params: { tag } }),

  // Portfolio
  getPortfolio: () => axios.get(`${API}/portfolio`),
  addToPortfolio: (data) => axios.post(`${API}/portfolio`, data),
  updatePortfolio: (ticker, data) => axios.put(`${API}/portfolio/${ticker}`, data),
  removeFromPortfolio: (ticker) => axios.delete(`${API}/portfolio/${ticker}`),
  getPortfolioRecommendation: (ticker) => axios.get(`${API}/portfolio/${ticker}/recommendation`),
  getCorrelationMatrix: () => axios.get(`${API}/portfolio/correlation-matrix`),

  // Live Intraday
  getLiveMarketStatus: () => axios.get(`${API}/live/market-status`),
  getLiveQuotes: (index = "NIFTY 50") => axios.get(`${API}/live/quotes`, { params: { index } }),
  getLiveGainers: () => axios.get(`${API}/live/gainers`),
  getLiveBulls: (index = "NIFTY 50") => axios.get(`${API}/live/bulls`, { params: { index } }),
  getLiveDeepBulls: () => axios.get(`${API}/live/deep-bulls`),
  // SSE stream URLs (used with EventSource, not axios)
  getLiveScanURL: (index = "NIFTY 50") => `${API}/live/scan?index=${encodeURIComponent(index)}`,
  getLiveDeepScanURL: () => `${API}/live/deep-scan`,

  // News & Sentiment
  getStockNews: (ticker, refresh = false) => axios.get(`${API}/news/${ticker}`, { params: { refresh } }),
  getTickerSentiment: (ticker, refresh = false) => axios.get(`${API}/sentiment/${ticker}`, { params: { refresh } }),
  getMarketSentiment: (universe = "nifty50") => axios.get(`${API}/sentiment/market/${universe}`),
  refreshMarketSentiment: (universe = "nifty50", limit = 30) => axios.post(`${API}/sentiment/refresh`, null, { params: { universe, limit } }),
  
  // Fundamentals & Macro
  getFundamental: (ticker, refresh = false) => axios.get(`${API}/fundamentals/${ticker}`, { params: { refresh } }),
  getFnoIndices: () => axios.get(`${API}/fno/indices`),
  getSectorHeatmap: () => axios.get(`${API}/sectors/heatmap`),
  
  // Settings & Admin
  getAlertSettings: () => axios.get(`${API}/alerts/settings`),
  updateAlertSettings: (data) => axios.post(`${API}/alerts/settings`, data),
  getRegimeChanges: (limit = 50) => axios.get(`${API}/alerts/regime-changes`, { params: { limit } }),
  getAdminHealth: () => axios.get(`${API}/admin/health`),

  // Evening Scanner
  getEveningResults: (params = {}) => axios.get(`${API}/evening/results`, { params }),
  getEveningScanStatus: () => axios.get(`${API}/evening/status`),
  triggerEveningScan: (universe = "evening_default") => axios.post(`${API}/evening/scan`, null, { params: { universe } }),
};
