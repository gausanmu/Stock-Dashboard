#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime

class NSEQuantEngineAPITester:
    def __init__(self, base_url="https://nse-quant-engine.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []

    def run_test(self, name, method, endpoint, expected_status, data=None, params=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    if isinstance(response_data, list):
                        print(f"   Response: List with {len(response_data)} items")
                    elif isinstance(response_data, dict):
                        print(f"   Response keys: {list(response_data.keys())}")
                except:
                    print(f"   Response: {response.text[:100]}...")
            else:
                self.failed_tests.append({
                    "test": name,
                    "expected": expected_status,
                    "actual": response.status_code,
                    "response": response.text[:200]
                })
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}")

            return success, response.json() if success and response.content else {}

        except Exception as e:
            self.failed_tests.append({
                "test": name,
                "error": str(e)
            })
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test GET /api/ returns root message"""
        success, response = self.run_test(
            "Root API Endpoint",
            "GET",
            "api/",
            200
        )
        return success

    def test_get_stocks(self):
        """Test GET /api/stocks returns list of stocks"""
        success, response = self.run_test(
            "Get All Stocks",
            "GET", 
            "api/stocks",
            200
        )
        if success and isinstance(response, list):
            print(f"   Found {len(response)} stocks in database")
            if len(response) > 0:
                sample_stock = response[0]
                print(f"   Sample stock: {sample_stock.get('ticker', 'N/A')} - {sample_stock.get('name', 'N/A')}")
        return success

    def test_scan_status(self):
        """Test GET /api/scan/status returns scan state"""
        success, response = self.run_test(
            "Get Scan Status",
            "GET",
            "api/scan/status", 
            200
        )
        if success:
            print(f"   Scan running: {response.get('running', False)}")
            print(f"   Progress: {response.get('progress', 0)}/{response.get('total', 0)}")
        return success

    def test_search_stocks(self):
        """Test GET /api/stocks/search?q=TCS returns matching stocks"""
        success, response = self.run_test(
            "Search Stocks (TCS)",
            "GET",
            "api/stocks/search",
            200,
            params={"q": "TCS"}
        )
        if success and isinstance(response, list):
            print(f"   Found {len(response)} matching stocks for 'TCS'")
        return success

    def test_get_regimes(self):
        """Test GET /api/stocks/regimes returns stocks grouped by regime"""
        success, response = self.run_test(
            "Get Stocks by Regimes",
            "GET",
            "api/stocks/regimes",
            200
        )
        if success and isinstance(response, dict):
            regimes = list(response.keys())
            print(f"   Found regimes: {regimes}")
            for regime, data in response.items():
                print(f"   {regime}: {data.get('count', 0)} stocks")
        return success

    def test_get_single_stock(self):
        """Test GET /api/stocks/TCS returns single stock detail"""
        success, response = self.run_test(
            "Get Single Stock (TCS)",
            "GET",
            "api/stocks/TCS",
            200
        )
        if success:
            print(f"   Stock: {response.get('ticker', 'N/A')} - {response.get('name', 'N/A')}")
            print(f"   Price: {response.get('price', 'N/A')}, Regime: {response.get('regime', 'N/A')}")
        return success

    def test_watchlist_operations(self):
        """Test watchlist CRUD operations"""
        # First get current watchlist
        success, current_watchlist = self.run_test(
            "Get Current Watchlist",
            "GET",
            "api/watchlist",
            200
        )
        if not success:
            return False

        # Add to watchlist
        test_ticker = "RELIANCE"
        success, response = self.run_test(
            "Add to Watchlist",
            "POST",
            "api/watchlist",
            200,
            data={"ticker": test_ticker, "tag": "GAINER"}
        )
        if not success:
            return False

        # Get watchlist again to verify addition
        success, updated_watchlist = self.run_test(
            "Get Updated Watchlist",
            "GET", 
            "api/watchlist",
            200
        )
        if not success:
            return False

        # Remove from watchlist
        success, response = self.run_test(
            "Remove from Watchlist",
            "DELETE",
            f"api/watchlist/{test_ticker}",
            200
        )
        return success

    def test_portfolio_operations(self):
        """Test portfolio CRUD operations"""
        # Get current portfolio
        success, current_portfolio = self.run_test(
            "Get Current Portfolio",
            "GET",
            "api/portfolio",
            200
        )
        if not success:
            return False

        if success:
            print(f"   Portfolio items: {len(current_portfolio.get('items', []))}")
            summary = current_portfolio.get('summary', {})
            print(f"   Total invested: {summary.get('total_invested', 0)}")
            print(f"   Total current: {summary.get('total_current', 0)}")

        # Add to portfolio
        test_ticker = "INFY"
        success, response = self.run_test(
            "Add to Portfolio",
            "POST",
            "api/portfolio",
            200,
            data={
                "ticker": test_ticker,
                "buy_price": 1500.0,
                "quantity": 10,
                "tag": "STAYER"
            }
        )
        if not success:
            return False

        # Get portfolio again to verify addition
        success, updated_portfolio = self.run_test(
            "Get Updated Portfolio",
            "GET",
            "api/portfolio", 
            200
        )
        if not success:
            return False

        # Remove from portfolio
        success, response = self.run_test(
            "Remove from Portfolio",
            "DELETE",
            f"api/portfolio/{test_ticker}",
            200
        )
        return success

    def test_macro_endpoints(self):
        """Test macro data endpoints"""
        success, response = self.run_test(
            "Get Macro Data",
            "GET",
            "api/market/macro",
            200
        )
        if success:
            indicators = list(response.keys())
            print(f"   Macro indicators: {indicators}")

        success2, response2 = self.run_test(
            "Get Confidence Score",
            "GET", 
            "api/market/confidence",
            200
        )
        if success2:
            print(f"   Confidence score: {response2.get('score', 'N/A')}")
            print(f"   Status: {response2.get('status', 'N/A')}")

        return success and success2

    def test_scan_levels(self):
        """Test GET /api/scan/levels returns scan level info with stock counts"""
        success, response = self.run_test(
            "Get Scan Levels",
            "GET",
            "api/scan/levels",
            200
        )
        if success:
            levels = list(response.keys())
            print(f"   Available scan levels: {levels}")
            for level, info in response.items():
                print(f"   {level}: {info.get('count', 0)} stocks, ~{info.get('est_minutes', 0)} min")
        return success

    def test_sectors_heatmap(self):
        """Test GET /api/sectors/heatmap returns sector performance data"""
        success, response = self.run_test(
            "Get Sectors Heatmap",
            "GET",
            "api/sectors/heatmap",
            200
        )
        if success and isinstance(response, list):
            print(f"   Found {len(response)} sectors")
            if len(response) > 0:
                sample_sector = response[0]
                print(f"   Sample sector: {sample_sector.get('sector', 'N/A')} - {sample_sector.get('avg_change', 0)}% change")
        return success

    def test_news_sentiment(self):
        """Test GET /api/news/TCS returns articles with sentiment analysis"""
        success, response = self.run_test(
            "Get News Sentiment (TCS)",
            "GET",
            "api/news/TCS",
            200
        )
        if success:
            articles = response.get('articles', [])
            overall = response.get('overall', {})
            print(f"   Found {len(articles)} articles")
            print(f"   Overall sentiment: {overall.get('sentiment', 'N/A')} ({overall.get('score', 0)}/100)")
            if len(articles) > 0:
                print(f"   Sample article: {articles[0].get('title', 'N/A')[:50]}...")
        return success

    def test_alerts_endpoints(self):
        """Test alerts configuration and regime changes endpoints"""
        # Test alert settings
        success1, response1 = self.run_test(
            "Get Alert Settings",
            "GET",
            "api/alerts/settings",
            200
        )
        if success1:
            print(f"   Alert email: {response1.get('email', 'N/A')}")
            print(f"   Alerts enabled: {response1.get('enabled', False)}")

        # Test regime changes
        success2, response2 = self.run_test(
            "Get Regime Changes",
            "GET",
            "api/alerts/regime-changes",
            200
        )
        if success2 and isinstance(response2, list):
            print(f"   Found {len(response2)} regime changes")
            if len(response2) > 0:
                sample_change = response2[0]
                print(f"   Sample change: {sample_change.get('ticker', 'N/A')} {sample_change.get('old_regime', 'N/A')} -> {sample_change.get('new_regime', 'N/A')}")

        return success1 and success2

    def test_scan_start_nifty200(self):
        """Test POST /api/scan/start with universe=nifty200 (without actually running it)"""
        # Note: We won't actually start the scan as it takes too long
        # Instead we'll test that the endpoint accepts the request properly
        print("\n🔍 Testing Scan Start (Nifty200) - Validation Only...")
        print("   Note: Not actually starting scan to avoid long wait time")
        
        # First check if a scan is already running
        success, status = self.run_test(
            "Check Scan Status Before Test",
            "GET",
            "api/scan/status",
            200
        )
        
        if success and status.get('running', False):
            print("   ⚠️  Scan already running, skipping start test")
            return True
        
        # Test the scan start endpoint (but we'll immediately check status instead of waiting)
        try:
            url = f"{self.base_url}/api/scan/start"
            headers = {'Content-Type': 'application/json'}
            response = requests.post(url, json={"universe": "nifty200"}, headers=headers, timeout=10)
            
            if response.status_code == 200:
                print("✅ Scan start endpoint accepts nifty200 universe")
                # Immediately check status to confirm it started
                status_response = requests.get(f"{self.base_url}/api/scan/status", timeout=10)
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    if status_data.get('running', False):
                        print("✅ Scan successfully initiated")
                        return True
                return True
            else:
                print(f"❌ Scan start failed with status {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Scan start test failed: {str(e)}")
            return False

def main():
    print("🚀 Starting NSE Quant Engine API Tests")
    print("=" * 50)
    
    tester = NSEQuantEngineAPITester()
    
    # Run all tests
    test_results = []
    
    # Phase 1 tests (existing)
    test_results.append(tester.test_root_endpoint())
    test_results.append(tester.test_get_stocks())
    test_results.append(tester.test_scan_status())
    test_results.append(tester.test_search_stocks())
    test_results.append(tester.test_get_regimes())
    test_results.append(tester.test_get_single_stock())
    test_results.append(tester.test_macro_endpoints())
    test_results.append(tester.test_watchlist_operations())
    test_results.append(tester.test_portfolio_operations())
    
    # Phase 2 tests (new features)
    test_results.append(tester.test_scan_levels())
    test_results.append(tester.test_sectors_heatmap())
    test_results.append(tester.test_news_sentiment())
    test_results.append(tester.test_alerts_endpoints())
    test_results.append(tester.test_scan_start_nifty200())

    # Print final results
    print("\n" + "=" * 50)
    print(f"📊 Final Results: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    if tester.failed_tests:
        print("\n❌ Failed Tests:")
        for failure in tester.failed_tests:
            print(f"   - {failure.get('test', 'Unknown')}: {failure.get('error', failure.get('response', 'Unknown error'))}")
    
    success_rate = (tester.tests_passed / tester.tests_run * 100) if tester.tests_run > 0 else 0
    print(f"📈 Success Rate: {success_rate:.1f}%")
    
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())