#!/usr/bin/env python3
"""Upload latest Kronos predictions from local JSON to Supabase."""
import os
import sys
import json
import glob
import urllib.request
from datetime import datetime

AIFIA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(AIFIA_DIR, "data")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    env_file = os.path.join(AIFIA_DIR, ".env")
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line.startswith("SUPABASE_URL="):
                    SUPABASE_URL = line.split("=", 1)[1].strip().strip('"').strip("'")
                elif line.startswith("SUPABASE_SERVICE_KEY="):
                    SUPABASE_KEY = line.split("=", 1)[1].strip().strip('"').strip("'")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Supabase not configured")
    sys.exit(1)


def find_latest_prediction():
    """Find the most recent Kronos prediction JSON file."""
    pred_dir = os.path.join(DATA_DIR, "predictions")
    files = sorted(glob.glob(os.path.join(pred_dir, "kronos_vn100_*.json")), reverse=True)
    if not files:
        print("❌ No prediction files found")
        return None
    return files[0]


def delete_today_predictions():
    """Delete all predictions for today to avoid duplicates."""
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"{SUPABASE_URL}/rest/v1/kronos_predictions?prediction_date=eq.{today}"
    req = urllib.request.Request(url, method="DELETE")
    req.add_header("apikey", SUPABASE_KEY)
    req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
    try:
        with urllib.request.urlopen(req) as resp:
            resp.read()
        return True
    except Exception as e:
        print(f"  ⚠️  Delete old predictions error: {e}")
        return False


def upload_prediction(pred: dict):
    """Upload a single Kronos prediction to Supabase."""
    url = f"{SUPABASE_URL}/rest/v1/kronos_predictions"
    
    # Build the insert row matching the table schema
    row = {
        "symbol": pred["symbol"],
        "prediction_date": datetime.now().strftime("%Y-%m-%d"),
        "predicted_ohlcv": pred.get("ohclv_snapshot", []),
        "metrics": {
            "current_price": pred.get("current_price"),
            "predicted_price": pred.get("predicted_price"),
            "change_pct": pred.get("change_pct"),
            "upside_prob": pred.get("upside_prob"),
            "volatility": pred.get("volatility"),
            "signal": pred.get("signal"),
            "predicted_high": pred.get("predicted_high"),
            "predicted_low": pred.get("predicted_low"),
            "prediction_periods": pred.get("prediction_periods"),
        },
        "model_version": "NeoQuasar/Kronos-small",
        "created_at": datetime.now().isoformat(),
    }
    
    # Upsert: use plain insert (no merge-duplicates)
    req = urllib.request.Request(url, method="POST")
    req.add_header("apikey", SUPABASE_KEY)
    req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
    req.add_header("Content-Type", "application/json")
    
    data = json.dumps(row).encode()
    req.data = data
    
    try:
        with urllib.request.urlopen(req) as resp:
            resp.read()
        return True
    except Exception as e:
        print(f"  ❌ Upload error for {pred['symbol']}: {e}")
        return False


def main():
    print("📤 Uploading Kronos predictions to Supabase...\n")
    
    latest_file = find_latest_prediction()
    if not latest_file:
        return
    
    print(f"📁 Source: {os.path.basename(latest_file)}")
    
    with open(latest_file) as f:
        data = json.load(f)
    
    results = data.get("results", [])
    print(f"📊 {len(results)} predictions to upload\n")
    
    # Delete old today predictions first
    delete_today_predictions()
    
    success = 0
    failed = 0
    
    for i, pred in enumerate(results, 1):
        symbol = pred.get("symbol", "?")
        print(f"[{i:>3}/{len(results)}] {symbol:>5}...", end=" ", flush=True)
        
        if upload_prediction(pred):
            success += 1
            print(f"✅ ${pred.get('current_price', 0):.2f} → ${pred.get('predicted_price', 0):.2f} "
                  f"({pred.get('change_pct', 0):+.2f}%) {pred.get('signal', '?')}")
        else:
            failed += 1
    
    print(f"\n{'='*50}")
    print(f"✅ {success} uploaded, ❌ {failed} failed")
    print(f"🔄 Uploaded at: {datetime.now().isoformat()}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
