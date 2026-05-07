#!/usr/bin/env python3
"""
Backend API Testing for NSE Quant Stock Dashboard
Tests all the key endpoints with focus on persistence and profile-aware functionality.
Uses localhost:8001 as specified in the review request.
"""

import requests
import json
import time
import sys
from datetime import datetime

# Backend URL - using localhost:8001 as specified in review request
BASE_URL = "http://localhost:8001"

class BackendTester:
    def __init__(self):
        self.session = requests.Session()
        self.test_results = []
        
    def log_test(self, test_name, success, details=""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"    {details}")
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details
        })
        
    def test_endpoint(self, method, endpoint, data=None, expected_status=200, timeout=30):
        """Generic endpoint tester"""
        url = f"{BASE_URL}{endpoint}"
        try:
            if method.upper() == "GET":
                response = self.session.get(url, timeout=timeout)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data, timeout=timeout)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, timeout=timeout)
            else:
                return False, f"Unsupported method: {method}"
                
            if response.status_code == expected_status:
                return True, response.json() if response.content else {}
            else:
                return False, f"Expected {expected_status}, got {response.status_code}: {response.text}"
        except Exception as e:
            return False, f"Request failed: {str(e)}"
    
    def restart_backend(self):
        """Restart backend service"""
        import subprocess
        try:
            result = subprocess.run(["sudo", "supervisorctl", "restart", "backend"], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print("🔄 Backend restarted successfully")
                time.sleep(4)  # Wait for backend to start
                return True
            else:
                print(f"❌ Backend restart failed: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ Backend restart error: {e}")
            return False
    
    def test_persistence_portfolio(self):
        """Test 1: Portfolio persistence (highest priority)"""
        print("\n=== TEST 1: PORTFOLIO PERSISTENCE ===")
        
        # Step 1: Add TCS to portfolio
        portfolio_data = {
            "ticker": "TCS",
            "buy_price": 3500,
            "quantity": 5,
            "profile": "LONG_TERM",
            "buy_date": "2024-06-01T00:00:00"
        }
        
        success, response = self.test_endpoint("POST", "/api/portfolio", portfolio_data)
        if not success:
            self.log_test("Add TCS to portfolio", False, response)
            return
        
        expected_response = {"status": "added", "ticker": "TCS"}
        if response.get("status") == "added" and response.get("ticker") == "TCS":
            self.log_test("Add TCS to portfolio", True, "TCS added successfully")
        else:
            self.log_test("Add TCS to portfolio", False, f"Unexpected response: {response}")
            return
        
        # Step 2: Get portfolio and verify TCS with recommendation
        success, response = self.test_endpoint("GET", "/api/portfolio")
        if not success:
            self.log_test("Get portfolio with TCS", False, response)
            return
        
        items = response.get("items", [])
        tcs_item = next((item for item in items if item["ticker"] == "TCS"), None)
        
        if not tcs_item:
            self.log_test("Get portfolio with TCS", False, "TCS not found in portfolio")
            return
        
        # Check if recommendation block exists
        recommendation = tcs_item.get("recommendation", {})
        required_fields = ["target_price", "stop_price", "holding_period", "action", "rationale", "risk_reward"]
        missing_fields = [field for field in required_fields if field not in recommendation]
        
        if missing_fields:
            self.log_test("Portfolio TCS recommendation", False, f"Missing fields: {missing_fields}")
        else:
            self.log_test("Portfolio TCS recommendation", True, 
                         f"All recommendation fields present: target={recommendation['target_price']}, action={recommendation['action']}")
        
        # Step 3: Restart backend
        if not self.restart_backend():
            self.log_test("Backend restart", False, "Failed to restart backend")
            return
        
        self.log_test("Backend restart", True, "Backend restarted successfully")
        
        # Step 4: Verify TCS still exists after restart
        success, response = self.test_endpoint("GET", "/api/portfolio")
        if not success:
            self.log_test("Portfolio persistence after restart", False, response)
            return
        
        items = response.get("items", [])
        tcs_item = next((item for item in items if item["ticker"] == "TCS"), None)
        
        if tcs_item:
            self.log_test("Portfolio persistence after restart", True, "TCS survived backend restart")
        else:
            self.log_test("Portfolio persistence after restart", False, "TCS lost after restart - CRITICAL PERSISTENCE FAILURE")
        
        # Cleanup: Remove TCS
        success, response = self.test_endpoint("DELETE", "/api/portfolio/TCS")
        if success:
            self.log_test("Cleanup TCS from portfolio", True, "TCS removed successfully")
        else:
            self.log_test("Cleanup TCS from portfolio", False, response)
    
    def test_profile_aware_scan(self):
        """Test 2: Profile-aware scan functionality"""
        print("\n=== TEST 2: PROFILE-AWARE SCAN ===")
        
        # Test scan start with LONG_TERM profile
        scan_data = {
            "universe": "nifty50",
            "profile": "LONG_TERM"
        }
        
        success, response = self.test_endpoint("POST", "/api/scan/start", scan_data)
        if not success:
            self.log_test("Start LONG_TERM scan", False, response)
            return
        
        if response.get("status") == "started":
            self.log_test("Start LONG_TERM scan", True, f"Scan started with {response.get('total', 0)} stocks")
        else:
            self.log_test("Start LONG_TERM scan", False, f"Unexpected response: {response}")
            return
        
        # Check scan status
        time.sleep(2)  # Give scan a moment to start
        success, response = self.test_endpoint("GET", "/api/scan/status")
        if success and response.get("running") == True:
            self.log_test("Scan status check", True, f"Scan running: {response.get('current_ticker', 'N/A')}")
        else:
            self.log_test("Scan status check", False, f"Scan not running: {response}")
        
        # Test duplicate scan (should return 400)
        success, response = self.test_endpoint("POST", "/api/scan/start", scan_data, expected_status=400)
        if success:
            self.log_test("Duplicate scan prevention", True, "Correctly prevented duplicate scan")
        else:
            self.log_test("Duplicate scan prevention", False, response)
    
    def test_recommendation_endpoint(self):
        """Test 3: Individual recommendation endpoint"""
        print("\n=== TEST 3: RECOMMENDATION ENDPOINT ===")
        
        # Add INFY to portfolio first
        portfolio_data = {
            "ticker": "INFY",
            "buy_price": 1500,
            "quantity": 2,
            "profile": "SWING"
        }
        
        success, response = self.test_endpoint("POST", "/api/portfolio", portfolio_data)
        if not success:
            self.log_test("Add INFY to portfolio", False, response)
            return
        
        self.log_test("Add INFY to portfolio", True, "INFY added successfully")
        
        # Get recommendation for INFY (with 30s timeout for yfinance)
        success, response = self.test_endpoint("GET", "/api/portfolio/INFY/recommendation", timeout=30)
        if not success:
            self.log_test("Get INFY recommendation", False, response)
        else:
            recommendation = response.get("recommendation", {})
            required_fields = ["target_price", "action", "holding_period"]
            missing_fields = [field for field in required_fields if field not in recommendation]
            
            if missing_fields:
                self.log_test("INFY recommendation structure", False, f"Missing fields: {missing_fields}")
            else:
                self.log_test("INFY recommendation structure", True, 
                             f"target_price={recommendation['target_price']}, action={recommendation['action']}")
        
        # Cleanup: Remove INFY
        success, response = self.test_endpoint("DELETE", "/api/portfolio/INFY")
        if success:
            self.log_test("Cleanup INFY from portfolio", True, "INFY removed successfully")
        else:
            self.log_test("Cleanup INFY from portfolio", False, response)
    
    def test_stocks_profile_filter(self):
        """Test 4: Stocks endpoint with profile filter"""
        print("\n=== TEST 4: STOCKS PROFILE FILTER ===")
        
        profiles = ["LONG_TERM", "SWING", "SHORT_TERM"]
        
        for profile in profiles:
            success, response = self.test_endpoint("GET", f"/api/stocks?profile={profile}")
            if success:
                stocks = response if isinstance(response, list) else []
                self.log_test(f"Get stocks for {profile}", True, f"Returned {len(stocks)} stocks")
            else:
                self.log_test(f"Get stocks for {profile}", False, response)
    
    def test_watchlist_persistence(self):
        """Test 5: Watchlist persistence"""
        print("\n=== TEST 5: WATCHLIST PERSISTENCE ===")
        
        # Add HDFCBANK to watchlist
        watchlist_data = {
            "ticker": "HDFCBANK",
            "tag": "STAYER"
        }
        
        success, response = self.test_endpoint("POST", "/api/watchlist", watchlist_data)
        if not success:
            self.log_test("Add HDFCBANK to watchlist", False, response)
            return
        
        self.log_test("Add HDFCBANK to watchlist", True, "HDFCBANK added successfully")
        
        # Restart backend
        if not self.restart_backend():
            self.log_test("Backend restart for watchlist test", False, "Failed to restart backend")
            return
        
        # Check if HDFCBANK still exists
        success, response = self.test_endpoint("GET", "/api/watchlist")
        if not success:
            self.log_test("Watchlist persistence after restart", False, response)
            return
        
        watchlist_items = response if isinstance(response, list) else []
        hdfcbank_item = next((item for item in watchlist_items if item.get("ticker") == "HDFCBANK"), None)
        
        if hdfcbank_item:
            self.log_test("Watchlist persistence after restart", True, "HDFCBANK survived restart")
        else:
            self.log_test("Watchlist persistence after restart", False, "HDFCBANK lost after restart")
        
        # Cleanup: Remove HDFCBANK
        success, response = self.test_endpoint("DELETE", "/api/watchlist/HDFCBANK")
        if success:
            self.log_test("Cleanup HDFCBANK from watchlist", True, "HDFCBANK removed successfully")
        else:
            self.log_test("Cleanup HDFCBANK from watchlist", False, response)
    
    def test_alerts_persistence(self):
        """Test 6: Alerts settings persistence"""
        print("\n=== TEST 6: ALERTS SETTINGS PERSISTENCE ===")
        
        # Set alert settings
        alert_data = {
            "email": "test@example.com",
            "enabled": True
        }
        
        success, response = self.test_endpoint("POST", "/api/alerts/settings", alert_data)
        if not success:
            self.log_test("Set alert settings", False, response)
            return
        
        self.log_test("Set alert settings", True, "Alert settings updated")
        
        # Restart backend
        if not self.restart_backend():
            self.log_test("Backend restart for alerts test", False, "Failed to restart backend")
            return
        
        # Check if settings persist
        success, response = self.test_endpoint("GET", "/api/alerts/settings")
        if not success:
            self.log_test("Alerts persistence after restart", False, response)
            return
        
        if response.get("email") == "test@example.com" and response.get("enabled") == True:
            self.log_test("Alerts persistence after restart", True, "Alert settings survived restart")
        else:
            self.log_test("Alerts persistence after restart", False, f"Settings changed: {response}")
    
    def test_general_endpoints(self):
        """Test 7: General sanity endpoints"""
        print("\n=== TEST 7: GENERAL SANITY CHECKS ===")
        
        # Test market macro
        success, response = self.test_endpoint("GET", "/api/market/macro")
        if success:
            self.log_test("Market macro endpoint", True, f"Returned macro data")
        else:
            self.log_test("Market macro endpoint", False, response)
        
        # Test market confidence
        success, response = self.test_endpoint("GET", "/api/market/confidence")
        if success and "score" in response and "status" in response:
            self.log_test("Market confidence endpoint", True, f"Score: {response['score']}, Status: {response['status']}")
        else:
            self.log_test("Market confidence endpoint", False, response)
        
        # Test scan levels
        success, response = self.test_endpoint("GET", "/api/scan/levels")
        if success:
            self.log_test("Scan levels endpoint", True, "Scan levels returned")
        else:
            self.log_test("Scan levels endpoint", False, response)
    
    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting Backend API Tests for NSE Quant Stock Dashboard")
        print(f"Backend URL: {BASE_URL}")
        
        # Test backend connectivity first
        success, response = self.test_endpoint("GET", "/api/market/confidence")
        if not success:
            print(f"❌ CRITICAL: Cannot connect to backend at {BASE_URL}")
            print(f"Error: {response}")
            return False
        
        print("✅ Backend connectivity confirmed")
        
        # Run all tests in priority order
        self.test_persistence_portfolio()      # Highest priority
        self.test_profile_aware_scan()         # High priority  
        self.test_recommendation_endpoint()    # High priority
        self.test_stocks_profile_filter()      # Medium priority
        self.test_watchlist_persistence()      # Medium priority
        self.test_alerts_persistence()         # Medium priority
        self.test_general_endpoints()          # Low priority
        
        # Summary
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        
        if total - passed > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  • {result['test']}: {result['details']}")
        
        return passed == total

if __name__ == "__main__":
    tester = BackendTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)