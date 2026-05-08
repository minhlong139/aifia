#!/usr/bin/env python3
"""Import crawled JSON data into Supabase.
Run after Supabase credentials are configured."""
import os
import sys
import json
import glob
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawler.config import CrawlerConfig
from crawler.storage import SupabaseStorage


def main():
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    
    config = CrawlerConfig()
    storage = SupabaseStorage(config)
    
    if not storage.is_connected():
        print("❌ Supabase not configured. Set SUPABASE_URL and SUPABASE_SERVICE_KEY")
        print("  Example:")
        print("  export SUPABASE_URL=https://your-project.supabase.co")
        print("  export SUPABASE_SERVICE_KEY=your-service-role-key")
        sys.exit(1)
    
    print("✅ Supabase connected\n")
    
    # 1. Import companies
    print("📦 Importing companies...")
    company_files = sorted(glob.glob(os.path.join(data_dir, "company_*.json")))
    for f in company_files:
        with open(f) as fh:
            data = json.load(fh)
        symbol = data.get("symbol", "?")
        try:
            storage.upsert_company(data)
            print(f"  ✅ {symbol}")
        except Exception as e:
            print(f"  ❌ {symbol}: {e}")
    
    # 2. Import financial reports
    print("\n📦 Importing financial reports...")
    report_files = sorted(glob.glob(os.path.join(data_dir, "financial_*.json")))
    for f in report_files:
        with open(f) as fh:
            records = json.load(fh)
        if not records:
            continue
        symbol = records[0].get("symbol", "?")
        try:
            storage.upsert_financial_reports_batch(records)
            print(f"  ✅ {symbol}: {len(records)} records")
        except Exception as e:
            print(f"  ❌ {symbol}: {e}")
    
    # 3. Import price history
    print("\n📦 Importing price history...")
    price_files = sorted(glob.glob(os.path.join(data_dir, "price_*.json")))
    for f in price_files:
        with open(f) as fh:
            records = json.load(fh)
        if not records:
            continue
        symbol = records[0].get("symbol", "?")
        try:
            storage.upsert_price_data(records)
            print(f"  ✅ {symbol}: {len(records)} records")
        except Exception as e:
            print(f"  ❌ {symbol}: {e}")
    
    print("\n🎉 Import complete!")


if __name__ == "__main__":
    main()
