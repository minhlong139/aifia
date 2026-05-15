#!/usr/bin/env python3
"""Upload price data from local JSON to Supabase.
Chạy sau mỗi lần crawl daily_price để đồng bộ lên Supabase.

Usage:
    python scripts/upload_prices.py                  # Upload all prices
    python scripts/upload_prices.py --incremental    # Chỉ upload ngày mới nhất
"""
import os
import sys
import json
import glob
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawler.config import CrawlerConfig
from crawler.storage import SupabaseStorage


def get_latest_date_from_records(records):
    """Find the latest date in a list of price records."""
    dates = [r.get("date") for r in records if r.get("date")]
    return max(dates) if dates else None


def main():
    incremental = "--incremental" in sys.argv

    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

    config = CrawlerConfig()
    storage = SupabaseStorage(config)

    if not storage.is_connected():
        print("❌ Supabase not configured. Set SUPABASE_URL and SUPABASE_SERVICE_KEY")
        sys.exit(1)

    print(f"✅ Supabase connected (incremental={incremental})\n")

    total_uploaded = 0
    price_files = sorted(glob.glob(os.path.join(data_dir, "price_*.json")))

    if not price_files:
        print("⚠️  No price_*.json files found.")
        return

    if incremental:
        print("📅 Incremental upload: checking latest date per symbol")

    for f in price_files:
        with open(f) as fh:
            records = json.load(fh)
        if not records:
            continue

        symbol = records[0].get("symbol", "?")
        cutoff_date = storage.get_latest_price_date(symbol) if incremental else None

        if incremental and cutoff_date:
            new_records = [r for r in records if r.get("date", "") > cutoff_date]
        else:
            new_records = records

        if not new_records:
            print(f"  ⏭️  {symbol}: 0 new records (up to date)")
            continue

        try:
            storage.upsert_price_data(new_records)
            print(f"  ✅ {symbol}: {len(new_records)} records uploaded")
            total_uploaded += len(new_records)
        except Exception as e:
            print(f"  ❌ {symbol}: {e}")

    print(f"\n🎉 Done! {total_uploaded} records uploaded to Supabase.")


if __name__ == "__main__":
    main()
