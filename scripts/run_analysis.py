#!/usr/bin/env python3
"""AIFIA Analysis - Entry point for running the processing pipeline."""
import os
import sys
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from processing.config import ProcessingConfig
from processing.report_generator import ReportGenerator
from crawler.storage import SupabaseStorage
from crawler.config import CrawlerConfig


def main():
    parser = argparse.ArgumentParser(description="AIFIA Analysis Pipeline")
    parser.add_argument("--symbols", nargs="+", required=True, help="Symbols to analyze")
    parser.add_argument("--ai-provider", choices=["openai", "anthropic", "mock"], default="mock")
    parser.add_argument("--with-kronos", action="store_true", help="Enable Kronos predictions")
    parser.add_argument("--save", action="store_true", help="Save results to Supabase")
    
    args = parser.parse_args()
    
    # Config
    proc_config = ProcessingConfig(
        ai_provider=args.ai_provider,
        enable_kronos=args.with_kronos,
    )
    crawl_config = CrawlerConfig()
    
    storage = SupabaseStorage(crawl_config)
    generator = ReportGenerator(proc_config)
    
    # Process each symbol
    for symbol in args.symbols:
        print(f"\n{'='*60}")
        print(f"🔬 Analyzing {symbol}")
        print(f"{'='*60}")
        
        # Get data from Supabase
        financial_data = {}
        price_data = None
        
        if storage.is_connected():
            reports = storage.get_financial_reports(symbol)
            
            # Group by type
            for r in reports:
                rtype = r.get("report_type")
                if rtype not in financial_data:
                    financial_data[rtype] = []
                financial_data[rtype].append(r)
            
            prices = storage.get_price_history(symbol, days=365)
            if prices:
                price_data = prices
        
        if not any(financial_data.values()):
            print(f"  ⚠️  No financial data found for {symbol} in Supabase")
            print(f"  Run crawler first: python scripts/run_crawler.py --symbols {symbol}")
            continue
        
        # Generate report
        report = generator.generate_company_report(
            symbol=symbol,
            financial_data=financial_data,
            price_data=price_data,
        )
        
        # Print summary
        result = report.get("result", {})
        print(f"\n{'─'*60}")
        print(f"📋 Report for {symbol}")
        print(f"{'─'*60}")
        print(f"  Score    : {report.get('score', 0):.1f}/100")
        print(f"  Risk     : {result.get('risk_level', 'N/A')}")
        print(f"  Verdict  : {result.get('verdict', 'N/A')}")
        print(f"  Summary  : {report.get('summary', 'N/A')[:200]}")
        
        if result.get("anomalies"):
            print(f"\n  ⚠️ Anomalies detected:")
            for a in result["anomalies"]:
                print(f"    [{a.get('severity', 'info').upper()}] {a.get('description', '')}")
        
        if report.get("recommendations"):
            print(f"\n  💡 Recommendations:")
            for r in report["recommendations"]:
                print(f"    • {r}")
        
        # Save to Supabase
        if args.save and storage.is_connected():
            storage.upsert_analysis(report)
            print(f"\n  ✅ Report saved to Supabase")
        
        print(f"{'─'*60}\n")


if __name__ == "__main__":
    main()
