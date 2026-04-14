import json
import urllib.request

ticker = "RELIANCE.NS"
url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=summaryProfile,summaryDetail,financialData"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req, timeout=5) as response:
        data = json.loads(response.read().decode())
        print(json.dumps(data, indent=2)[:500])
except Exception as e:
    print("Error:", e)
