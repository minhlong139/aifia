"""AIFIA Crawler Pipeline - Orchestrates data collection from all sources."""
from typing import List, Dict, Optional, Set
from datetime import datetime
import time
import json
import os

from .config import CrawlerConfig
from .sources.vnstock_source import VnstockSource
from .storage import SupabaseStorage


class RateLimiter:
    """Global rate limiter that ensures max N requests per minute."""
    def __init__(self, max_per_minute: int = 15):
        self.max_per_minute = max_per_minute
        self.request_times: list = []
        self.min_interval = 60.0 / max_per_minute
    
    def wait(self):
        """Wait if needed to stay under rate limit."""
        import time
        now = time.time()
        # Remove requests older than 60s
        self.request_times = [t for t in self.request_times if now - t < 60]
        
        if len(self.request_times) >= self.max_per_minute:
            wait = 60 - (now - self.request_times[0]) + 1
            if wait > 0:
                print(f"    ⏳ Rate limit: waiting {wait:.0f}s...")
                time.sleep(wait)
        else:
            # Ensure min interval between requests
            if self.request_times:
                elapsed = now - self.request_times[-1]
                if elapsed < self.min_interval:
                    time.sleep(self.min_interval - elapsed)
        
        self.request_times.append(time.time())


INDEX_SYMBOLS = {"VNINDEX", "HNXINDEX", "UPCOMINDEX", "VN30", "VN-INDEX"}


