#!/usr/bin/env bash
#
# Automated Leafly strain import runner.
#
# Runs scrape + import in batches, logging everything.
# Designed to run detached inside the Docker container.
#
# Usage:
#   docker exec -d canna-web bash /app/scripts/auto_import.sh
#   docker exec -d canna-web bash /app/scripts/auto_import.sh --batch-size 30 --batch-pause 120
#
# Monitor:
#   docker exec canna-web tail -f /app/scripts/output/auto_import.log
#
# Stop gracefully:
#   docker exec canna-web touch /app/scripts/output/STOP_IMPORT
#

set -euo pipefail

# ── Defaults ──────────────────────────────────────────────────────────
BATCH_SIZE=50
STRAIN_PAUSE=5
BATCH_PAUSE=60
SCRAPE_PAUSE=2
MAX_BATCHES=0          # 0 = unlimited
SKIP_SCRAPE=false

# ── Paths ─────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT_DIR="${SCRIPT_DIR}/output"
LOG_FILE="${OUTPUT_DIR}/auto_import.log"
STOP_FILE="${OUTPUT_DIR}/STOP_IMPORT"
ALIAS_FILE="${OUTPUT_DIR}/leafly_missing_aliases.txt"
PID_FILE="${OUTPUT_DIR}/auto_import.pid"

# ── Parse arguments ───────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --batch-size)     BATCH_SIZE="$2";     shift 2 ;;
        --strain-pause)   STRAIN_PAUSE="$2";   shift 2 ;;
        --batch-pause)    BATCH_PAUSE="$2";    shift 2 ;;
        --scrape-pause)   SCRAPE_PAUSE="$2";   shift 2 ;;
        --max-batches)    MAX_BATCHES="$2";    shift 2 ;;
        --skip-scrape)    SKIP_SCRAPE=true;    shift   ;;
        *)
            echo "Unknown option: $1" >&2
            echo "Options: --batch-size N --strain-pause N --batch-pause N --scrape-pause N --max-batches N --skip-scrape" >&2
            exit 1
            ;;
    esac
done

# ── Helpers ───────────────────────────────────────────────────────────
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

check_stop() {
    if [[ -f "$STOP_FILE" ]]; then
        log "STOP_IMPORT flag detected. Shutting down gracefully."
        rm -f "$STOP_FILE" "$PID_FILE"
        exit 0
    fi
}

cleanup() {
    rm -f "$PID_FILE"
    log "Import runner exited."
}
trap cleanup EXIT

# ── Pre-flight ────────────────────────────────────────────────────────
mkdir -p "$OUTPUT_DIR"

# Prevent duplicate runs
if [[ -f "$PID_FILE" ]]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "Import already running (PID $OLD_PID). Exiting." >&2
        exit 1
    fi
    rm -f "$PID_FILE"
fi
echo $$ > "$PID_FILE"

# Remove stale stop file from previous run
rm -f "$STOP_FILE"

log "=========================================="
log "Leafly Auto Import Started"
log "  batch_size=$BATCH_SIZE  strain_pause=$STRAIN_PAUSE"
log "  batch_pause=$BATCH_PAUSE  max_batches=$MAX_BATCHES"
log "  skip_scrape=$SKIP_SCRAPE"
log "=========================================="

# ── Step 1: Scrape slugs ─────────────────────────────────────────────
if [[ "$SKIP_SCRAPE" == false ]]; then
    check_stop
    log "Step 1: Scraping Leafly slugs..."
    if python "${SCRIPT_DIR}/scrape_leafly_slugs.py" --pause "$SCRAPE_PAUSE" >> "$LOG_FILE" 2>&1; then
        log "Scrape completed."
    else
        log "WARNING: Scrape failed (exit code $?). Using existing alias file."
    fi
else
    log "Step 1: Skipping scrape (--skip-scrape)."
fi

# ── Step 2: Check alias file ─────────────────────────────────────────
if [[ ! -f "$ALIAS_FILE" ]]; then
    log "ERROR: Alias file not found: $ALIAS_FILE"
    exit 1
fi

TOTAL_ALIASES=$(grep -c '[^[:space:]]' "$ALIAS_FILE" 2>/dev/null || echo 0)
log "Total aliases in file: $TOTAL_ALIASES"

if [[ "$TOTAL_ALIASES" -eq 0 ]]; then
    log "No aliases to import. Done."
    exit 0
fi

# ── Step 3: Import in batches ────────────────────────────────────────
BATCH_NUM=0

while true; do
    check_stop

    BATCH_NUM=$((BATCH_NUM + 1))

    # Check max batches limit
    if [[ "$MAX_BATCHES" -gt 0 && "$BATCH_NUM" -gt "$MAX_BATCHES" ]]; then
        log "Reached max batches limit ($MAX_BATCHES). Stopping."
        log "=========================================="
        log "Import runner finished. Total batches: $MAX_BATCHES"
        log "=========================================="
        exit 0
    fi

    # Check how many aliases remain (re-read file each batch since import
    # appends filtered/skipped aliases to the skip file, and we may want
    # to re-scrape periodically to refresh the list)
    REMAINING=$(grep -c '[^[:space:]]' "$ALIAS_FILE" 2>/dev/null || echo 0)
    if [[ "$REMAINING" -eq 0 ]]; then
        log "No more aliases to import. All done!"
        break
    fi

    log "── Batch $BATCH_NUM (${REMAINING} aliases remaining) ──"
    log "Importing up to $BATCH_SIZE strains..."

    BATCH_START=$(date +%s)

    # Run import — capture exit code but don't abort on failure
    set +e
    python manage.py import_leafly_strains \
        --alias-file "$ALIAS_FILE" \
        --limit "$BATCH_SIZE" \
        --pause "$STRAIN_PAUSE" \
        >> "$LOG_FILE" 2>&1
    EXIT_CODE=$?
    set -e

    BATCH_END=$(date +%s)
    BATCH_DURATION=$(( BATCH_END - BATCH_START ))

    if [[ "$EXIT_CODE" -eq 0 ]]; then
        log "Batch $BATCH_NUM completed in ${BATCH_DURATION}s."
    else
        log "WARNING: Batch $BATCH_NUM exited with code $EXIT_CODE after ${BATCH_DURATION}s."
    fi

    # Re-scrape to refresh the missing aliases list (removes imported ones)
    log "Refreshing alias list..."
    if python "${SCRIPT_DIR}/scrape_leafly_slugs.py" --pause "$SCRAPE_PAUSE" >> "$LOG_FILE" 2>&1; then
        log "Alias list refreshed."
    else
        log "WARNING: Refresh scrape failed. Will use existing list."
    fi

    # Pause between batches
    log "Pausing ${BATCH_PAUSE}s before next batch..."
    sleep "$BATCH_PAUSE"
done

log "=========================================="
log "Import runner finished. Total batches: $BATCH_NUM"
log "=========================================="
