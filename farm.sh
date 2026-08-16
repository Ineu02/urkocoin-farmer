#!/bin/bash
# urkocoin auto-farmer — spins wheel, claims dust, converts GOLD→URKO, auto-withdraws
# Usage: bash farm.sh (reads .env for credentials)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="${SCRIPT_DIR}/farm.log"

# Load credentials from .env
if [ ! -f "${SCRIPT_DIR}/.env" ]; then
    echo "$(date): ERROR: .env not found! Copy .env.example → .env and fill in credentials." >> "$LOG"
    exit 1
fi
source "${SCRIPT_DIR}/.env"

LP="${URKO_COIN_INITDATA}"
WALLET="${URKO_WALLET:-4uyH55BVHaLKC9qX29jLEo7RqPZ6EwYemFfpjpaf4kuA}"
NETWORK="${URKO_SCHAIN:-solana}"
API="https://api.urko.io/v1"

api() {
    curl -s --max-time 10 -X POST "${API}/$1" \
        -H "Content-Type: application/json" \
        -H "launch-params: $LP" \
        -d "${2:-{}}" 2>&1
}

echo "$(date): === Farm cycle start ===" >> "$LOG"

# 1. Spin wheel (up to 5 times)
for i in 1 2 3 4 5; do
    RESP=$(api "wheel/spin")
    if echo "$RESP" | grep -q "spin limit reached"; then
        break
    fi
    PRIZE=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); p=d.get('payload',{}); print(f'{p.get(\"prize\",\"?\")} +{p.get(\"amount\",0)}')" 2>/dev/null || echo "parse error")
    echo "$(date): Spin $i: $PRIZE" >> "$LOG"
    sleep 4
done

# 2. Claim dust
DUST=$(api "user/dust")
if echo "$DUST" | grep -q '"ok":true'; then
    echo "$(date): Dust claimed!" >> "$LOG"
fi

# 3. Check balance
BAL=$(api "deposit/mios")
GOLD=$(echo "$BAL" | python3 -c "import sys,json; print(json.load(sys.stdin).get('payload',{}).get('balances',{}).get('gold',0))" 2>/dev/null || echo 0)
URKO=$(echo "$BAL" | python3 -c "import sys,json; print(json.load(sys.stdin).get('payload',{}).get('balances',{}).get('urko',0))" 2>/dev/null || echo 0)
echo "$(date): Balance: GOLD=$GOLD | URKO=$URKO" >> "$LOG"

# 4. Convert GOLD → URKO (500:1)
if [ "$GOLD" -gt 500 ] 2>/dev/null; then
    AMT=$((GOLD / 500))
    api "exchange/swap" "{\"usdtCount\":$AMT}" > /dev/null
    echo "$(date): Swapped $GOLD GOLD → $AMT URKO" >> "$LOG"
    
    BAL2=$(api "deposit/mios")
    URKO=$(echo "$BAL2" | python3 -c "import sys,json; print(json.load(sys.stdin).get('payload',{}).get('balances',{}).get('urko',0))" 2>/dev/null || echo 0)
fi

# 5. Auto-withdraw if ≥ 10,000 URKO (leave 2,500 fee buffer)
if [ "$URKO" -ge 10000 ] 2>/dev/null; then
    WD_AMOUNT=$((URKO - 2500))
    echo "$(date): *** WITHDRAWAL: $WD_AMOUNT URKO → $WALLET ***" >> "$LOG"
    WD=$(api "user/withdrawal" "{\"token\":\"urko\",\"amount\":$WD_AMOUNT,\"cryptoAddress\":\"$WALLET\",\"cryptoNetwork\":\"$NETWORK\"}")
    echo "$(date): Withdrawal result: $WD" >> "$LOG"
fi

echo "$(date): === Farm cycle end ===" >> "$LOG"
echo "---" >> "$LOG"
