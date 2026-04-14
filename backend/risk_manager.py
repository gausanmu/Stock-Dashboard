import math
import yfinance as yf
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class RiskManager:
    def __init__(self, account_size=50000.0, max_portfolio_drawdown=0.15, max_sector_allocation=0.30):
        self.account_size = account_size
        self.max_portfolio_drawdown = max_portfolio_drawdown
        self.max_sector_allocation = max_sector_allocation

    def calculate_net_returns(self, entry_price, exit_price, quantity, is_delivery=True):
        """
        Calculates Net Returns factoring Indian market costs (Zerodha style approx).
        """
        turnover = (entry_price + exit_price) * quantity
        
        # Brokerage (Equity Delivery is usually 0 or minimal, intraday is 0.03% or Rs 20)
        brokerage = 0 if is_delivery else min(20, turnover * 0.0003) * 2 
        
        # STT/CTT: 0.1% on buy and sell for delivery
        stt = turnover * 0.001 if is_delivery else (exit_price * quantity * 0.00025)
        
        # Exchange transaction charges: ~0.00345%
        exchange_txn_charge = turnover * 0.0000345
        
        # GST: 18% on brokerage + exchange txn charge
        gst = (brokerage + exchange_txn_charge) * 0.18
        
        # SEBI charges & Stamp duty
        sebi_charges = turnover * 0.000001
        stamp_duty = (entry_price * quantity) * 0.00015 if is_delivery else (entry_price * quantity) * 0.00003

        total_charges = brokerage + stt + exchange_txn_charge + gst + sebi_charges + stamp_duty
        gross_profit = (exit_price - entry_price) * quantity
        net_profit = gross_profit - total_charges
        
        return {
            "gross_profit": round(gross_profit, 2),
            "total_charges": round(total_charges, 2),
            "net_profit": round(net_profit, 2),
            "net_roi_pct": round((net_profit / (entry_price * quantity)) * 100, 2)
        }

    def position_sizing_kelly(self, win_rate, win_loss_ratio, current_price, stop_loss_price, max_risk_pct=0.02):
        """
        Calculates optimal position size using modified Kelly / Fixed fraction.
        """
        if current_price <= stop_loss_price:
            return 0
            
        # Kelly percentage = W - [(1 - W) / R]
        kelly_pct = win_rate - ((1 - win_rate) / win_loss_ratio) if win_loss_ratio > 0 else 0
        
        # Half-Kelly for safety
        allocation_pct = max(0, min(kelly_pct / 2, max_risk_pct)) 
        
        # If totally unproven, fallback to fixed fractional risk (e.g., risk max 2% of account)
        if allocation_pct <= 0:
            allocation_pct = max_risk_pct
            
        max_loss_per_share = current_price - stop_loss_price
        risk_capital = self.account_size * allocation_pct
        
        recommended_shares = math.floor(risk_capital / max_loss_per_share)
        
        # Ensure we don't exceed our total account power (no leverage)
        max_affordable = math.floor(self.account_size / current_price)
        final_shares = min(recommended_shares, max_affordable)
        
        return {
            "recommended_shares": final_shares,
            "allocated_capital": round(final_shares * current_price, 2),
            "risk_amount": round(final_shares * max_loss_per_share, 2),
            "risk_pct_of_account": round(((final_shares * max_loss_per_share) / self.account_size) * 100, 2)
        }

    def check_correlation(self, target_ticker, portfolio_tickers, period="3mo", threshold=0.7):
        """
        Checks if the target_ticker correlates highly (>0.7) with existing portfolio.
        """
        if not portfolio_tickers:
            return {"correlated_with": [], "max_correlation": 0.0, "safe": True}
            
        all_tickers = portfolio_tickers + [target_ticker]
        ns_tickers = [t if t.endswith(".NS") else f"{t}.NS" for t in all_tickers]
        
        try:
            data = yf.download(ns_tickers, period=period, progress=False)["Close"]
            
            if len(all_tickers) == 1 or data.empty or target_ticker not in data.columns:
                return {"correlated_with": [], "max_correlation": 0.0, "safe": True}
                
            corr_matrix = data.corr()
            target_ns = target_ticker if target_ticker.endswith(".NS") else f"{target_ticker}.NS"
            
            correlations = corr_matrix[target_ns].drop(target_ns)
            high_corr = correlations[correlations > threshold].to_dict()
            
            # Remove .NS from output keys
            cleaned_high_corr = {k.replace(".NS", ""): round(v, 2) for k, v in high_corr.items()}
            
            safe = len(high_corr) == 0
            
            return {
                "correlated_with": cleaned_high_corr,
                "max_correlation": round(correlations.max(), 2) if not correlations.empty else 0.0,
                "safe": safe
            }
            
        except Exception as e:
            logger.error(f"Correlation check failed: {e}")
            return {"correlated_with": [], "max_correlation": 0.0, "safe": True}

    def analyze_portfolio_risk(self, portfolio, current_account_value):
        """
        Analyzes the full portfolio for sector limits and global drawdown.
        portfolio format: list of dicts {"ticker": str, "sector": str, "value": float, "pnl_pct": float}
        """
        if not portfolio:
            return {"status": "HEALTHY", "warnings": []}
            
        warnings = []
        sector_weights = {}
        total_pnl = 0.0
        
        for item in portfolio:
            sector = item.get("sector", "General")
            val = item.get("value", 0.0)
            sector_weights[sector] = sector_weights.get(sector, 0.0) + val
            total_pnl += (item.get("pnl_pct", 0.0) * val) # Weighted PnL proxy

        # Check total drawdown
        if current_account_value > 0 and self.account_size > 0:
             drawdown = (self.account_size - current_account_value) / self.account_size
             if drawdown > self.max_portfolio_drawdown:
                 warnings.append(f"CRITICAL: Portfolio drawdown ({round(drawdown*100, 2)}%) exceeds {self.max_portfolio_drawdown*100}% limit. Halt new trades.")

        # Check sector concentration
        for sector, value in sector_weights.items():
            weight_pct = value / current_account_value if current_account_value > 0 else 0
            if weight_pct > self.max_sector_allocation:
                warnings.append(f"WARNING: Sector {sector} exceeds {self.max_sector_allocation*100}% concentration ({round(weight_pct*100, 2)}%).")

        return {
            "status": "CRITICAL" if any("CRITICAL" in w for w in warnings) else "WARNING" if warnings else "HEALTHY",
            "warnings": warnings,
            "sector_exposure": {k: round((v/current_account_value)*100, 2) if current_account_value>0 else 0 for k, v in sector_weights.items()}
        }
