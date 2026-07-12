#!/usr/bin/env bash
# Process MIXSED2 EK80 ADCP data: extract → daily → combined
#
# Usage:
#   bash run_ek80adcp.sh
#
# Edit DATA_ROOT below for your system, then run.
# Re-running is safe: --skip-existing skips already-extracted files.
# Interrupt with Ctrl-C and restart; it picks up where it left off.

set -euo pipefail

# ── Edit this one line for your system ───────────────────────────────────────
# macOS (network drive):   /Volumes/Compartida/MIXSED2/EK80/EK80ADCP
# Linux / WSL:             /mnt/d/MIXSED2/EK80/EK80ADCP
# Git Bash on Windows:     /d/MIXSED2/EK80/EK80ADCP
DATA_ROOT=/Volumes/Compartida/MIXSED2/EK80/EK80ADCP
# ─────────────────────────────────────────────────────────────────────────────

RAW="$DATA_ROOT/files"
EXTRACTED="$DATA_ROOT/extracted"
DAILY="$DATA_ROOT/daily"

# Locate venv relative to this script so it works from any working directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/venv/bin/activate"

_elapsed() { local s=$(( SECONDS - $1 )); printf "%dm%02ds" $((s/60)) $((s%60)); }

echo "=== Step 1: extract raw files (~1 min each, 105 files) ==="
_t=$SECONDS
ek80adcp extract "$RAW" \
    -o "$EXTRACTED" \
    --depth-max 350 \
    --time-bin 60s \
    --skip-existing
echo "  step 1 done in $(_elapsed $_t)"

echo ""
echo "=== Step 2: concatenate by day ==="
_t=$SECONDS
ek80adcp concat "$EXTRACTED" \
    -o "$DAILY" \
    --by-day \
    --plot
echo "  step 2 done in $(_elapsed $_t)"

echo ""
echo "=== Step 3: single combined file ==="
_t=$SECONDS
ek80adcp concat "$DAILY" \
    -o "$DAILY/DSMIXSED2-combined.nc" \
    --plot
echo "  step 3 done in $(_elapsed $_t)"

echo ""
echo "All done."
