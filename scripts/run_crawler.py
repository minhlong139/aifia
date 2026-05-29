#!/usr/bin/env python3
"""AIFIA Crawler - Entry point for running the crawl pipeline.

Chạy độc lập qua OS cronjob (không phụ thuộc OpenClaw).
"""
import os
import sys
import argparse
from datetime import datetime, date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawler.config import CrawlerConfig
from crawler.pipeline import CrawlPipeline, INDEX_SYMBOLS

MARKET_INDEX_SYMBOLS = ["VNINDEX"]


def load_symbol_list(data_dir: str) -> list:
    """Load symbol list from saved JSON or return VN100."""
    import json
    path = os.path.join(data_dir, "vn100_symbols.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f).get("symbols", [])
    return []  # fallback: pipeline will fetch


def main():
    parser = argparse.ArgumentParser(description="AIFIA Data Crawler")
    parser.add_argument("--symbols", nargs="+", 
                        help="Specific symbols (default: VN100 from saved list or API)")
    parser.add_argument("--batch-size", type=int, default=10, 
                        help="Companies per batch")
    parser.add_argument("--years", type=int, default=5,
                        help="Years of financial data to fetch")
    
    # Mode flags ───────────────────────────────────
    parser.add_argument("--incremental", action="store_true",
                        help="Chỉ crawl dữ liệu mới (giá: từ ngày gần nhất trong DB)")
    parser.add_argument("--price-only", action="store_true",
                        help="Chỉ crawl giá (OHLCV), bỏ qua company info & financial")
    parser.add_argument("--financial-only", action="store_true",
                        help="Chỉ crawl báo cáo tài chính, bỏ qua giá & company")
    parser.add_argument("--intraday", action="store_true",
                        help="Chỉ crawl VN30 intraday snapshot")
    parser.add_argument("--dry-run", action="store_true",
                        help="In ra log nhưng không ghi vào Supabase")
    
    args = parser.parse_args()
    
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    
    config = CrawlerConfig(
        batch_size=args.batch_size,
        financial_years_back=args.years,
    )
    
    pipeline = CrawlPipeline(config)
    
    # Xác định symbol list ──────────────────────
    symbols = args.symbols
    if symbols and symbols[0].upper() == "ALL":
        symbols = load_symbol_list(data_dir) or pipeline._fetch_symbol_list()
    elif not symbols:
        symbols = pipeline._fetch_symbol_list()
    
    if not symbols:
        print("❌ No symbols to crawl. Run a full crawl first to generate symbol list.")
        sys.exit(1)
    
    print(f"📋 Processing {len(symbols)} symbols: {symbols[:5]}...{symbols[-3:]}" if len(symbols) > 8 else f"📋 Processing {len(symbols)} symbols: {symbols}")
    
    # Chế độ chạy ──────────────────────────────
    # Ensure market indices (VNINDEX, etc.) are always crawled for prices
    for index_sym in MARKET_INDEX_SYMBOLS:
        if index_sym not in symbols:
            symbols.append(index_sym)
            print(f"📌 Added market index: {index_sym}")

    if args.intraday:
        print("⏱️  INTRADAY MODE — VN30 snapshot")
        # Intraday: chỉ crawl VN30 hoặc top nhóm
        # Hiện tại vnstock có hỗ trợ intraday quote? Chưa có — để placeholder
        print("   ⚠️  Intraday chưa có nguồn dữ liệu realtime. Bỏ qua.")
        return
    
    if args.financial_only:
        print("📊 FINANCIAL-ONLY MODE")
        for i, sym in enumerate(symbols, 1):
            if sym.upper() in INDEX_SYMBOLS:
                print(f"\n[{i}/{len(symbols)}] {sym} is a market index. Skipping.")
                continue
            print(f"\n[{i}/{len(symbols)}] {sym}...")
            pipeline._crawl_financial_reports(sym)
        print(f"\n✅ Done. {pipeline.stats['financial_reports']} records crawled.")
        return
    
    if args.price_only:
        print("💹 PRICE-ONLY MODE" + (" (incremental)" if args.incremental else ""))
        for i, sym in enumerate(symbols, 1):
            print(f"\n[{i}/{len(symbols)}] {sym}...")
            pipeline._crawl_price_history(sym)
        print(f"\n✅ Done. {pipeline.stats['price_records']} records crawled.")
        return
    
    # Full crawl ────────────────────────────────
    pipeline.run(symbols=symbols)


if __name__ == "__main__":
    main()
