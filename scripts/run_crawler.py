#!/usr/bin/env python3
"""AIFIA Crawler - Entry point for running the crawl pipeline."""
import os
import sys
import argparse
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawler.config import CrawlerConfig
from crawler.pipeline import CrawlPipeline


def main():
    parser = argparse.ArgumentParser(description="AIFIA Data Crawler")
    parser.add_argument("--symbols", nargs="+", help="Specific symbols to crawl (default: VN100)")
    parser.add_argument("--batch-size", type=int, default=10, help="Companies per batch")
    parser.add_argument("--years", type=int, default=5, help="Years of financial data")
    parser.add_argument("--dry-run", action="store_true", help="Print without storing to Supabase")
    
    args = parser.parse_args()
    
    config = CrawlerConfig(
        batch_size=args.batch_size,
        financial_years_back=args.years,
    )
    
    pipeline = CrawlPipeline(config)
    
    if args.symbols:
        pipeline.run(symbols=args.symbols)
    else:
        pipeline.run()


if __name__ == "__main__":
    main()
