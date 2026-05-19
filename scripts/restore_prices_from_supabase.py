#!/usr/bin/env python3
"""Restore local price_*.json files from Supabase after data loss.

The backfill script overwrote local price files with only the backfilled days.
Supabase still has the full history. This script pulls all data back.
"""
import os
import sys
import json
import urllib.request
import time

AIFIA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(AIFIA_DIR, "data")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://oqpplmqykuwhwfbcjmxs.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

if not SUPABASE_KEY:
    # Try loading from .env
    env_file = os.path.join(AIFIA_DIR, ".env")
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line.startswith("SUPABASE_SERVICE_KEY="):
                    SUPABASE_KEY = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break

if not SUPABASE_KEY:
    print("❌ SUPABASE_SERVICE_KEY not found")
    sys.exit(1)


def supabase_request(path: str):
    """Make a Supabase REST API request."""
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    req = urllib.request.Request(url)
    req.add_header("apikey", SUPABASE_KEY)
    req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def restore_symbol(symbol: str) -> int:
    """Restore one symbol's price data from Supabase."""
    out_path = os.path.join(DATA_DIR, f"price_{symbol}.json")
    
    # Get total count
    count_url = f"price_history?symbol=eq.{symbol}&select=count"
    req = urllib.request.Request(f"{SUPABASE_URL}/rest/v1/{count_url}")
    req.add_header("apikey", SUPABASE_KEY)
    req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
    req.add_header("Prefer", "count=exact")
    
    try:
        with urllib.request.urlopen(req) as resp:
            content_range = resp.headers.get("content-range", "")
            total = 0
            if "/" in content_range:
                total = int(content_range.split("/")[-1])
    except Exception:
        total = 0
    
    if total == 0:
        print(f"  ⚠️  {symbol}: 0 records in Supabase")
        return 0
    
    # Fetch all records in pages
    all_records = []
    offset = 0
    page_size = 1000
    
    while offset < total:
        page_url = f"price_history?symbol=eq.{symbol}&order=date.asc&limit={page_size}&offset={offset}"
        page = supabase_request(page_url)
        
        if not page:
            break
        
        for r in page:
            all_records.append({
                "symbol": r["symbol"],
                "date": r["date"],
                "open": float(r["open"]),
                "high": float(r["high"]),
                "low": float(r["low"]),
                "close": float(r["close"]),
                "volume": int(r.get("volume", 0)),
                "source": "supabase_restore",
                "ingested_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            })
        
        offset += page_size
    
    # Save to file
    with open(out_path, "w") as f:
        json.dump(all_records, f, indent=2, default=str)
    
    return len(all_records)


def main():
    print("🔄 Restoring price data from Supabase...\n")
    
    # Get all symbols from existing price files
    price_files = sorted(
        f for f in os.listdir(DATA_DIR)
        if f.startswith("price_") and f.endswith(".json") and f != "price_VNINDEX.json"
    )
    
    symbols = [f.replace("price_", "").replace(".json", "") for f in price_files]
    print(f"📋 {len(symbols)} symbols to restore\n")
    
    total_records = 0
    failed = []
    
    for i, symbol in enumerate(symbols, 1):
        print(f"[{i:>3}/{len(symbols)}] {symbol:>5}...", end=" ", flush=True)
        try:
            count = restore_symbol(symbol)
            total_records += count
            print(f"✅ {count} records")
        except Exception as e:
            print(f"❌ {e}")
            failed.append(symbol)
    
    print(f"\n{'='*50}")
    print(f"✅ Restored {total_records} total records across {len(symbols) - len(failed)} symbols")
    if failed:
        print(f"❌ Failed: {failed}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
