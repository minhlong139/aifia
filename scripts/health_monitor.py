#!/usr/bin/env python3
"""AIFIA Health Monitor — Standalone health check with Telegram alert capability.

Checks:
  1. Data freshness: latest date for all tables
  2. Data completeness: record counts vs baseline
  3. Kronos prediction freshness
  4. Dependency health: venv, kronos_repo, Supabase connectivity

Outputs JSON for programmatic use or human-readable for Telegram.
"""
import os
import sys
import json
import urllib.request
from datetime import datetime, date, timedelta

AIFIA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(AIFIA_DIR, "data")

CHECK_RESULTS = {
    "checked_at": datetime.now().isoformat(),
    "status": "OK",
    "checks": [],
}


def load_env():
    """Load Supabase credentials from .env."""
    env_file = os.path.join(AIFIA_DIR, ".env")
    if not os.path.exists(env_file):
        return
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def add_check(name: str, status: str, detail: str = ""):
    CHECK_RESULTS["checks"].append({
        "name": name,
        "status": status,
        "detail": detail,
    })
    if status != "OK":
        CHECK_RESULTS["status"] = "WARN"


def check_venv():
    python = os.path.join(AIFIA_DIR, ".venv", "bin", "python")
    if os.path.isfile(python):
        add_check("Python venv", "OK", f"Found at .venv")
        return python
    add_check("Python venv", "FAIL", "venv not found")
    return None


def check_kronos_repo():
    kronos_paths = [
        os.path.join(AIFIA_DIR, "kronos_repo", "model", "__init__.py"),
        "/tmp/kronos_repo/model/__init__.py",
    ]
    for p in kronos_paths:
        if os.path.isfile(p):
            add_check("Kronos repo", "OK", f"Found at {os.path.dirname(os.path.dirname(p))}")
            return True
    add_check("Kronos repo", "FAIL", "Not found — predictions will fail")
    return False


def check_supabase():
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        add_check("Supabase config", "FAIL", "SUPABASE_URL or key missing")
        return False

    try:
        req = urllib.request.Request(f"{url}/rest/v1/price_history?select=count")
        req.add_header("apikey", key)
        req.add_header("Authorization", f"Bearer {key}")
        req.add_header("Prefer", "count=exact")
        with urllib.request.urlopen(req, timeout=10) as resp:
            cr = resp.headers.get("content-range", "0/0")
            total = cr.split("/")[-1] if "/" in cr else "?"
            add_check("Supabase API", "OK", f"Connected, {total} price records")
            return True
    except Exception as e:
        add_check("Supabase API", "FAIL", str(e)[:80])
        return False


def check_price_freshness(canary_symbols=None):
    if canary_symbols is None:
        canary_symbols = ["FPT", "VCB", "HPG", "VIC", "VNM"]

    today = date.today()
    stale_count = 0
    empty_count = 0

    for sym in canary_symbols:
        fpath = os.path.join(DATA_DIR, f"price_{sym}.json")
        if not os.path.isfile(fpath):
            empty_count += 1
            continue

        try:
            with open(fpath) as f:
                records = json.load(f)
            if not records:
                empty_count += 1
                continue

            dates = [r.get("date", "") for r in records if r.get("date")]
            latest = max(dates) if dates else "N/A"
            days_stale = (today - date.fromisoformat(latest)).days if latest != "N/A" else 999

            if days_stale > 3:
                stale_count += 1
        except Exception:
            empty_count += 1

    if empty_count > 0:
        add_check("Price data files", "FAIL", f"{empty_count} canary files empty/missing")
    elif stale_count > 0:
        add_check("Price freshness", "WARN", f"{stale_count}/{len(canary_symbols)} canaries stale >3 days")
    else:
        add_check("Price freshness", "OK", f"All {len(canary_symbols)} canaries fresh")


