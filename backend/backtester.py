import os
import json
import logging
from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
import yfinance as yf

from analysis_engine import _classify_swing, _classify_long_term

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(__file__), "backtest_data")
os.makedirs(DATA_DIR, exist_ok=True)

BACKTEST_UNIVERSE = {
    'IT': ['TCS.NS', 'INFY.NS', 'WIPRO.NS'],
    'Banking': ['HDFCBANK.NS', 'ICICIBANK.NS', 'SBIN.NS'],
    'Auto': ['MARUTI.NS', 'M&M.NS', 'TATAMOTORS.NS'],
    'Pharma': ['SUNPHARMA.NS', 'DRREDDY.NS'],
    'FMCG': ['HINDUNILVR.NS', 'ITC.NS', 'NESTLEIND.NS'],
    'Energy': ['RELIANCE.NS', 'ONGC.NS'],
    'Metals': ['TATASTEEL.NS', 'HINDALCO.NS'],
    'Infra': ['LT.NS', 'ULTRACEMCO.NS']
}

WEIGHT_SEARCH_SPACE = [
    {'trend': 0.50, 'momentum': 0.30, 'volatility': 0.20},  # Baseline
    {'trend': 0.60, 'momentum': 0.25, 'volatility': 0.15},  # Trend-heavy
    {'trend': 0.40, 'momentum': 0.40, 'volatility': 0.20},  # Momentum-heavy
    {'trend': 0.45, 'momentum': 0.30, 'volatility': 0.25},  # Volatility-aware
    {'trend': 0.33, 'momentum': 0.33, 'volatility': 0.34},  # Equal weight
]

# ── Data Fetching & Caching ───────────────────────────────────────
def get_historical_data(ticker: str, start_date: str, end_date: str, force_refresh: bool = False) -> pd.DataFrame:
    """Fetch from yfinance, cache locally as parquet to avoid API limits."""
    file_path = os.path.join(DATA_DIR, f"{ticker}.parquet")
    meta_path = os.path.join(DATA_DIR, "metadata.json")
    
    meta = {}
    if os.path.exists(meta_path):
        with open(meta_path, "r") as f:
            meta = json.load(f)
            
    # Check cache validity (7 days)
    last_updated = meta.get(ticker, "2000-01-01")
    days_old = (datetime.now() - datetime.fromisoformat(last_updated)).days
    
    if os.path.exists(file_path) and not force_refresh and days_old < 7:
        df = pd.read_parquet(file_path)
        # Filter dates
        if not df.empty:
            df = df[(df.index >= pd.to_datetime(start_date).tz_localize(df.index.tz)) & 
                    (df.index <= pd.to_datetime(end_date).tz_localize(df.index.tz))]
            return df
            
    logger.info(f"Downloading data for {ticker}...")
    stock = yf.Ticker(ticker)
    df = stock.history(start=start_date, end=datetime.now().strftime("%Y-%m-%d"))
    if df.empty:
        return df
        
    df.to_parquet(file_path)
    meta[ticker] = datetime.now().isoformat()
    with open(meta_path, "w") as f:
        json.dump(meta, f)
        
    df = df[(df.index >= pd.to_datetime(start_date).tz_localize(df.index.tz)) & 
            (df.index <= pd.to_datetime(end_date).tz_localize(df.index.tz))]
    return df

