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
    
    def __init__(self, config: CrawlerConfig, rate_limiter=None):
        self.config = config
        self._source = None
        self._source_name = 'KBS'
        self._rate_limiter = rate_limiter
    
    def _get_source(self, module: str):
        """Lazy-import and return the right vnstock API module."""
        if self._source is None:
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
    
    def get_price_history(self, symbol: str, start: str = None, 
                          end: str = None) -> List[Dict]:
        """Get historical OHLCV price data."""
        quote = self._get_source('quote')(symbol)
        start = start or self.config.price_start_date
        end = end or datetime.now().strftime("%Y-%m-%d")
        
        try:
            df = self._safe_call(quote.history, start=start, end=end)
            if df is not None and not df.empty:
                records = []
                for _, row in df.iterrows():
                    t = row.get('time')
                    if pd.isna(t):
                        continue
                    
                    records.append({
                        "symbol": symbol.upper(),
                        "date": str(t.date()) if hasattr(t, 'date') else str(t)[:10],
                        "open": float(row.get('open', 0)) if not pd.isna(row.get('open', np.nan)) else None,
                        "high": float(row.get('high', 0)) if not pd.isna(row.get('high', np.nan)) else None,
                        "low": float(row.get('low', 0)) if not pd.isna(row.get('low', np.nan)) else None,
                        "close": float(row.get('close', 0)) if not pd.isna(row.get('close', np.nan)) else None,
                        "volume": int(row.get('volume', 0)) if not pd.isna(row.get('volume', np.nan)) else 0,
                        "source": "vnstock",
                        "ingested_at": datetime.now().isoformat(),
                    })
                return records
        except Exception as e:
            print(f"  [Vnstock] Error getting price for {symbol}: {e}")
        
        return []
