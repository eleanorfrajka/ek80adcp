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

# ── Edit this one line for your system (or set DATA_ROOT in the environment) ─
# macOS (network drive):   /Volumes/Compartida/MIXSED2/EK80/EK80ADCP
# Linux / WSL:             /mnt/d/MIXSED2/EK80/EK80ADCP
# Git Bash on Windows:     /d/MIXSED2/EK80/EK80ADCP
DATA_ROOT="${DATA_ROOT:-/Volumes/Compartida/MIXSED2/EK80/EK80ADCP}"
if [[ ! -d "$DATA_ROOT" ]]; then
  echo "DATA_ROOT not found: $DATA_ROOT" >&2
  echo "Edit DATA_ROOT in this script or set it in the environment before running." >&2
  exit 1
fi
# ─────────────────────────────────────────────────────────────────────────────

RAW="$DATA_ROOT/files"
EXTRACTED="$DATA_ROOT/extracted"
DAILY="$DATA_ROOT/daily"

# Locate venv relative to this script so it works from any working directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_ACTIVATE="$SCRIPT_DIR/venv/bin/activate"
if [[ ! -f "$VENV_ACTIVATE" ]]; then
  echo "Missing venv at $VENV_ACTIVATE" >&2
  echo "Run: python -m venv venv && pip install -e ." >&2
  exit 1
fi
source "$VENV_ACTIVATE"

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