def check_price_record_counts():
    """Verify local price files have reasonable record counts."""
    threshold = 100  # minimum expected records
    low_count = 0
    total_symbols = 0

    for fname in os.listdir(DATA_DIR):
        if not fname.startswith("price_") or not fname.endswith(".json"):
            continue
        if "VNINDEX" in fname:
            continue
        total_symbols += 1
        try:
            with open(os.path.join(DATA_DIR, fname)) as f:
                records = json.load(f)
            if len(records) < threshold:
                low_count += 1
        except Exception:
            low_count += 1

    if low_count > 0:
        add_check("Price record counts", "FAIL",
                  f"{low_count}/{total_symbols} symbols have <{threshold} records")
    else:
        add_check("Price record counts", "OK",
                  f"All {total_symbols} symbols have ≥{threshold} records")


def check_kronos_freshness():
    pred_dir = os.path.join(DATA_DIR, "predictions")
    if not os.path.isdir(pred_dir):
        add_check("Kronos predictions", "WARN", "predictions dir not found")
        return

    files = sorted(
        [f for f in os.listdir(pred_dir) if f.startswith("kronos_vn100_") and f.endswith(".json")],
        reverse=True,
    )
    if not files:
        add_check("Kronos predictions", "WARN", "No prediction files found")
        return

    latest_file = files[0]
    # Parse date from filename: kronos_vn100_YYYYMMDD_HHMMSS.json
    try:
        date_str = latest_file.replace("kronos_vn100_", "").split("_")[0]
        file_date = date.fromisoformat(f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}")
        days_stale = (date.today() - file_date).days
    except Exception:
        days_stale = 999

    # Also check content
    full_path = os.path.join(pred_dir, latest_file)
    try:
        with open(full_path) as f:
            data = json.load(f)
        results = data.get("results", [])
        detail = f"{latest_file}: {len(results)} symbols predicted"
    except Exception:
        detail = f"{latest_file}: unreadable"

    if days_stale > 3:
        add_check("Kronos freshness", "WARN", f"{days_stale}d stale — {detail}")
    else:
        add_check("Kronos freshness", "OK", f"{detail}")


def check_disk_space():
    import shutil
    usage = shutil.disk_usage(DATA_DIR)
    free_gb = usage.free / (1024 ** 3)
    if free_gb < 1:
        add_check("Disk space", "WARN", f"{free_gb:.1f}GB free")
    else:
        add_check("Disk space", "OK", f"{free_gb:.1f}GB free")


def format_telegram_report() -> str:
    """Format check results as Telegram message."""
    lines = ["🩺 **AIFIA Health Check**", f"⏰ {datetime.now().strftime('%H:%M %d/%m/%Y')}", ""]

    # Group checks by status
    fails = [c for c in CHECK_RESULTS["checks"] if c["status"] == "FAIL"]
    warns = [c for c in CHECK_RESULTS["checks"] if c["status"] == "WARN"]
    oks = [c for c in CHECK_RESULTS["checks"] if c["status"] == "OK"]

    if fails:
        lines.append("❌ **FAILURES:**")
        for c in fails:
            lines.append(f"  • {c['name']}: {c['detail']}")
        lines.append("")

    if warns:
        lines.append("⚠️ **WARNINGS:**")
        for c in warns:
            lines.append(f"  • {c['name']}: {c['detail']}")
        lines.append("")

    lines.append(f"✅ {len(oks)} checks OK")

    overall = "🟢 HEALTHY" if not fails else "🔴 UNHEALTHY"
    lines.insert(2, f"Status: {overall}")
    lines.append(f"\n🔄 Kiểm tra lúc: {CHECK_RESULTS['checked_at'][:19]}")

    return "\n".join(lines)


def main():
    load_env()

    check_venv()
    check_kronos_repo()
    check_supabase()
    check_price_freshness()
    check_price_record_counts()
    check_kronos_freshness()
    check_disk_space()

    if "--json" in sys.argv:
        print(json.dumps(CHECK_RESULTS, indent=2, ensure_ascii=False))
    else:
        print(format_telegram_report())

    # Exit code for cron monitoring
    if CHECK_RESULTS["status"] != "OK":
        sys.exit(1)


if __name__ == "__main__":
    main()
