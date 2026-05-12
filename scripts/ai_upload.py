#!/usr/bin/env python3
"""
Merge AI-enhanced batches & upload to Supabase.
Called after sub-agents finish AI analysis.

Usage:
    python scripts/ai_upload.py --date YYYY-MM-DD
    python scripts/ai_upload.py --date-latest
"""
import os, sys, json, glob
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                k, _, v = line.partition("=")
                os.environ[k.strip()] = v.strip()

from crawler.storage import SupabaseStorage
from crawler.config import CrawlerConfig

HISTORY_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "history")


def load_ai_enhancements(day: str) -> dict:
    """Load all ai_batch files for a given date, merge by symbol."""
    day_dir = os.path.join(HISTORY_DIR, day)
    if not os.path.isdir(day_dir):
        print(f"❌ No data dir: {day_dir}")
        return {}

    merged = {}
    for fpath in sorted(glob.glob(os.path.join(day_dir, "ai_batch_*.json"))):
        with open(fpath) as f:
            data = json.load(f)
        for item in data.get("enhanced_analyses", []):
            sym = item.get("symbol")
            if sym:
                merged[sym] = item
        print(f"  📖 {os.path.basename(fpath)}: {len(data.get('enhanced_analyses',[]))} stocks")

    return merged


def load_batch_data(day: str) -> dict:
    """Load original batch data for metrics."""
    day_dir = os.path.join(HISTORY_DIR, day)
    merged = {}
    for fpath in sorted(glob.glob(os.path.join(day_dir, "batch_*.json"))):
        with open(fpath) as f:
            data = json.load(f)
        for stock in data.get("stocks", []):
            merged[stock["symbol"]] = stock
    return merged


def upload(day: str, ai_data: dict, batch_data: dict):
    """Upload merged analysis to Supabase."""
    config = CrawlerConfig()
    storage = SupabaseStorage(config)
    if not storage.is_connected():
        print("❌ Supabase not connected")
        return

    saved = 0
    for sym, ai in ai_data.items():
        bd = batch_data.get(sym, {})
        m = bd.get("metrics", {})

        # Build enhanced analysis
        result = {
            "score": bd.get("score", 0),
            "verdict": bd.get("verdict"),
            "metrics": m,
            "anomalies": bd.get("anomalies", []),
            "ai_commentary": ai.get("ai_commentary", ""),
            "strengths": ai.get("strengths", []),
            "weaknesses": ai.get("weaknesses", []),
            "outlook": ai.get("outlook", ""),
            "key_risks": ai.get("key_risks", []),
            "report_date": day,
            "model_version": "aifia_v2_ai_enhanced",
        }

        summary = f"Mã {sym} — Điểm {bd.get('score',0)}/100 ({bd.get('verdict','')}). {ai.get('ai_commentary','')[:300]}"

        try:
            storage.client.table("analysis_results").insert({
                "symbol": sym,
                "analysis_type": "full_report",
                "result": json.dumps(result),
                "summary": summary,
                "score": bd.get("score", 0),
                "recommendations": _gen_recs(bd, ai),
                "model_version": "aifia_v2_ai_enhanced",
                "metadata": json.dumps({
                    "report_date": day,
                    "industry": bd.get("industry"),
                    "price": m.get("price"),
                    "has_ai": True,
                }),
            }).execute()
            saved += 1
        except Exception as e:
            print(f"  ❌ {sym}: {e}")

    print(f"\n✅ Uploaded {saved}/{len(ai_data)} enhanced analyses to Supabase")


def _gen_recs(bd: dict, ai: dict) -> list:
    recs = []
    for an in bd.get("anomalies", []):
        if an["severity"] == "high":
            recs.append(f"⚠️ {an['description']}")
    m = bd.get("metrics", {})
    if m.get("de_ratio") and m["de_ratio"] > 100:
        recs.append("Giám sát đòn bẩy tài chính")
    s = ai.get("strengths", [])
    w = ai.get("weaknesses", [])
    if len(w) > len(s):
        recs.append("Xem xét rủi ro nhiều hơn cơ hội")
    return recs or ["Tiếp tục theo dõi"]


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="Date YYYY-MM-DD")
    parser.add_argument("--date-latest", action="store_true", help="Use latest date dir")
    args = parser.parse_args()

    if args.date_latest:
        dirs = sorted([d for d in os.listdir(HISTORY_DIR) if len(d) == 10 and d[4] == "-"])
        day = dirs[-1] if dirs else date.today().isoformat()
    elif args.date:
        day = args.date
    else:
        day = date.today().isoformat()

    print(f"📅 Merge & Upload for {day}")
    ai = load_ai_enhancements(day)
    bd = load_batch_data(day)
    print(f"   AI-enhanced: {len(ai)} stocks | Batch data: {len(bd)} stocks")
    if ai:
        upload(day, ai, bd)
    else:
        print("   ⚠️ No AI enhancement files found")
