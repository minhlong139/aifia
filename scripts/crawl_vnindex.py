#!/usr/bin/env python3
"""AIFIA - Crawl VNINDEX price data for the homepage chart.

Chạy độc lập để đồng bộ dữ liệu VNINDEX từ Vnstock vào Supabase.
Dùng cron job hoặc chạy sau mỗi phiên giao dịch.

Usage:
    python scripts/crawl_vnindex.py                  # Full crawl từ 2018
    python scripts/crawl_vnindex.py --incremental    # Chỉ crawl ngày mới
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawler.config import CrawlerConfig
from crawler.pipeline import CrawlPipeline

INDEX_SYMBOL = "VNINDEX"


def main():
    incremental = "--incremental" in sys.argv

    config = CrawlerConfig()
    pipeline = CrawlPipeline(config)

    if incremental:
        print(f"📅 Incremental mode: skipping dates already in DB for {INDEX_SYMBOL}")

    print(f"\n📊 Crawling {INDEX_SYMBOL} price history...")
    pipeline._crawl_price_history(INDEX_SYMBOL)

    total = pipeline.stats.get("price_records", 0)
    print(f"\n✅ Done. {total} price records for {INDEX_SYMBOL}.")

    # Verify Supabase has the data
    if pipeline.storage.is_connected():
        latest = pipeline.storage.get_latest_price_date(INDEX_SYMBOL)
        print(f"📅 Latest date in DB: {latest}")
    else:
        print("⚠️  Supabase not connected — data saved locally only")


if __name__ == "__main__":
    main()
