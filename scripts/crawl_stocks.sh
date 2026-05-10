#!/usr/bin/env bash
# ===========================================================================
# AIFIA Crawl Controller — chạy độc lập qua OS cron, KHÔNG phụ thuộc OpenClaw
# ===========================================================================
# Usage:
#   ./scripts/crawl_stocks.sh daily_price          # Price update sau mỗi phiên
#   ./scripts/crawl_stocks.sh intraday             # Intraday (option, cần nguồn realtime)
#   ./scripts/crawl_stocks.sh weekly_financial     # Financial + company info (cuối tuần)
#   ./scripts/crawl_stocks.sh full_vn100           # Full crawl toàn bộ VN100 (1 lần/ tháng)
#   ./scripts/crawl_stocks.sh kronos_prediction    # Chạy Kronos dự báo (sau daily_price)
#   ./scripts/crawl_stocks.sh check_health         # Kiểm tra token/supabase
# ===========================================================================

set -euo pipefail

AIFIA_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="$AIFIA_DIR/.venv/bin/python"
SCRIPTS="$AIFIA_DIR/scripts"
LOG_DIR="$AIFIA_DIR/logs"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

mkdir -p "$LOG_DIR"

log() {
    echo "[$TIMESTAMP] $*" >> "$LOG_DIR/crawl_$(date +%Y%m%d).log"
    echo "[$TIMESTAMP] $*"
}

run_script() {
    local name="$1"
    shift
    log "▶ Starting: $name"
    cd "$AIFIA_DIR"
    
    if "$PYTHON" "$@" >> "$LOG_DIR/${name}_$(date +%Y%m%d).log" 2>&1; then
        log "✅ Completed: $name"
    else
        local exit_code=$?
        log "❌ FAILED: $name (exit=$exit_code) — see $LOG_DIR/${name}_$(date +%Y%m%d).log"
        return $exit_code
    fi
}

# ──────────────────────────────────────────────────────────────────────────
# Các task crawl
# ──────────────────────────────────────────────────────────────────────────

daily_price() {
    log "📊 [DAILY] Incremental price update — chỉ crawl ngày mới nhất"
    run_script "daily_price" "$SCRIPTS/run_crawler.py" \
        --symbols ALL \
        --incremental \
        --price-only
}

weekly_financial() {
    log "📋 [WEEKLY] Financial reports + company info refresh"
    run_script "weekly_financial" "$SCRIPTS/run_crawler.py" \
        --symbols ALL \
        --financial-only \
        --years 2
}

full_vn100() {
    log "🔄 [FULL] Full crawl toàn bộ VN100 (price + financial + company)"
    run_script "full_vn100" "$SCRIPTS/run_crawler.py" \
        --symbols ALL \
        --years 5
}

kronos_prediction() {
    log "🔮 [DAILY] Kronos prediction cho tất cả VN100"
    run_script "kronos_pred" "$SCRIPTS/run_kronos_all.py"
}

intraday() {
    log "⏱️ [INTRADAY] Snapshot giá intraday"
    run_script "intraday" "$SCRIPTS/run_crawler.py" \
        --symbols VN30 \
        --intraday
}

check_health() {
    local ok=true
    
    # Check Python venv
    if [ ! -x "$PYTHON" ]; then
        log "❌ Python venv not found at $PYTHON"
        ok=false
    else
        log "✅ Python: $($PYTHON --version 2>&1)"
    fi
    
    # Check Supabase env
    if [ -z "${SUPABASE_URL:-}" ] && [ -z "${SUPABASE_SERVICE_KEY:-}" ]; then
        source "$AIFIA_DIR/.env" 2>/dev/null || true
    fi
    
    if [ -n "${SUPABASE_URL:-}" ]; then
        log "✅ SUPABASE_URL configured"
    else
        log "⚠️  SUPABASE_URL not set — data will only save to local JSON"
    fi
    
    if [ -n "${SUPABASE_SERVICE_KEY:-}" ]; then
        log "✅ SUPABASE_SERVICE_KEY configured"
    else
        log "⚠️  SUPABASE_SERVICE_KEY not set"
    fi
    
    # Check disk space
    local avail=$(df -k "$AIFIA_DIR/data" | tail -1 | awk '{print $4}')
    log "💾 Data dir free: $(numfmt --to=iec $((avail * 1024)) 2>/dev/null || echo "${avail}KB")"
    
    # Check last crawl
    if [ -f "$LOG_DIR/daily_price_$(date +%Y%m%d).log" ]; then
        log "📁 Daily log exists for today"
    fi
    
    $ok
}

# ──────────────────────────────────────────────────────────────────────────
# CLI dispatch
# ──────────────────────────────────────────────────────────────────────────
case "${1:-help}" in
    daily_price)        daily_price ;;
    weekly_financial)   weekly_financial ;;
    full_vn100)         full_vn100 ;;
    kronos_prediction)  kronos_prediction ;;
    intraday)           intraday ;;
    check_health)       check_health ;;
    *)
        echo "Usage: $0 <task>"
        echo ""
        echo "Tasks:"
        echo "  daily_price        [CORE] Cập nhật giá sau phiên (chạy 15:00 T2-T6)"
        echo "  weekly_financial   [CORE] Refresh báo cáo tài chính (chạy cuối tuần)"
        echo "  full_vn100         [BULK] Full crawl toàn bộ VN100 (chạy 1 lần/tháng)"
        echo "  kronos_prediction  [AI]   Dự báo Kronos (chạy sau daily_price)"
        echo "  intraday           [NÂNG CAO] Snapshot giá intraday VN30"
        echo "  check_health       Kiểm tra cấu hình hệ thống"
        ;;
esac
