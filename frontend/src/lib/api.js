import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "http://127.0.0.1:8000";
const API = `${BACKEND_URL}/api`;

export const api = {
  getMacro: () => axios.get(`${API}/market/macro`),
  getConfidence: () => axios.get(`${API}/market/confidence`),
  startScan: (universe = "nifty50") => axios.post(`${API}/scan/start`, { universe }),
  getScanStatus: () => axios.get(`${API}/scan/status`),
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
  getStockNews: (ticker) => axios.get(`${API}/news/${ticker}`),
  getSectorHeatmap: () => axios.get(`${API}/sectors/heatmap`),
  getAlertSettings: () => axios.get(`${API}/alerts/settings`),
  updateAlertSettings: (data) => axios.post(`${API}/alerts/settings`, data),
  getRegimeChanges: (limit = 50) =>
    axios.get(`${API}/alerts/regime-changes`, { params: { limit } }),
  getScanLevels: () => axios.get(`${API}/scan/levels`),
};
