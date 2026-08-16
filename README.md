# urkocoin farmer

Auto-farms urkocoin (tap-to-earn Telegram bot) — spins wheel, claims dust, converts GOLD→URKO, auto-withdraws when balance hits 10K.

## Setup

```bash
git clone https://github.com/Ineu02/urkocoin-farmer.git
cd urkocoin-farmer
cp .env.example .env
nano .env  # fill in your credentials
bash install.sh
```

## Credentials (.env)

| Variable | Description |
|----------|-------------|
| `URKO_COIN_INITDATA` | Telegram webapp initData (capture via browser devtools) |
| `URKO_WALLET` | Solana wallet address for withdrawals |
| `URKO_SCHAIN` | Network: `solana` (default) or `evm` |

### How to get initData

1. Open @urkocoin_bot in Telegram
2. Click the webapp button
3. Open browser DevTools (F12) → Network tab
4. Find any request to `api.urko.io`
5. Copy the `launch-params` header value

## Files

| File | Purpose |
|------|---------|
| `farm.sh` | Main farming script (wheel + dust + swap + withdraw) |
| `healthcheck.sh` | Monitors if farmer is alive (silent when healthy) |
| `install.sh` | One-click installer with crontab setup |
| `.env.example` | Credential template |

## Manual run

```bash
bash farm.sh
tail -f farm.log
```