class CrawlPipeline:
    """Main data collection orchestrator for AIFIA.
    
    Flow:
    1. Fetch VN100 symbol list
    2. For each symbol: company info -> Supabase + local JSON
    3. For each symbol: financial reports -> Supabase + local JSON
    4. For each symbol: price history -> Supabase + local JSON
    5. Macro data -> Supabase + local JSON
    """
    
    def __init__(self, config: Optional[CrawlerConfig] = None):
        self.config = config or CrawlerConfig()
        self.rate_limiter = RateLimiter(max_per_minute=15)
        self.vnstock = VnstockSource(self.config, rate_limiter=self.rate_limiter)
        self.storage = SupabaseStorage(self.config)
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.stats = {
            "companies": 0,
            "financial_reports": 0,
            "price_records": 0,
            "errors": 0,
            "skipped": 0,
            "symbols_attempted": [],
            "symbols_with_data": [],
        }
    
    def run(self, symbols: Optional[List[str]] = None):
        """Execute the full crawl pipeline."""
        start_time = datetime.now()
        print(f"\n{'='*60}")
        print(f"🔍 AIFIA Crawl Pipeline Started")
        print(f"   Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        if not self.storage.is_connected():
            print("⚠️  Supabase not configured → saving to data/*.json")
        else:
            print("✅ Supabase connected")
        
        # Step 1: Get symbol list
        if not symbols:
            symbols = self._fetch_symbol_list()
        
        if not symbols:
            print("❌ No symbols to crawl. Exiting.")
            return
        
        print(f"\n📋 {len(symbols)} symbols to process")
        self._save_symbols(symbols)
        
        # Step 2: Process each company with rate limiting
        for i, symbol in enumerate(symbols, 1):
            print(f"\n[{i}/{len(symbols)}] {symbol}...")
            self.stats["symbols_attempted"].append(symbol)
            self._process_company(symbol)
            
            # Rate limit handled by RateLimiter in vnstock_source
        
        # Summary
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\n{'='*60}")
        print(f"✅ Crawl Pipeline Complete")
        print(f"   Duration  : {elapsed:.0f}s ({elapsed/60:.1f}min)")
        print(f"   Companies : {self.stats['companies']}")
        print(f"   Reports   : {self.stats['financial_reports']}")
        print(f"   Price recs: {self.stats['price_records']}")
        print(f"   Errors    : {self.stats['errors']}")
        print(f"   Skipped   : {self.stats['skipped']}")
        print(f"{'='*60}\n")
        
        # Save summary
        self._save_summary()
        
        return self.stats
    
    def _fetch_symbol_list(self) -> List[str]:
        """Determine the list of symbols to crawl."""
        print("\n📋 Fetching VN100 symbol list...")
        symbols = self.vnstock.get_vn100_symbols()
        if not symbols:
            print("⚠️  VN100 empty, falling back to all symbols...")
            symbols = self.vnstock.get_all_symbols()
        return symbols
    
    def _process_company(self, symbol: str):
        """Process a single symbol: info + reports + prices.
        Index symbols (VNINDEX, HNXINDEX, etc.) only get price history.
        """
        try:
            is_index = symbol.upper() in INDEX_SYMBOLS
            if not is_index:
                self._crawl_company_info(symbol)
                self._crawl_financial_reports(symbol)
            else:
                print(f"  📊 Index symbol — crawling prices only")
            self._crawl_price_history(symbol)
            self.stats["symbols_with_data"].append(symbol)
        except Exception as e:
            print(f"  ❌ Error: {e}")
            self.stats["errors"] += 1
    
    def _crawl_company_info(self, symbol: str):
        """Crawl company information."""
        if symbol.upper() in INDEX_SYMBOLS:
            print("  ⚠️ Index symbol — skipping company info")
            return
        print(f"  📄 Company info...", end=" ")
        info = self.vnstock.get_company_info_complete(symbol)
        
        if not info:
            print("⚠️  no data")
            self.stats["skipped"] += 1
            return
        
        # Save locally
        self._save_json(f"company_{symbol}.json", info)
        
        # Save to Supabase
        if self.storage.is_connected():
            self.storage.upsert_company(info)
        
        self.stats["companies"] += 1
        print("✅")
    
    def _crawl_financial_reports(self, symbol: str):
        """Crawl all financial reports."""
        if symbol.upper() in INDEX_SYMBOLS:
            print("  ⚠️ Index symbol — skipping financial reports")
            return
        print(f"  📊 Financial reports...")
        financials = self.vnstock.get_all_financials(symbol)
        
        # Flatten all report types
        all_records = []
        for rtype, records in financials.items():
            all_records.extend(records)
        
        if all_records:
            self._save_json(f"financial_{symbol}.json", all_records)
            
            if self.storage.is_connected():
                self.storage.upsert_financial_reports_batch(all_records)
        
        self.stats["financial_reports"] += len(all_records)
        print(f"  ✅ {len(all_records)} records")
    
    def _crawl_price_history(self, symbol: str):
        """Crawl price history."""
        print(f"  💹 Prices...", end=" ")
        
        latest_date = None
        if self.storage.is_connected():
            latest_date = self.storage.get_latest_price_date(symbol)
        
        prices = self.vnstock.get_price_history(symbol, start=latest_date)
        
        if not prices:
            print("⚠️  empty")
            return
        
        self._save_json(f"price_{symbol}.json", prices, merge=True)
        
        if self.storage.is_connected():
            self.storage.upsert_price_data(prices)
        
        self.stats["price_records"] += len(prices)
        print(f"✅ {len(prices)} records")
    
    # ──────────────────────────────────────────────
    # Local file helpers (backup when no Supabase)
    # ──────────────────────────────────────────────
    
    def _save_json(self, filename: str, data, merge: bool = False):
        """Save data to local JSON file as backup.
        
        Args:
            filename: Output filename
            data: New data to save
            merge: If True, merge with existing file (for price data).
                   If False, overwrite (for company info, financials)
        """
        path = os.path.join(self.data_dir, filename)
        try:
            if merge and os.path.exists(path):
                with open(path) as f:
                    existing = json.load(f)
                # Merge by date, deduplicate
                existing_dates = {r.get("date") for r in existing}
                new_items = [r for r in data if r.get("date") not in existing_dates]
                combined = existing + new_items
                combined.sort(key=lambda r: r.get("date", ""))
                with open(path, 'w') as f:
                    json.dump(combined, f, indent=2, default=str)
            else:
                with open(path, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
        except Exception as e:
            print(f"    ⚠️  Failed to save {filename}: {e}")
    
    def _save_symbols(self, symbols: List[str]):
        """Save the full symbol list for reference."""
        self._save_json("vn100_symbols.json", {
            "count": len(symbols),
            "symbols": symbols,
            "fetched_at": datetime.now().isoformat(),
        })
    
    def _save_summary(self):
        """Save crawl summary."""
        self._save_json("crawl_summary.json", {
            **self.stats,
            "finished_at": datetime.now().isoformat(),
        })


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="AIFIA Crawler Pipeline")
    parser.add_argument("--symbols", nargs="+", help="Specific symbols to crawl")
    parser.add_argument("--batch", type=int, default=5, help="Batch size")
    
    args = parser.parse_args()
    
    config = CrawlerConfig(batch_size=args.batch)
    pipeline = CrawlPipeline(config)
    pipeline.run(symbols=args.symbols)
