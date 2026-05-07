import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || (process.env.NODE_ENV === 'development' ? "http://127.0.0.1:8000" : "");
const API = BACKEND_URL ? `${BACKEND_URL}/api` : "/api";

export const api = {
  getMacro: () => axios.get(`${API}/market/macro`),
  getConfidence: () => axios.get(`${API}/market/confidence`),
  startScan: (universe = "nifty50", profile = "LONG_TERM") =>
    axios.post(`${API}/scan/start`, { universe, profile }),
  refreshScan: (universe = "nifty50", profile = "LONG_TERM") =>
    axios.post(`${API}/scan/refresh`, { universe, profile }),
  getScanStatus: () => axios.get(`${API}/scan/status`),
  getScanLevels: () => axios.get(`${API}/scan/levels`),
  getScanResults: (universe = "nifty50", params = {}) =>
    axios.get(`${API}/scan/results`, { params: { universe, ...params } }),

  getStocks: (params) => axios.get(`${API}/stocks`, { params }),
  searchStocks: (q) => axios.get(`${API}/stocks/search`, { params: { q } }),
  getStockDetail: (ticker) => axios.get(`${API}/stocks/${ticker}`),
  getStockHistory: (ticker, period = "6mo") =>
    axios.get(`${API}/stocks/${ticker}/history`, { params: { period } }),
  getRegimes: () => axios.get(`${API}/stocks/regimes`),

  getWatchlist: () => axios.get(`${API}/watchlist`),
  addToWatchlist: (data) => axios.post(`${API}/watchlist`, data),
  removeFromWatchlist: (ticker) => axios.delete(`${API}/watchlist/${ticker}`),
  updateWatchlistTag: (ticker, tag) =>
    axios.put(`${API}/watchlist/${ticker}/tag`, null, { params: { tag } }),

  getPortfolio: () => axios.get(`${API}/portfolio`),
  addToPortfolio: (data) => axios.post(`${API}/portfolio`, data),
  updatePortfolio: (ticker, data) => axios.put(`${API}/portfolio/${ticker}`, data),
  removeFromPortfolio: (ticker) => axios.delete(`${API}/portfolio/${ticker}`),
  getPortfolioRecommendation: (ticker) =>
    axios.get(`${API}/portfolio/${ticker}/recommendation`),

  getStockNews: (ticker, refresh = false) =>
    axios.get(`${API}/news/${ticker}`, { params: { refresh } }),
  getTickerSentiment: (ticker, refresh = false) =>
    axios.get(`${API}/sentiment/${ticker}`, { params: { refresh } }),
  getMarketSentiment: (universe = "nifty50") =>
    axios.get(`${API}/sentiment/market/${universe}`),
  refreshMarketSentiment: (universe = "nifty50", limit = 30) =>
    axios.post(`${API}/sentiment/refresh`, null, { params: { universe, limit } }),
  getFundamental: (ticker, refresh = false) =>
    axios.get(`${API}/fundamentals/${ticker}`, { params: { refresh } }),
  getFnoIndices: () => axios.get(`${API}/fno/indices`),

  getSectorHeatmap: () => axios.get(`${API}/sectors/heatmap`),
  getAlertSettings: () => axios.get(`${API}/alerts/settings`),
  updateAlertSettings: (data) => axios.post(`${API}/alerts/settings`, data),
  getRegimeChanges: (limit = 50) =>
    axios.get(`${API}/alerts/regime-changes`, { params: { limit } }),
  getAdminHealth: () => axios.get(`${API}/admin/health`),
};
