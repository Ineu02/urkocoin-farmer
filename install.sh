#!/bin/bash
# urkocoin farmer — one-click installer
# Usage: curl -sL <raw-github-url>/install.sh | bash
set -euo pipefail

INSTALL_DIR="${URKO_INSTALL_DIR:-$HOME/urkocoin-farmer}"
REPO_URL="https://github.com/Ineu02/urkocoin-farmer.git"

echo "=== urkocoin farmer installer ==="

# Clone or pull
if [ -d "$INSTALL_DIR" ]; then
    echo "[*] Updating existing install..."
    cd "$INSTALL_DIR"
    git pull --quiet 2>/dev/null || true
else
    echo "[*] Cloning repo..."
    git clone "$REPO_URL" "$INSTALL_DIR" 2>/dev/null
    cd "$INSTALL_DIR"
fi

chmod +x farm.sh healthcheck.sh

# Create .env if missing
if [ ! -f .env ]; then
    echo "[!] No .env found. Creating from template..."
    cp .env.example .env
    echo "[!] EDIT .env and fill in your credentials:"
    echo "    nano ${INSTALL_DIR}/.env"
    exit 1
fi

source .env
if [ -z "${URKO_COIN_INITDATA:-}" ]; then
    echo "[!] URKO_COIN_INITDATA is empty in .env! Edit it first."
    echo "    nano ${INSTALL_DIR}/.env"
    exit 1
fi

# Install crontab entries
CRON_FARM="*/30 * * * * cd ${INSTALL_DIR} && bash farm.sh >> ${INSTALL_DIR}/farm.log 2>&1"
CRON_HEALTH="*/30 * * * * cd ${INSTALL_DIR} && bash healthcheck.sh | xargs -r hermes cron 2>/dev/null"

# Add to crontab if not already present
(crontab -l 2>/dev/null | grep -v "urkocoin-farmer" || true; echo "$CRON_FARM"; echo "$CRON_HEALTH") | crontab -

echo "[✓] Installed to ${INSTALL_DIR}"
echo "[✓] Cron jobs set (farm every 30m, health check every 30m)"
echo "[✓] Logs: ${INSTALL_DIR}/farm.log"
echo ""
echo "Manual run: cd ${INSTALL_DIR} && bash farm.sh"
echo "Watch logs: tail -f ${INSTALL_DIR}/farm.log"