# ── Indicator Calculation ─────────────────────────────────────────
def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Vectorized calculation of indicators to match analysis_engine."""
    df = df.copy()
    if len(df) < 200:
        return pd.DataFrame()
        
    df['SMA50'] = df['Close'].rolling(50).mean()
    df['SMA200'] = df['Close'].rolling(200).mean()
    df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
    
    # RSI
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    df['RSI'] = df['RSI'].fillna(50)
    
    # MACD
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    df['MACD_HIST'] = macd - macd_signal
    
    # Bollinger Bands
    df['BB_MID'] = df['Close'].rolling(20).mean()
    std = df['Close'].rolling(20).std()
    df['BB_UPPER'] = df['BB_MID'] + 2 * std
    df['BB_LOWER'] = df['BB_MID'] - 2 * std
    
    # ATR & ADX
    tr = np.maximum((df['High'] - df['Low']), 
         np.maximum(abs(df['High'] - df['Close'].shift(1)), 
                    abs(df['Low'] - df['Close'].shift(1))))
    atr = pd.Series(tr).rolling(14).mean()
    
    up = df['High'] - df['High'].shift(1)
    dn = df['Low'].shift(1) - df['Low']
    pos_dm = np.where((up > dn) & (up > 0), up, 0.0)
    neg_dm = np.where((dn > up) & (dn > 0), dn, 0.0)
    pos_dm_roll = pd.Series(pos_dm, index=df.index).rolling(14).mean()
    neg_dm_roll = pd.Series(neg_dm, index=df.index).rolling(14).mean()
    
    pdi = 100 * (pos_dm_roll / atr)
    mdi = 100 * (neg_dm_roll / atr)
    dx = (abs(pdi - mdi) / (pdi + mdi)) * 100
    df['ADX'] = dx.rolling(14).mean().fillna(20)
    
    return df.dropna()

# ── Simulation Engine ─────────────────────────────────────────────
class BacktestEngine:
    def __init__(self, initial_capital=1000000, risk_per_trade_pct=0.02, 
                 transaction_cost_pct=0.01, check_intraday_stops=True):
        self.initial_capital = initial_capital
        self.risk_per_trade_pct = risk_per_trade_pct
        self.tc_pct = transaction_cost_pct  # 1% round trip
        self.check_intraday_stops = check_intraday_stops
        
    def _calc_metrics(self, trades, daily_portfolio_value, benchmark_returns):
        if not trades:
            return {}
            
        df_trades = pd.DataFrame(trades)
        wins = df_trades[df_trades['pnl'] > 0]
        losses = df_trades[df_trades['pnl'] <= 0]
        
        win_rate = len(wins) / len(df_trades)
        avg_win = wins['pnl'].mean() if not wins.empty else 0
        avg_loss = abs(losses['pnl'].mean()) if not losses.empty else 0
        
        expectancy = (avg_win * win_rate) - (avg_loss * (1 - win_rate))
        profit_factor = wins['pnl'].sum() / abs(losses['pnl'].sum()) if abs(losses['pnl'].sum()) > 0 else float('inf')
        
        # Portfolio series metrics
        returns = pd.Series(daily_portfolio_value).pct_change().dropna()
        total_return = (daily_portfolio_value[-1] - self.initial_capital) / self.initial_capital
        
        annual_factor = 252
        ann_ret = returns.mean() * annual_factor
        ann_vol = returns.std() * np.sqrt(annual_factor)
        
        sharpe = ann_ret / ann_vol if ann_vol > 0 else 0
        
        downside_returns = returns[returns < 0]
        downside_vol = downside_returns.std() * np.sqrt(annual_factor)
        sortino = ann_ret / downside_vol if downside_vol > 0 else 0
        
        cum_ret = (1 + returns).cumprod()
        running_max = cum_ret.cummax()
        drawdowns = (cum_ret - running_max) / running_max
        max_dd = abs(drawdowns.min()) if not drawdowns.empty else 0
        
        calmar = ann_ret / max_dd if max_dd > 0 else 0
        
        # Benchmark
        bm_total = (benchmark_returns[-1] - benchmark_returns[0]) / benchmark_returns[0] if benchmark_returns else 0
        
        return {
            'total_return_pct': round(total_return * 100, 2),
            'benchmark_return_pct': round(bm_total * 100, 2),
            'win_rate': round(win_rate, 2),
            'sharpe': round(sharpe, 2),
            'sortino': round(sortino, 2),
            'calmar': round(calmar, 2),
            'expectancy': round(expectancy, 2),
            'profit_factor': round(profit_factor, 2),
            'max_drawdown_pct': round(max_dd * 100, 2),
            'trades_count': len(trades)
        }

    def run(self, data_dict: dict, weights: dict, start_date: str, end_date: str):
        capital = self.initial_capital
        positions = {}  # ticker -> {buy_price, quantity, sl, target}
        trades = []
        
        # Extract common sorted dates
        all_dates = set()
        for df in data_dict.values():
            filtered = df[(df.index >= pd.to_datetime(start_date).tz_localize(df.index.tz)) & 
                          (df.index <= pd.to_datetime(end_date).tz_localize(df.index.tz))]
            all_dates.update(filtered.index)
        dates = sorted(list(all_dates))
        
        daily_pv = []
        benchmark_close = []
        
        for current_date in dates:
            current_pv = capital
            daily_bm_val = 0
            
            # Process Exits
            for ticker in list(positions.keys()):
                df = data_dict.get(ticker)
                if df is None or current_date not in df.index:
                    current_pv += positions[ticker]['quantity'] * positions[ticker]['buy_price']
                    continue
                    
                row = df.loc[current_date]
                pos = positions[ticker]
                
                # Check stops / targets
                exit_price = None
                reason = ""
                
                if self.check_intraday_stops:
                    # Realistic intraday stop/target check
                    if row['Low'] <= pos['sl']:
                        exit_price = min(row['Open'], pos['sl']) # Gap down handling
                        reason = "STOP_LOSS"
                    elif row['High'] >= pos['target']:
                        exit_price = max(row['Open'], pos['target']) # Gap up handling
                        reason = "TARGET"
                else:
                    if row['Close'] <= pos['sl']:
                        exit_price = row['Close']
                        reason = "STOP_LOSS"
                    elif row['Close'] >= pos['target']:
                        exit_price = row['Close']
                        reason = "TARGET"
                
                # Exit if trailing regime breaks (e.g. falls out of swing)
                if not exit_price:
                    regime = _classify_swing(row['Close'], row['SMA50'], row['SMA200'], 
                                             row['EMA20'], row['EMA50'], row['RSI'], 
                                             row['MACD_HIST'], row['ADX'], 
                                             row['BB_UPPER'], row['BB_LOWER'], weights)
                    if regime in ("SWING_SHORT", "AVOID", "NEUTRAL", "NO_TRADE", "RANGE_BOUND"):
                        exit_price = row['Close']
                        reason = "REGIME_EXIT"
                        
                if exit_price:
                    # Sell!
                    revenue = (exit_price * pos['quantity']) * (1 - self.tc_pct/2) # half TC on exit
                    capital += revenue
                    pnl = revenue - (pos['buy_price'] * pos['quantity'])
                    trades.append({
                        'ticker': ticker, 'entry_date': pos['entry_date'], 'exit_date': current_date,
                        'buy_price': pos['buy_price'], 'exit_price': exit_price,
                        'pnl': pnl, 'reason': reason
                    })
                    del positions[ticker]
                else:
                    current_pv += row['Close'] * pos['quantity']
                    
            # Process Entries
            for ticker, df in data_dict.items():
                if current_date not in df.index:
                    continue
                    
                row = df.loc[current_date]
                daily_bm_val += row['Close']
                
                if ticker in positions:
                    continue
                
                regime = _classify_swing(row['Close'], row['SMA50'], row['SMA200'], 
                                         row['EMA20'], row['EMA50'], row['RSI'], 
                                         row['MACD_HIST'], row['ADX'], 
                                         row['BB_UPPER'], row['BB_LOWER'], weights)
                                         
                if regime in ("BREAKOUT_LONG", "EMA_TREND_LONG", "MEAN_REVERSION_LONG"):
                    # Enter trade using Fixed Risk
                    sl_pct = 0.05 # 5% stop loss
                    target_pct = 0.10 # 10% target
                    
                    sl_price = row['Close'] * (1 - sl_pct)
                    target_price = row['Close'] * (1 + target_pct)
                    max_loss_per_share = row['Close'] - sl_price
                    
                    risk_amt = capital * self.risk_per_trade_pct
                    qty = int(risk_amt / max_loss_per_share)
                    cost = (qty * row['Close']) * (1 + self.tc_pct/2) # half TC on entry
                    
                    if cost < capital and qty > 0:
                        capital -= cost
                        positions[ticker] = {
                            'buy_price': row['Close'],
                            'quantity': qty,
                            'sl': sl_price,
                            'target': target_price,
                            'entry_date': current_date
                        }
            
            daily_pv.append(current_pv)
            benchmark_close.append(daily_bm_val)
            
        # Close remaining positions at end
        if dates:
            for ticker, pos in list(positions.items()):
                df = data_dict.get(ticker)
                # Ensure we have data for the last date
                if dates[-1] in df.index:
                    last_row = df.loc[dates[-1]]
                else:
                    last_row = df.iloc[-1]
                revenue = (last_row['Close'] * pos['quantity']) * (1 - self.tc_pct/2)
                capital += revenue
                trades.append({
                    'ticker': ticker, 'entry_date': pos['entry_date'], 'exit_date': dates[-1],
                    'buy_price': pos['buy_price'], 'exit_price': last_row['Close'],
                    'pnl': revenue - (pos['buy_price'] * pos['quantity']), 'reason': 'EOD'
                })
            
        metrics = self._calc_metrics(trades, daily_pv, benchmark_close)
        return metrics

# ── Rolling Window Validation ─────────────────────────────────────
def run_rolling_windows():
    windows = [
        {"train": ("2020-01-01", "2021-12-31"), "test": ("2022-01-01", "2022-12-31"), "name": "2022 Bear"},
        {"train": ("2020-01-01", "2022-12-31"), "test": ("2023-01-01", "2023-12-31"), "name": "2023 Bull"},
        {"train": ("2020-01-01", "2023-12-31"), "test": ("2024-01-01", "2024-12-31"), "name": "2024 Correct"}
    ]
    
    # 1. Download/Load Data for the whole period to save time
    tickers = [t for sec in BACKTEST_UNIVERSE.values() for t in sec]
    data_cache = {}
    for t in tickers:
        df = get_historical_data(t, "2019-01-01", "2024-12-31") # Start 2019 for 200dma
        if not df.empty:
            data_cache[t] = add_indicators(df)
            
    engine = BacktestEngine(check_intraday_stops=True)
    results = []
    
    for win in windows:
        logger.info(f"\n{'='*40}")
        logger.info(f"--- Running Window: {win['name']} ---")
        logger.info(f"{'='*40}")
        best_sharpe = -999
        best_weights = None
        
        # Training / Grid Search
        logger.info(f"Optimizing on In-Sample: {win['train']}")
        for w in WEIGHT_SEARCH_SPACE:
            metrics = engine.run(data_cache, w, win['train'][0], win['train'][1])
            sharpe = metrics.get('sharpe', -999)
            if sharpe > best_sharpe:
                best_sharpe = sharpe
                best_weights = w
                
        logger.info(f"-> Best In-Sample Weights: {best_weights} (Sharpe: {best_sharpe})")
        
        # Testing (Out of Sample)
        logger.info(f"\nTesting on Out-of-Sample: {win['test']}")
        oos_metrics = engine.run(data_cache, best_weights, win['test'][0], win['test'][1])
        
        results.append({
            'window': win['name'],
            'weights': best_weights,
            'is_sharpe': best_sharpe,
            'oos_metrics': oos_metrics
        })
        
        logger.info(f"-> OOS Results:")
        logger.info(f"   Sharpe: {oos_metrics.get('sharpe', 0)}")
        logger.info(f"   Return: {oos_metrics.get('total_return_pct', 0)}%")
        logger.info(f"   Win Rate: {oos_metrics.get('win_rate', 0)}")
        logger.info(f"   Max DD: {oos_metrics.get('max_drawdown_pct', 0)}%")
        logger.info(f"   Calmar: {oos_metrics.get('calmar', 0)}")
        logger.info(f"   Expectancy: {oos_metrics.get('expectancy', 0)}")
        logger.info(f"   Trades: {oos_metrics.get('trades_count', 0)}")
        logger.info(f"   Benchmark Return: {oos_metrics.get('benchmark_return_pct', 0)}%")
                    
    return results

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    run_rolling_windows()
