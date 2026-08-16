#!/bin/bash
# Combined: refresh token + farm — used by cron
set -eo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"

# 1. Refresh initData
python3 "${DIR}/refresh_token.py" >> "${DIR}/farm.log" 2>&1
if [ $? -ne 0 ]; then
    echo "$(date): TOKEN REFRESH FAILED" >> "${DIR}/farm.log"
    exit 1
fi

# 2. Run farm
bash "${DIR}/farm.sh"
