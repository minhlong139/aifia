#!/usr/bin/env bash
# ===========================================================================
# AIFIA Crawl Controller v2 — chạy độc lập qua OS cron
# 
# Cải tiến v2 (19/05/2026):
#   - Pre-flight check trước mỗi job (dependency, data readiness)
#   - Post-run validation (kiểm tra output thực tế, không chỉ exit code)
#   - Self-healing: auto clone Kronos nếu thiếu
#   - Health monitor tích hợp với Telegram alert
#   - Timestamp "Cập nhật lúc" hiển thị rõ ràng
# ===========================================================================
# Usage:
#   ./scripts/crawl_stocks.sh daily_price          # Price update sau mỗi phiên
#   ./scripts/crawl_stocks.sh daily_price_and_upload  # [CORE] Price + upload
#   ./scripts/crawl_stocks.sh kronos_prediction    # Dự báo Kronos
#   ./scripts/crawl_stocks.sh weekly_financial     # Financial (cuối tuần)
#   ./scripts/crawl_stocks.sh full_vn100           # Full crawl (1 lần/tháng)
#   ./scripts/crawl_stocks.sh health_monitor       # Health check + Telegram alert
# ===========================================================================

set -euo pipefail

AIFIA_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="$AIFIA_DIR/.venv/bin/python"
SCRIPTS="$AIFIA_DIR/scripts"
LOG_DIR="$AIFIA_DIR/logs"
DATA_DIR="$AIFIA_DIR/data"
NOW=$(date '+%Y-%m-%d %H:%M:%S')
TODAY=$(date +%Y%m%d)

mkdir -p "$LOG_DIR"

# ──────────────────────────────────────────────────────────────────────────
# Load .env
# ──────────────────────────────────────────────────────────────────────────
if [ -f "$AIFIA_DIR/.env" ]; then
    set -a
    source "$AIFIA_DIR/.env"
    set +a
fi

# ──────────────────────────────────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────────────────────────────────
log() {
    local ts=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$ts] $*" >> "$LOG_DIR/crawl_${TODAY}.log"
    echo "[$ts] $*"
}

log_error() { log "❌ $*"; }
log_warn()  { log "⚠️  $*"; }
log_ok()    { log "✅ $*"; }
log_info()  { log "ℹ️  $*"; }

# ──────────────────────────────────────────────────────────────────────────
# Pre-flight: system dependency checks
# ──────────────────────────────────────────────────────────────────────────

preflight_venv() {
    if [ ! -x "$PYTHON" ]; then
        log_error "Python venv not found at $PYTHON"
        return 1
    fi
    return 0
}

preflight_supabase() {
    if [ -z "${SUPABASE_URL:-}" ] || [ -z "${SUPABASE_SERVICE_KEY:-}" ]; then
        log_warn "Supabase credentials not configured — upload will be skipped"
        return 1
    fi
    return 0
}

preflight_kronos_repo() {
    # Self-healing: try permanent path, then /tmp, then auto-clone
    local kronos_ok=false
    
    for kp in "$AIFIA_DIR/kronos_repo" "/tmp/kronos_repo"; do
        if [ -f "$kp/model/__init__.py" ]; then
            kronos_ok=true
            break
        fi
    done
    
    if $kronos_ok; then
        return 0
    fi
    
    # Auto-heal: clone to permanent location
    log_warn "Kronos repo missing — auto-cloning..."
    if git clone https://github.com/shiyu-coder/Kronos.git "$AIFIA_DIR/kronos_repo" 2>&1 | tail -1; then
        log_ok "Kronos repo cloned to permanent location"
        return 0
    else
        log_error "Failed to clone Kronos repo"
        return 1
    fi
}

