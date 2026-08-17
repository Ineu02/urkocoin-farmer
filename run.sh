#!/bin/bash
# Combined: refresh + farm + tap + games
set -eo pipefail
PROJECT="/root/urkocoin-farmer"
LOG="${PROJECT}/farm.log"

# 1. Refresh token
python3 "${PROJECT}/refresh_token.py" >> "${LOG}" 2>&1

# 2. Auto-tap (WebSocket clicks)
python3.12 "${PROJECT}/auto_tap.py" >> "${LOG}" 2>&1

# 3. Farm (spin + dust + swap)
bash "${PROJECT}/farm.sh" >> "${LOG}" 2>&1

# 4. Play active games
python3.12 "${PROJECT}/game_player.py" >> "${LOG}" 2>&1
