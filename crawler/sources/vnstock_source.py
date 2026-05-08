"""Vnstock API data source for AIFIA."""
from typing import List, Dict, Optional, Any, Iterator
from datetime import datetime, timedelta
import time
import json

import pandas as pd

from ..config import CrawlerConfig


class VnstockSource:
    """Data source using the vnstock Python library.
    
    Provides: company list, company info, financial reports, price history.
    """
    
    def __init__(self, config: CrawlerConfig):
        self.config = config
        self._vnstock = None  # lazy import
    
    def _import_vnstock(self):
        """Lazy import vnstock with error handling."""
        if self._vnstock is None:
            try:
                import vnstock
                self._vnstock = vnstock
            except ImportError:
                raise ImportError(
                    "vnstock library not installed. Run: pip install vnstock"
                )
        return self._vnstock
    
    def _to_dict(self, df: pd.DataFrame) -> List[Dict]:
        """Convert pandas DataFrame to list of dicts for Supabase."""
        if df is None or df.empty:
            return []
        # Convert NaN to None for JSON serialization
        return json.loads(df.fillna(0).to_json(orient="records", date_format="iso"))
    
    def _rate_limit(self):
        """Respect rate limits between API calls."""
        time.sleep(self.config.delay_between_requests)
    
    # ──────────────────────────────────────────────
    # Company List
    # ──────────────────────────────────────────────
    
    def get_all_symbols(self) -> List[str]:
        """Get all listed symbols."""
        vn = self._import_vnstock()
        try:
            df = vn.all_symbols()
            return df["ticker"].tolist() if "ticker" in df.columns else []
        except Exception as e:
            print(f"  [Vnstock] Error getting all symbols: {e}")
            return []
    
    def get_vn100_symbols(self) -> List[str]:
        """Get VN100 symbols specifically."""
        vn = self._import_vnstock()
        try:
            df = vn.symbols_by_group("VN100")
            symbols = df["ticker"].tolist() if "ticker" in df.columns else []
            print(f"  [Vnstock] Found {len(symbols)} VN100 symbols")
            return symbols
        except Exception as e:
            print(f"  [Vnstock] Error getting VN100: {e}")
            return []
    
    # ──────────────────────────────────────────────
    # Company Info
    # ──────────────────────────────────────────────
    
    def get_company_overview(self, symbol: str) -> Optional[Dict]:
        """Get company overview data."""
        vn = self._import_vnstock()
        try:
            df = vn.overview(symbol)
            if df is not None and not df.empty:
                data = self._to_dict(df)
                return data[0] if data else None
        except Exception as e:
            print(f"  [Vnstock] Error getting overview for {symbol}: {e}")
        return None
    
    def get_company_profile(self, symbol: str) -> Optional[Dict]:
        """Get detailed company profile."""
        vn = self._import_vnstock()
        try:
            df = vn.profile(symbol)
            if df is not None and not df.empty:
                data = self._to_dict(df)
                return data[0] if data else None
        except Exception as e:
            print(f"  [Vnstock] Error getting profile for {symbol}: {e}")
        return None
    
    def get_company_info_complete(self, symbol: str) -> Dict:
        """Get combined company info (overview + profile)."""
        overview = self.get_company_overview(symbol) or {}
        profile = self.get_company_profile(symbol) or {}
        
        # Merge, preferring non-null values
        info = {**profile, **overview}
        
        # Ensure required fields
        info.setdefault("symbol", symbol.upper())
        
        # Build profile text for AI
        profile_parts = []
        for key in ["industry", "industry_en", "established_date", "website", "no_employees"]:
            if key in info and info[key]:
                profile_parts.append(f"{key}: {info[key]}")
        info["profile_text"] = "\n".join(profile_parts)
        
        self._rate_limit()
        return info
    
    # ──────────────────────────────────────────────
    # Financial Reports
    # ──────────────────────────────────────────────
    
    def get_income_statement(self, symbol: str, years: int = 5) -> List[Dict]:
        """Get income statement data (quarterly)."""
        vn = self._import_vnstock()
        try:
            df = vn.income_statement(symbol, period="quarter", years=years)
            return self._to_dict(df)
        except Exception as e:
            print(f"  [Vnstock] Error getting income statement for {symbol}: {e}")
            return []
    
    def get_balance_sheet(self, symbol: str, years: int = 5) -> List[Dict]:
        """Get balance sheet data (quarterly)."""
        vn = self._import_vnstock()
        try:
            df = vn.balance_sheet(symbol, period="quarter", years=years)
            return self._to_dict(df)
        except Exception as e:
            print(f"  [Vnstock] Error getting balance sheet for {symbol}: {e}")
            return []
    
    def get_cash_flow(self, symbol: str, years: int = 5) -> List[Dict]:
        """Get cash flow data (quarterly)."""
        vn = self._import_vnstock()
        try:
            df = vn.cash_flow(symbol, period="quarter", years=years)
            return self._to_dict(df)
        except Exception as e:
            print(f"  [Vnstock] Error getting cash flow for {symbol}: {e}")
            return []
    
    def get_financial_ratios(self, symbol: str, years: int = 5) -> List[Dict]:
        """Get financial ratios."""
        vn = self._import_vnstock()
        try:
            df = vn.ratio(symbol, period="quarter", years=years)
            return self._to_dict(df)
        except Exception as e:
            print(f"  [Vnstock] Error getting ratios for {symbol}: {e}")
            return []
    
    def get_all_financials(self, symbol: str) -> dict:
        """Get all financial reports for a company."""
        years = self.config.financial_years_back
        return {
            "income_statement": self.get_income_statement(symbol, years),
            "balance_sheet": self.get_balance_sheet(symbol, years),
            "cash_flow": self.get_cash_flow(symbol, years),
            "ratios": self.get_financial_ratios(symbol, years),
        }
    
    # ──────────────────────────────────────────────
    # Price History
    # ──────────────────────────────────────────────
    
    def get_price_history(self, symbol: str, start: str = None, end: str = None) -> List[Dict]:
        """Get historical OHLCV price data."""
        vn = self._import_vnstock()
        start = start or self.config.price_start_date
        end = end or datetime.now().strftime("%Y-%m-%d")
        
        try:
            df = vn.stock_historical_data(symbol, start, end)
            if df is not None and not df.empty:
                data = self._to_dict(df)
                # Add symbol field
                for row in data:
                    row["symbol"] = symbol.upper()
                return data
        except Exception as e:
            print(f"  [Vnstock] Error getting price history for {symbol}: {e}")
        return []
    
    # ──────────────────────────────────────────────
    # Shareholders & Management
    # ──────────────────────────────────────────────
    
    def get_shareholders(self, symbol: str) -> List[Dict]:
        """Get major shareholders."""
        vn = self._import_vnstock()
        try:
            df = vn.shareholders(symbol)
            return self._to_dict(df)
        except Exception as e:
            print(f"  [Vnstock] Error getting shareholders for {symbol}: {e}")
            return []
    
    def get_officers(self, symbol: str) -> List[Dict]:
        """Get management/board members."""
        vn = self._import_vnstock()
        try:
            df = vn.officers(symbol)
            return self._to_dict(df)
        except Exception as e:
            print(f"  [Vnstock] Error getting officers for {symbol}: {e}")
            return []
    
    # ──────────────────────────────────────────────
    # Macro Data
    # ──────────────────────────────────────────────
    
    def get_macro_data(self) -> List[Dict]:
        """Get macro economic indicators (GDP, CPI, etc.)."""
        vn = self._import_vnstock()
        results = []
        try:
            # Try common macro indicators
            macro_types = ["gdp", "cpi", "interest_rate"]
            for macro_type in macro_types:
                try:
                    df = vn.macro_data(macro_type)
                    if df is not None and not df.empty:
                        data = self._to_dict(df)
                        for row in data:
                            row["indicator"] = macro_type
                        results.extend(data)
                except Exception:
                    pass
                self._rate_limit()
        except Exception as e:
            print(f"  [Vnstock] Error getting macro data: {e}")
        return results
