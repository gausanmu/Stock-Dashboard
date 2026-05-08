"""
Evening Scanner Backtest v2 - With Pre-Filters + Corrected Weights

Tests 1-day and 2-day hold periods (matching evening scanner's purpose).
Includes trend, liquidity, volatility, ADX pre-filters.
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import logging, time
import yfinance as yf
from evening_scanner import (
    _detect_compression_breakout, _detect_volume_accumulation,
    _detect_seller_exhaustion, _detect_breakout_retest,
    _detect_ema_power, _calculate_entry_exit, _atr, _adx, _sma,
    PATTERN_WEIGHTS, WATCH_THRESHOLD, MIN_AVG_VOLUME, MIN_ATR_PCT
)

logging.basicConfig(level=logging.WARNING)

TEST_TICKERS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
    "HINDUNILVR", "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK",
    "LT", "AXISBANK", "ASIANPAINT", "MARUTI", "TITAN",
    "SUNPHARMA", "BAJFINANCE", "HCLTECH", "WIPRO", "ULTRACEMCO",
    "NTPC", "POWERGRID", "ONGC", "COALINDIA", "ADANIENT",
    "TATASTEEL", "JSWSTEEL", "TECHM", "HINDALCO", "DRREDDY",
    "CIPLA", "EICHERMOT", "BPCL", "TATACONSUM", "GRASIM",
    "APOLLOHOSP", "HEROMOTOCO", "BAJAJ-AUTO", "BEL", "TRENT",
]

LOOKBACK = 60


def run_for_hold_period(hold_days, close_all, high_all, low_all, vol_all, dates_all, ticker):
    """Run backtest for a single ticker at a given hold period."""
    trades = []
    close, high, low, volume, dates = close_all, high_all, low_all, vol_all, dates_all

    start_idx = max(60, len(close) - LOOKBACK - hold_days - 5)
    end_idx = len(close) - hold_days

    for day_idx in range(start_idx, end_idx):
        c = close[:day_idx + 1]
        h = high[:day_idx + 1]
        l = low[:day_idx + 1]
        v = volume[:day_idx + 1]

        if len(c) < 55:
            continue

        # PRE-FILTERS (same as live scanner)
        avg_vol = sum(v[-20:]) / max(len(v[-20:]), 1)
        if avg_vol < MIN_AVG_VOLUME:
            continue

        sma50 = _sma(c, 50)
        if c[-1] < sma50:
            continue  # Trend filter

        atr_val = _atr(h, l, c)
        atr_pct = atr_val / c[-1] if c[-1] > 0 else 0
        if atr_pct < MIN_ATR_PCT:
            continue  # Volatility filter

        adx_val = _adx(h, l, c)
        if adx_val < 18:
            continue  # ADX filter

        # Run patterns
        p1, _ = _detect_compression_breakout(c, h, l, v)
        p2, _ = _detect_volume_accumulation(c, v, h, l)
        p3, _ = _detect_seller_exhaustion(c, h, l, v)
        p4, _ = _detect_breakout_retest(c, h, l)
        p5, _ = _detect_ema_power(c)

        # Weighted conviction (v2 weights)
        conviction = (
            p2 * PATTERN_WEIGHTS["volume_accumulation"]
            + p1 * PATTERN_WEIGHTS["compression_breakout"]
            + p4 * PATTERN_WEIGHTS["breakout_retest"]
            + p5 * PATTERN_WEIGHTS["ema_power"]
            + p3 * PATTERN_WEIGHTS["seller_exhaustion"]
        )

        if conviction < WATCH_THRESHOLD:
            continue

        tier = "ROCKET" if conviction >= 0.55 else "STRONG" if conviction >= 0.40 else "WATCH"

        levels = _calculate_entry_exit(c, h, l, atr_val)
        if not levels or levels["risk_reward"] < 1.5:
            continue

        entry = levels["entry"]
        sl = levels["stop_loss"]
        t1 = levels["target_1"]

        # Forward test
        won = False
        lost = False
        exit_price = None

        for fwd in range(1, hold_days + 1):
            fi = day_idx + fwd
            if fi >= len(close):
                break
            if low[fi] <= sl:
                lost = True
                exit_price = sl
                break
            if high[fi] >= t1:
                won = True
                exit_price = t1
                break

        if not won and not lost:
            exit_price = close[min(day_idx + hold_days, len(close) - 1)]
            won = exit_price > entry

        pnl_pct = ((exit_price - entry) / entry) * 100

        top_pattern = "none"
        scores = {"vol_acc": p2, "compress": p1, "retest": p4, "ema": p5, "exhaust": p3}
        top_pattern = max(scores, key=scores.get)

        trades.append({
            "ticker": ticker, "tier": tier, "conviction": round(conviction, 3),
            "pnl_pct": round(pnl_pct, 2), "won": won, "top_pattern": top_pattern,
            "date": str(dates[day_idx])[:10],
        })

    return trades


def print_results(label, all_trades):
    total = len(all_trades)
    if total == 0:
        print(f"\n  {label}: No trades generated")
        return

    wins = sum(1 for t in all_trades if t["won"])
    win_rate = wins / total * 100
    returns = [t["pnl_pct"] for t in all_trades]
    avg_ret = sum(returns) / len(returns)
    winning = [r for r in returns if r > 0]
    losing = [r for r in returns if r <= 0]
    avg_win = sum(winning) / len(winning) if winning else 0
    avg_loss = sum(losing) / len(losing) if losing else 0
    gross_profit = sum(r for r in returns if r > 0)
    gross_loss = abs(sum(r for r in returns if r < 0))
    pf = gross_profit / gross_loss if gross_loss > 0 else 999

    # Max drawdown with 1% position sizing
    equity = [0]
    for r in returns:
        equity.append(equity[-1] + r * 0.01)  # 1% risk per trade
    peak = 0
    max_dd = 0
    for e in equity:
        if e > peak: peak = e
        dd = peak - e
        if dd > max_dd: max_dd = dd

    print(f"\n  === {label} ===")
    print(f"  Trades: {total}  |  Wins: {wins}  |  Win Rate: {win_rate:.1f}%")
    print(f"  Avg Return: {avg_ret:+.2f}%  |  Avg Win: +{avg_win:.2f}%  |  Avg Loss: {avg_loss:.2f}%")
    print(f"  Profit Factor: {pf:.2f}x  |  Total: {sum(returns):+.1f}%  |  Max DD (1% size): {max_dd:.2f}%")

    # By tier
    print(f"\n  By Tier:")
    for tier_name in ["ROCKET", "STRONG", "WATCH"]:
        tt = [t for t in all_trades if t["tier"] == tier_name]
        if tt:
            tw = sum(1 for t in tt if t["won"])
            tr = [t["pnl_pct"] for t in tt]
            print(f"    {tier_name:8s}: {len(tt):3d} trades, {tw/len(tt)*100:5.1f}% WR, avg {sum(tr)/len(tr):+.2f}%")
        else:
            print(f"    {tier_name:8s}: none")

    # By pattern
    print(f"\n  By Lead Pattern:")
    for pat in ["vol_acc", "compress", "retest", "ema", "exhaust"]:
        pt = [t for t in all_trades if t["top_pattern"] == pat]
        if pt:
            pw = sum(1 for t in pt if t["won"])
            print(f"    {pat:12s}: {len(pt):3d} signals, {pw/len(pt)*100:5.1f}% WR")


def main():
    print("=" * 70)
    print("  EVENING SCANNER BACKTEST v2 (with pre-filters)")
    print(f"  Stocks: {len(TEST_TICKERS)} | Lookback: {LOOKBACK} days")
    print(f"  Filters: SMA50 trend, ADX>18, ATR>1.5%, Vol>100k")
    print("=" * 70)

    trades_1d = []
    trades_2d = []
    trades_3d = []

    for idx, ticker in enumerate(TEST_TICKERS):
        symbol = f"{ticker}.NS"
        print(f"  [{idx+1}/{len(TEST_TICKERS)}] {ticker}...", end=" ", flush=True)

        try:
            stock = yf.Ticker(symbol)
            hist = stock.history(period="1y")
            if hist.empty or len(hist) < 100:
                print("SKIP")
                continue

            c = hist["Close"].tolist()
            h = hist["High"].tolist()
            l = hist["Low"].tolist()
            v = hist["Volume"].tolist()
            d = hist.index.tolist()

            t1 = run_for_hold_period(1, c, h, l, v, d, ticker)
            t2 = run_for_hold_period(2, c, h, l, v, d, ticker)
            t3 = run_for_hold_period(3, c, h, l, v, d, ticker)

            trades_1d.extend(t1)
            trades_2d.extend(t2)
            trades_3d.extend(t3)

            total = len(t2)
            wins = sum(1 for t in t2 if t["won"])
            print(f"{total} signals, {wins} wins ({wins/total*100:.0f}%)" if total else "filtered out")

        except Exception as e:
            print(f"ERR: {e}")
        time.sleep(0.3)

    print("\n" + "=" * 70)
    print("  RESULTS COMPARISON")
    print("=" * 70)

    print_results("1-DAY HOLD (pure next-day prediction)", trades_1d)
    print_results("2-DAY HOLD (short swing)", trades_2d)
    print_results("3-DAY HOLD (swing trade)", trades_3d)

    print("\n" + "=" * 70)
    if trades_2d:
        wr = sum(1 for t in trades_2d if t["won"]) / len(trades_2d) * 100
        returns = [t["pnl_pct"] for t in trades_2d]
        gp = sum(r for r in returns if r > 0)
        gl = abs(sum(r for r in returns if r < 0))
        pf = gp / gl if gl > 0 else 999
        print(f"  VERDICT (2-day): {wr:.1f}% win rate, {pf:.2f}x profit factor")
        if wr >= 55 and pf >= 1.5:
            print("  [OK] PROFITABLE - edge confirmed!")
        elif wr >= 50 or pf >= 1.2:
            print("  [!!] MARGINAL - close but needs more tuning")
        else:
            print("  [XX] Not ready - keep iterating")
    print("=" * 70)


if __name__ == "__main__":
    main()
