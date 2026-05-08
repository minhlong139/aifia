"""AIFIA Crawler Pipeline - Orchestrates data collection from all sources."""
from typing import List, Dict, Optional
from datetime import datetime
import time
import json
import os

from .config import CrawlerConfig
from .sources.vnstock_source import VnstockSource
from .storage import SupabaseStorage


class CrawlPipeline:
    """Main data collection orchestrator for AIFIA.
    
    Flow:
    1. Fetch VN100 symbol list
    2. For each symbol: company info -> Supabase
    3. For each symbol: financial reports -> Supabase
    4. For each symbol: price history -> Supabase
    5. Macro data -> Supabase
    """
    
    def __init__(self, config: Optional[CrawlerConfig] = None):
        self.config = config or CrawlerConfig()
        self.vnstock = VnstockSource(self.config)
        self.storage = SupabaseStorage(self.config)
        self.stats = {
            "companies": 0,
            "financial_reports": 0,
            "price_records": 0,
            "errors": 0,
            "skipped": 0,
        }
    
    def run(self, symbols: Optional[List[str]] = None):
        """Execute the full crawl pipeline.
        
        Args:
            symbols: Optional list of symbols to crawl. If None, crawl VN100.
        """
        start_time = datetime.now()
        print(f"\n{'='*60}")
        print(f"🔍 AIFIA Crawl Pipeline Started")
        print(f"   Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        # Step 0: Validate storage connection
        if not self.storage.is_connected():
            print("⚠️  Supabase not configured. Running in dry-run mode (print only).")
        
        # Step 1: Get symbol list
        if not symbols:
            symbols = self._fetch_symbol_list()
        
        if not symbols:
            print("❌ No symbols to crawl. Exiting.")
            return
        
        print(f"\n📋 Total symbols to process: {len(symbols)}")
        
        # Step 2: Process each company
        for i, symbol in enumerate(symbols, 1):
            print(f"\n[{i}/{len(symbols)}] Processing {symbol}...")
            self._process_company(symbol)
        
        # Step 3: Macro data
        print(f"\n{'─'*60}")
        print("📊 Fetching macro data...")
        self._crawl_macro_data()
        
        # Summary
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\n{'='*60}")
        print(f"✅ Crawl Pipeline Complete")
        print(f"   Duration: {elapsed:.1f}s")
        print(f"   Companies : {self.stats['companies']}")
        print(f"   Reports   : {self.stats['financial_reports']}")
        print(f"   Price recs: {self.stats['price_records']}")
        print(f"   Errors    : {self.stats['errors']}")
        print(f"   Skipped   : {self.stats['skipped']}")
        print(f"{'='*60}\n")
        
        return self.stats
    
    def _fetch_symbol_list(self) -> List[str]:
        """Determine the list of symbols to crawl."""
        print("\n📋 Fetching VN100 symbol list...")
        
        symbols = self.vnstock.get_vn100_symbols()
        
        if not symbols:
            print("⚠️  VN100 list empty, falling back to all symbols...")
            symbols = self.vnstock.get_all_symbols()
        
        return symbols
    
    def _process_company(self, symbol: str):
        """Process a single company: info + reports + prices."""
        try:
            # 2a. Company info
            self._crawl_company_info(symbol)
            
            # 2b. Financial reports
            self._crawl_financial_reports(symbol)
            
            # 2c. Price history
            self._crawl_price_history(symbol)
            
        except Exception as e:
            print(f"  ❌ Error processing {symbol}: {e}")
            self.stats["errors"] += 1
    
    def _crawl_company_info(self, symbol: str):
        """Crawl company information and store to Supabase."""
        print(f"  📄 Fetching company info...")
        
        info = self.vnstock.get_company_info_complete(symbol)
        
        if not info:
            print(f"  ⚠️  No company info found")
            self.stats["skipped"] += 1
            return
        
        # Store to Supabase
        if self.storage.is_connected():
            success = self.storage.upsert_company(info)
            if success:
                self.stats["companies"] += 1
                print(f"  ✅ Company info saved")
            else:
                print(f"  ⚠️  Failed to save company info")
        else:
            print(f"  📝 [Dry-run] Company info: {info.get('symbol')} - {info.get('industry', 'N/A')}")
            self.stats["companies"] += 1
    
    def _crawl_financial_reports(self, symbol: str):
        """Crawl all financial reports for a company."""
        print(f"  📊 Fetching financial reports...")
        
        financials = self.vnstock.get_all_financials(symbol)
        
        total_reports = 0
        for report_type, data in financials.items():
            if not data:
                continue
            
            # Transform for Supabase schema
            reports_batch = []
            for row in data:
                quarter = row.get("quarter", row.get("q"))
                year = row.get("year")
                
                if not quarter or not year:
                    continue
                
                report = {
                    "symbol": symbol.upper(),
                    "quarter": int(quarter),
                    "year": int(year),
                    "report_type": report_type,
                    "report_data": row,
                    "source": "vnstock",
                    "ingested_at": datetime.now().isoformat(),
                }
                reports_batch.append(report)
            
            if reports_batch:
                if self.storage.is_connected():
                    self.storage.upsert_financial_reports_batch(reports_batch)
                total_reports += len(reports_batch)
        
        self.stats["financial_reports"] += total_reports
        print(f"  ✅ {total_reports} reports saved")
    
    def _crawl_price_history(self, symbol: str):
        """Crawl price history for a company."""
        print(f"  💹 Fetching price history...")
        
        # Check if we already have data (incremental crawl)
        latest_date = None
        if self.storage.is_connected():
            latest_date = self.storage.get_latest_price_date(symbol)
        
        prices = self.vnstock.get_price_history(symbol, start=latest_date)
        
        if not prices:
            print(f"  ⚠️  No price data")
            return
        
        if self.storage.is_connected():
            self.storage.upsert_price_data(prices)
        
        self.stats["price_records"] += len(prices)
        print(f"  ✅ {len(prices)} price records saved")
    
    def _crawl_macro_data(self):
        """Crawl macro economic indicators."""
        macro_data = self.vnstock.get_macro_data()
        
        if not macro_data:
            print(f"  ⚠️  No macro data found")
            return
        
        if self.storage.is_connected():
            self.storage.upsert_macro_data(macro_data)
        
        print(f"  ✅ {len(macro_data)} macro records saved")


# CLI entry point
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="AIFIA Crawler Pipeline")
    parser.add_argument("--symbols", nargs="+", help="Specific symbols to crawl")
    parser.add_argument("--dry-run", action="store_true", help="Print without storing")
    
    args = parser.parse_args()
    
    config = CrawlerConfig()
    pipeline = CrawlPipeline(config)
    
    if args.dry_run:
        # Disable storage by not setting credentials
        pass
    
    pipeline.run(symbols=args.symbols)
