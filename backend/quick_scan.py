from evening_scanner import scan_single_stock

tickers = ['ASIANPAINT','SUNPHARMA','SBIN','ADANIENT','RELIANCE','TITAN','BEL','POWERGRID','TRENT','EICHERMOT']
results = []
for t in tickers:
    r = scan_single_stock(t)
    if r and r.get('trade_plan'):
        p = r['trade_plan']
        results.append(r)
        print(f"{r['ticker']:12s} | {r['conviction_tier']:7s} | {r['conviction_score']*100:.0f}%  | Rs{r['price']:>8.0f} | SL {p['stop_loss_pct']}% | T1 +{p['target_1_pct']}% | R:R {p['risk_reward']}")
    else:
        print(f"{t:12s} | FILTERED OUT")

print(f"\n{len(results)} stocks passed filters today")