preflight_price_data() {
    # Check that at least some symbols have sufficient data for Kronos
    local fpt_file="$DATA_DIR/price_FPT.json"
    if [ -f "$fpt_file" ]; then
        local record_count=$("$PYTHON" -c "
import json
with open('$fpt_file') as f:
    records = json.load(f)
print(len(records))
" 2>/dev/null || echo "0")
        
        if [ "$record_count" -lt 50 ]; then
            log_error "FPT chỉ có $record_count records (cần ≥50 cho Kronos). Data có thể đã bị hỏng!"
            return 1
        fi
        log_info "FPT canary: $record_count records — OK for Kronos"
    fi
    return 0
}

# ──────────────────────────────────────────────────────────────────────────
# Post-run validation
# ──────────────────────────────────────────────────────────────────────────

validate_price_output() {
    local logfile="$LOG_DIR/daily_price_${TODAY}.log"
    
    if [ ! -f "$logfile" ]; then
        log_error "No daily_price log found"
        return 1
    fi
    
    # Count symbols that got data
    local symbols_with_data=$(grep -c '✅ [0-9]* records' "$logfile" 2>/dev/null || echo "0")
    local symbols_empty=$(grep -c '⚠️  empty' "$logfile" 2>/dev/null || echo "0")
    
    log_info "Price crawl: ${symbols_with_data} symbols with data, ${symbols_empty} empty"
    
    if [ "$symbols_with_data" = "0" ]; then
        log_error "HEALTH_CHECK: 0/100 symbols got price data — API may be broken"
        return 1
    fi
    
    # Check FPT canary freshness
    local fpt_date=$("$PYTHON" -c "
import json
with open('$DATA_DIR/price_FPT.json') as f:
    records = json.load(f)
dates = [r['date'] for r in records if r.get('date')]
print(max(dates) if dates else 'N/A')
" 2>/dev/null)
    
    local days_stale=999
    if [ "$fpt_date" != "N/A" ]; then
        days_stale=$(( ($(date +%s) - $(date -d "$fpt_date" +%s 2>/dev/null || echo 0)) / 86400 ))
    fi
    
    log_info "FPT latest: $fpt_date (${days_stale}d ago)"
    
    if [ "$days_stale" -gt 3 ]; then
        log_error "FPT data stale >3 days — crawling may have failed silently"
        return 1
    fi
    
    return 0
}

validate_kronos_output() {
    local logfile="$LOG_DIR/kronos_pred_${TODAY}.log"
    
    if [ ! -f "$logfile" ]; then
        log_error "No kronos_pred log found"
        return 1
    fi
    
    # Check that predictions were generated
    if grep -q "predictions saved to" "$logfile" 2>/dev/null; then
        local pred_count=$(grep -oP '\d+(?=/\d+ predictions saved)' "$logfile" 2>/dev/null || echo "?")
        log_ok "Kronos: predictions generated for $pred_count symbols"
        return 0
    else
        # Check for specific error patterns
        if grep -q "No symbols with adequate data" "$logfile" 2>/dev/null; then
            log_error "Kronos: 0 symbols had ≥50 records — price data may be corrupted"
        elif grep -q "ModuleNotFoundError" "$logfile" 2>/dev/null; then
            log_error "Kronos: model import failed — kronos_repo missing or broken"
        else
            log_error "Kronos: no prediction output found — unknown error"
        fi
        return 1
    fi
}

# ──────────────────────────────────────────────────────────────────────────
# Script runner with validation
# ──────────────────────────────────────────────────────────────────────────

run_script() {
    local name="$1"
    shift
    log "▶ Starting: $name"
    cd "$AIFIA_DIR"
    
    if "$PYTHON" "$@" >> "$LOG_DIR/${name}_${TODAY}.log" 2>&1; then
        log_ok "Completed: $name"
    else
        local exit_code=$?
        log_error "FAILED: $name (exit=$exit_code) — see $LOG_DIR/${name}_${TODAY}.log"
        return $exit_code
    fi
}

# ──────────────────────────────────────────────────────────────────────────
# Task implementations
# ──────────────────────────────────────────────────────────────────────────

daily_price() {
    log "📊 [DAILY] Cập nhật giá incremental"
    log "🔄 Cập nhật lúc: $NOW"
    
    if ! preflight_venv; then return 1; fi
    
    run_script "daily_price" "$SCRIPTS/run_crawler.py" \
        --symbols ALL \
        --incremental \
        --price-only
}

daily_price_and_upload() {
    log "📊 [DAILY] Cập nhật giá + upload Supabase"
    log "🔄 Cập nhật lúc: $NOW"
    
    # Pre-flight
    if ! preflight_venv; then return 1; fi
    
    # Crawl
    run_script "daily_price" "$SCRIPTS/run_crawler.py" \
        --symbols ALL \
        --incremental \
        --price-only
    
    # Validate
    if ! validate_price_output; then
        log_error "Upload skipped — price crawl failed validation"
        return 1
    fi
    
    # Upload
    log "☁️  [UPLOAD] Uploading to Supabase..."
    if preflight_supabase; then
        run_script "upload_prices" "$SCRIPTS/upload_prices.py" --incremental
    fi
    
    log "📅 FPT canary latest date: $("$PYTHON" -c "
import json
with open('$DATA_DIR/price_FPT.json') as f:
    records = json.load(f)
dates = [r['date'] for r in records if r.get('date')]
print(max(dates) if dates else 'N/A')
" 2>/dev/null)"
}

weekly_financial() {
    log "📋 [WEEKLY] Financial reports + company info refresh"
    log "🔄 Cập nhật lúc: $NOW"
    
    if ! preflight_venv; then return 1; fi
    
    run_script "weekly_financial" "$SCRIPTS/run_crawler.py" \
        --symbols ALL \
        --financial-only \
        --years 2
}

full_vn100() {
    log "🔄 [FULL] Full crawl toàn bộ VN100"
    log "🔄 Cập nhật lúc: $NOW"
    
    if ! preflight_venv; then return 1; fi
    
    run_script "full_vn100" "$SCRIPTS/run_crawler.py" \
        --symbols ALL \
        --years 5
}

kronos_prediction() {
    log "🔮 [DAILY] Kronos prediction cho VN100"
    log "🔄 Cập nhật lúc: $NOW"
    
    # Pre-flight checks
    if ! preflight_venv; then return 1; fi
    if ! preflight_kronos_repo; then return 1; fi
    if ! preflight_price_data; then return 1; fi
    
    # Run prediction
    run_script "kronos_pred" "$SCRIPTS/run_kronos_all.py"
    
    # Validate output
    validate_kronos_output
    
    # Show last prediction time
    local latest_pred=$(ls -t "$DATA_DIR/predictions"/kronos_vn100_*.json 2>/dev/null | head -1)
    if [ -n "$latest_pred" ]; then
        log "📁 Latest prediction: $(basename "$latest_pred")"
    fi
    
    # Upload to Supabase
    log "☁️  [UPLOAD] Uploading Kronos predictions to Supabase..."
    if preflight_supabase; then
        run_script "upload_kronos" "$SCRIPTS/upload_kronos.py"
    fi
}

health_monitor() {
    # Standalone health check — can be called by OS cron or systemd timer
    # Runs Python health_monitor.py and echoes results
    # If OpenClaw alert is needed, cron job handles Telegram delivery
    
    log "🩺 [HEALTH MONITOR] Full system health check"
    log "🔄 Kiểm tra lúc: $NOW"
    
    if ! preflight_venv; then return 1; fi
    
    if "$PYTHON" "$SCRIPTS/health_monitor.py" 2>&1; then
        log_ok "Health check passed"
    else
        log_error "Health check found issues"
        # Print detailed report
        "$PYTHON" "$SCRIPTS/health_monitor.py" 2>&1 | tee -a "$LOG_DIR/crawl_${TODAY}.log"
        return 1
    fi
}

check_health() {
    # Quick config check (legacy)
    health_monitor
}

intraday() {
    log "⏱️ [INTRADAY] Snapshot giá intraday"
    log "🔄 Cập nhật lúc: $NOW"
    
    if ! preflight_venv; then return 1; fi
    
    run_script "intraday" "$SCRIPTS/run_crawler.py" \
        --symbols VN30 \
        --intraday
}

# ──────────────────────────────────────────────────────────────────────────
# CLI dispatch
# ──────────────────────────────────────────────────────────────────────────
case "${1:-help}" in
    daily_price)            daily_price ;;
    daily_price_and_upload) daily_price_and_upload ;;
    weekly_financial)       weekly_financial ;;
    full_vn100)             full_vn100 ;;
    kronos_prediction)      kronos_prediction ;;
    health_monitor)         health_monitor ;;
    check_health)           check_health ;;
    intraday)               intraday ;;
    *)
        echo "Usage: $0 <task>"
        echo ""
        echo "Tasks:"
        echo "  daily_price             [CORE] Cập nhật giá (local JSON)"
        echo "  daily_price_and_upload  [CORE] Cập nhật giá + upload Supabase"
        echo "  weekly_financial        [CORE] Refresh báo cáo tài chính (cuối tuần)"
        echo "  full_vn100              [BULK] Full crawl toàn bộ VN100 (1 lần/tháng)"
        echo "  kronos_prediction       [AI]   Dự báo Kronos (sau daily_price)"
        echo "  health_monitor          [OPS]  Health check toàn diện + alert"
        echo "  check_health            [OPS]  Alias cho health_monitor"
        echo "  intraday                [NÂNG CAO] Snapshot giá intraday VN30"
        echo ""
        echo "🔄 Cập nhật lúc script version: 2026-05-19 v2"
        ;;
esac
