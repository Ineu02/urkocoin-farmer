#!/bin/bash
# urkocoin farmer health check — alerts if farming log is stale
# Runs silent when healthy, outputs alert when broken
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="${SCRIPT_DIR}/farm.log"
MAX_STALE_MIN=${URKO_FARM_STALE_MIN:-90}

if [ ! -f "$LOG" ]; then
    echo "🔴 ALERT: Farm log missing! Farmer never ran."
    exit 0
fi

LAST_MOD=$(stat -c %Y "$LOG" 2>/dev/null || echo 0)
NOW=$(date +%s)
AGE_MIN=$(( (NOW - LAST_MOD) / 60 ))

if [ "$AGE_MIN" -gt "$MAX_STALE_MIN" ]; then
    LAST_LINE=$(tail -1 "$LOG")
    echo "🔴 ALERT: Farmer STALE ${AGE_MIN}min! Last: $LAST_LINE"
else
    exit 0
fi
