"""Vnstock v4 API data source for AIFIA.

vnstock v4 uses source='KBS' for data access.
Financial data format: items as rows, quarters as columns.
"""
from typing import List, Dict, Optional, Any, Iterator
from datetime import datetime, timedelta, date
import time
import json

import pandas as pd
import numpy as np
import re

from ..config import CrawlerConfig


class VnstockSource:
    """Data source using vnstock v4 API."""

    INDEX_SYMBOLS = {"VNINDEX", "VN-INDEX", "HNXINDEX", "UPCOMINDEX", "VN30"}
    
    def __init__(self, config: CrawlerConfig, rate_limiter=None):
        self.config = config
        self._source = None
        self._source_name = 'KBS'
        self._rate_limiter = rate_limiter
        self._registered = False
    
    def _ensure_registered(self):
        """Register a Vnstock API key once when VNSTOCK_API_KEY is configured."""
        if self._registered:
            return
        self._registered = True
        if not self.config.vnstock_api_key:
            return
        try:
            from vnstock import register_user
            register_user(api_key=self.config.vnstock_api_key)
            print("  [Vnstock] API key registered")
        except Exception as e:
            print(f"  [Vnstock] API key registration skipped: {e}")
    
    def _get_source(self, module: str):
        """Lazy-import and return the right vnstock API module."""
        if self._source is None:
            self._ensure_registered()
            from vnstock.api.listing import Listing
            from vnstock.api.company import Company
            from vnstock.api.financial import Finance
            from vnstock.api.quote import Quote
            self._source = {
                'listing': Listing(source=self._source_name),
                'company': lambda s: Company(symbol=s, source=self._source_name),
                'finance': lambda s: Finance(symbol=s, source=self._source_name),
                'quote': lambda s: Quote(symbol=s, source=self._source_name),
            }
        return self._source[module]
    
    def _wait_for_rate(self):
        """Wait for rate limit before making an API call."""
        if self._rate_limiter:
            self._rate_limiter.wait()
        else:
            time.sleep(self.config.delay_between_requests)
    
    def _safe_call(self, fn, *args, max_retries=3, **kwargs):
        """Make an API call with rate limit handling and automatic retry."""
        for attempt in range(max_retries):
            self._wait_for_rate()
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                err_str = str(e)
                # Check if it's a rate limit error
                wait_match = re.search(r'Chờ (\d+) giây', err_str)
                if wait_match and attempt < max_retries - 1:
                    wait_sec = int(wait_match.group(1)) + 2
                    print(f"    ⚡ Rate limited! Waiting {wait_sec}s (attempt {attempt+1}/{max_retries})...")
                    time.sleep(wait_sec)
                else:
                    raise  # re-raise if not rate limit or out of retries
    
    # ──────────────────────────────────────────────
    # Company List
    # ──────────────────────────────────────────────
    
    def get_all_symbols(self) -> List[str]:
        listing = self._get_source('listing')
        try:
            series = listing.all_symbols()
            return list(series) if series is not None else []
        except Exception as e:
            print(f"  [Vnstock] Error getting all symbols: {e}")
            return []
    
    def get_vn100_symbols(self) -> List[str]:
        listing = self._get_source('listing')
        try:
            series = self._safe_call(listing.symbols_by_group, 'VN100')
            return list(series) if series is not None else []
        except Exception as e:
            print(f"  [Vnstock] Error getting VN100: {e}")
            all_sym = self.get_all_symbols()
            return all_sym[:100] if len(all_sym) >= 100 else all_sym
    
    # ──────────────────────────────────────────────
    # Company Info
    # ──────────────────────────────────────────────
    
    def get_company_info_complete(self, symbol: str) -> Dict:
        """Get combined company info from overview + info."""
        info = {"symbol": symbol.upper()}
        
        try:
            company = self._get_source('company')(symbol)
            
            try:
                ov = self._safe_call(company.overview)
                if ov is not None and isinstance(ov, pd.DataFrame) and not ov.empty:
                    rec = ov.to_dict('records')[0]
                    info.update({
                        k: rec.get(k) for k in rec 
                        if k not in ['symbol'] and not isinstance(rec.get(k), (dict, list))
                    })
            except Exception as e:
                print(f"  [Vnstock] Overview error for {symbol}: {e}")
            
            try:
                c_info = self._safe_call(company.info)
                if c_info is not None:
                    if isinstance(c_info, pd.DataFrame) and not c_info.empty:
                        rec = c_info.to_dict('records')[0]
                        for k in rec:
                            if k not in ['symbol'] and not isinstance(rec.get(k), (dict, list)):
                                if isinstance(rec.get(k), str) and len(rec[k]) > 1000:
                                    info['profile_text'] = rec[k]
                                elif k not in info:
                                    info[k] = rec[k]
            except Exception as e:
                print(f"  [Vnstock] Info error for {symbol}: {e}")
            
        except Exception as e:
            print(f"  [Vnstock] Error getting company info for {symbol}: {e}")
        
        return info
    
    # ──────────────────────────────────────────────
    # Financial Reports
    # ──────────────────────────────────────────────
    
    def _transform_financial_data(self, df: pd.DataFrame, symbol: str, 
                                  report_type: str) -> List[Dict]:
        """Transform vnstock financial data (items as rows, quarters as cols)
        into normalized records for Supabase."""
        if df is None or df.empty:
            return []
        
        records = []
        
        # Identify quarter columns (e.g., '2025-Q4', '2026-Q1')
        quarter_cols = [c for c in df.columns if '-Q' in str(c) or 'Q' in str(c)]
        
        if not quarter_cols:
            return []
        
        for col in quarter_cols:
            # Parse quarter/year from column name
            try:
                if col.endswith('_1'):  # duplicate quarter (e.g. 2025-Q4_1)
                    col_clean = col.replace('_1', '')
                else:
                    col_clean = col
                
                parts = col_clean.split('-Q')
                year = int(parts[0])
                quarter = int(parts[1]) if parts[1] else None
            except (ValueError, IndexError):
                continue
            
            if not quarter:
                continue
            
            # Build report data as {item_name: value, ...}
            report_data = {}
            for _, row in df.iterrows():
                item = row.get('item_id') or row.get('item', '')
                val = row.get(col)
                # Convert numpy types
                if isinstance(val, (np.integer,)):
                    val = int(val)
                elif isinstance(val, (np.floating,)):
                    val = float(val) if not np.isnan(val) else None
                report_data[str(item)] = val
            
            records.append({
                "symbol": symbol.upper(),
                "quarter": quarter,
                "year": year,
                "report_type": report_type,
                "report_data": report_data,
                "source": "vnstock",
                "ingested_at": datetime.now().isoformat(),
            })
        
        return records
    
    def get_all_financials(self, symbol: str) -> Dict[str, List[Dict]]:
        """Get all financial reports for a company."""
        finance = self._get_source('finance')(symbol)
        result = {}
        
        for rtype in ['income_statement', 'balance_sheet', 'cash_flow', 'ratio']:
            try:
                method = getattr(finance, rtype, None)
                if method:
                    df = self._safe_call(method, period='quarter', years=5)
                    records = self._transform_financial_data(df, symbol, rtype)
                    result[rtype] = records
                    print(f"    {rtype}: {len(records)} quarters")
            except Exception as e:
                print(f"    {rtype}: error - {str(e)[:50]}")
                result[rtype] = []
        
        return result
    
    # ──────────────────────────────────────────────
    # Price History
    # ──────────────────────────────────────────────

    def _row_value(self, row: pd.Series, *keys: str):
        for key in keys:
            if key in row.index:
                val = row.get(key)
                if val is not None and not pd.isna(val):
                    return val
        return None

    def _price_records_from_df(self, df: pd.DataFrame, symbol: str) -> List[Dict]:
        if df is None or df.empty:
            return []

        records = []
        for _, row in df.iterrows():
            t = self._row_value(row, 'time', 'date', 'tradingDate', 'reportDate')
            if t is None:
                continue

            dt = pd.to_datetime(t, errors='coerce')
            if pd.isna(dt):
                continue

            open_price = self._row_value(row, 'open', 'Open')
            high = self._row_value(row, 'high', 'High')
            low = self._row_value(row, 'low', 'Low')
            close = self._row_value(row, 'close', 'Close', 'value')
            volume = self._row_value(row, 'volume', 'Volume', 'totalVolume')

            records.append({
                "symbol": symbol.upper().replace("VN-INDEX", "VNINDEX"),
                "date": str(dt.date()),
                "open": float(open_price) if open_price is not None else None,
                "high": float(high) if high is not None else None,
                "low": float(low) if low is not None else None,
                "close": float(close) if close is not None else None,
                "volume": int(volume) if volume is not None else 0,
                "source": "vnstock",
                "ingested_at": datetime.now().isoformat(),
            })
        return records
    
    def get_index_history(self, symbol: str, start: str = None,
                          end: str = None) -> List[Dict]:
        """Get historical OHLCV for market indices such as VNINDEX."""
        self._ensure_registered()
        start = start or self.config.price_start_date
        end = end or datetime.now().strftime("%Y-%m-%d")
        normalized = symbol.upper().replace("VN-INDEX", "VNINDEX")

        try:
            try:
                from vnstock import Market
            except ImportError:
                from vnstock_data import Market

            market = Market()
            df = self._safe_call(market.index(normalized).ohlcv, start=start, end=end)
            return self._price_records_from_df(df, normalized)
        except Exception as e:
            print(f"  [Vnstock] Error getting index price for {symbol}: {e}")
            return []
    
    def get_price_history(self, symbol: str, start: str = None, 
                          end: str = None) -> List[Dict]:
        """Get historical OHLCV price data."""
        normalized = symbol.upper()
        if normalized in self.INDEX_SYMBOLS:
            return self.get_index_history(normalized, start=start, end=end)

        quote = self._get_source('quote')(symbol)
        start = start or self.config.price_start_date
        end = end or datetime.now().strftime("%Y-%m-%d")
        
        try:
            try:
                df = self._safe_call(quote.history, start=start, end=end, interval='d')
            except TypeError:
                df = self._safe_call(quote.history, start=start, end=end)
            return self._price_records_from_df(df, symbol)
        except Exception as e:
            print(f"  [Vnstock] Error getting price for {symbol}: {e}")
        
        return []
