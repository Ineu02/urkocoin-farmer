#!/usr/bin/env python3.12
"""ATF Enhanced Auto-Miner with boost exploit
- Auto login, start mine, boost (captcha bypass), sync, claim
- Loops forever with retry logic"""
import requests, json, urllib.parse, time, re, os, sys, signal, logging
from datetime import datetime
from logging.handlers import RotatingFileHandler

# --- Config ---
BASE = 'https://atfminers.asloni.online/miner'
ENV_FILE = '/root/urkocoin-farmer/.atf_initdata'
LOG_FILE = '/root/urkocoin-farmer/atf-miner.log'
SYNC_INTERVAL = 15      # seconds between syncs
CLAIM_INTERVAL = 300    # claim every 5 min
BOOST_INTERVAL = 10     # seconds between boost attempts
RETRY_DELAY = 3         # seconds between retries
MAX_RETRIES = 5

# --- Logging ---
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logger = logging.getLogger('atf')
logger.setLevel(logging.DEBUG)
fh = RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=3)
fh.setLevel(logging.DEBUG)
fh.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)-7s %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
logger.addHandler(fh)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(logging.Formatter('%(message)s'))
logger.addHandler(ch)

# --- Signal handling ---
running = True
def sig_handler(sig, frame):
    global running
    logger.info("Shutting down gracefully...")
    running = False
signal.signal(signal.SIGTERM, sig_handler)
signal.signal(signal.SIGINT, sig_handler)

# --- Load credentials ---
def load_init_data():
    with open(ENV_FILE) as f:
        return f.read().strip()

# --- API helper ---
def api_call(session, action, init_data, tma, tg_id, extra={}, retries=MAX_RETRIES):
    for i in range(retries):
        try:
            headers = {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                'X-Telegram-Init-Data': init_data,
                'User-Agent': 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36'
            }
            if tma:
                headers['X-ATF-TMA-Session'] = tma
                session.cookies.set('atf_tma_session', tma, domain='atfminers.asloni.online', path='/miner')
            
            body = {
                'initData': init_data,
                'request_id': f'vps-{int(time.time()*1000)}',
                'device_id': 'atf-miner-vps',
                'tg_id': tg_id,
                **extra
            }
            r = session.post(f'{BASE}/index.php?action={action}&t={int(time.time()*1000)}',
                           headers=headers, json=body, timeout=30)
            return r.json()
        except Exception as e:
            logger.warning(f"  {action} retry {i+1}: {type(e).__name__}: {e}")
            time.sleep(RETRY_DELAY * (i + 1))
    return {'status': 'timeout'}

# --- Math solver ---
def solve_math(question):
    q = question.replace('×', '*').replace('÷', '/').replace('=', '').replace('?', '').strip()
    m = re.search(r'(\d+)\s*([+\-*/])\s*(\d+)', q)
    if m:
        a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
        return {'+': a+b, '-': a-b, '*': a*b, '/': a//b}.get(op, 0)
    return 0

# --- Main loop ---
def run():
    global running
    init_data = load_init_data()
    params = urllib.parse.parse_qs(init_data)
    user = json.loads(params.get('user', ['{}'])[0])
    tg_id = user['id']
    username = user.get('username', '')
    
    logger.info("=" * 60)
    logger.info(f"ATF MINER STARTING — {username} (tg_id={tg_id})")
    logger.info("=" * 60)
    
    session = requests.Session()
    tma = ''
    last_sync = 0
    last_claim = 0
    last_boost = 0
    total_claimed = 0
    boost_exploits = 0
    
    while running:
        try:
            # --- Login ---
            logger.info("Logging in...")
            login = api_call(session, 'login', init_data, tma, tg_id, {'username': username})
            if login.get('status') != 'success':
                logger.error(f"Login failed: {login.get('message', 'unknown')}")
                time.sleep(30)
                continue
            tma = login.get('tma_session_token', '')
            u = login.get('user', {})
            mined = u.get('mined_balance', 0)
            pending = u.get('pending_reward', 0)
            level = u.get('miner_level', 1)
            difficulty = login.get('difficulty', 21)
            tps = login.get('boost_taps_per_sec', 1.75)
            logger.info(f"OK — Level={level} Mined={mined} Pending={pending} Diff={difficulty} TPS={tps}")
            
            # --- Start mining ---
            logger.info("Starting mining...")
            ch = api_call(session, 'get_math_challenge', init_data, tma, tg_id, {'scope': 'start_mine'})
            if ch.get('status') == 'success':
                ans = solve_math(ch.get('question', ''))
                start = api_call(session, 'start_mine', init_data, tma, tg_id, 
                               {'math_challenge_id': ch['challenge_id'], 'math_answer': str(ans)})
                if start.get('status') == 'success':
                    logger.info("Mining STARTED ✓")
                else:
                    logger.warning(f"Start mine: {start.get('message', '')}")
            
            # --- Mining loop ---
            cycle_count = 0
            while running:
                now = time.time()
                
                # Sync
                if now - last_sync >= SYNC_INTERVAL:
                    sync = api_call(session, 'sync_mining_state', init_data, tma, tg_id, {})
                    if sync.get('status') == 'success':
                        sb = sync.get('session_balance', 0)
                        tm = sync.get('total_mined_this_session', 0)
                        pr = sync.get('pending_reward', 0)
                        ba = sync.get('boost_active', False)
                        br = sync.get('boost_ready', False)
                        logger.debug(f"Sync #{cycle_count}: balance={sb} mined={tm} pending={pr} boost={'ON' if ba else 'off'} ready={br}")
                    last_sync = now
                    cycle_count += 1
                
                # Boost with exploit (empty challenge_id bypasses captcha)
                if now - last_boost >= BOOST_INTERVAL:
                    boost = api_call(session, 'activate_boost', init_data, tma, tg_id, 
                                    {'math_challenge_id': '', 'math_answer': '0', 'display_preview': 0})
                    status = boost.get('status', '')
                    if status == 'success':
                        logger.info(f"⚡ BOOST ACTIVATED (exploit!) pending={boost.get('pending_reward',0)}")
                        boost_exploits += 1
                    elif status == 'penalty':
                        # Penalty active - wait and retry
                        remaining = boost.get('remaining', 0)
                        if remaining > 0:
                            logger.info(f"⏳ Boost locked for {remaining}s (penalty)")
                            last_boost = now + remaining - 5  # retry 5s before penalty ends
                        else:
                            last_boost = now + 60
                    elif status == 'cooldown':
                        cd = boost.get('cooldown_remaining', 10)
                        logger.debug(f"Boost cooldown: {cd}s")
                        last_boost = now + cd
                    else:
                        logger.debug(f"Boost: {status} — {boost.get('message','')[:80]}")
                    last_boost = max(last_boost, now + BOOST_INTERVAL)
                
                # Claim — use LOGIN pending (sync returns 0, login returns real pending)
                if now - last_claim >= CLAIM_INTERVAL:
                    login2 = api_call(session, 'login', init_data, tma, tg_id, {'username': username})
                    if login2.get('status') == 'success':
                        tma = login2.get('tma_session_token', tma)
                        pr = login2.get('user', {}).get('pending_reward', 0)
                        if pr > 0.00001:
                            claim = api_call(session, 'claim', init_data, tma, tg_id,
                                           {'claim_preview': float(pr)})
                            if claim.get('status') == 'success':
                                amt = claim.get('claimed_amount', 0)
                                total_claimed += amt
                                new_bal = claim.get('new_pool_balance', 0)
                                logger.info(f"💰 CLAIMED {amt} ATF (total: {total_claimed:.4f}, bal: {new_bal})")
                            else:
                                logger.debug(f"Claim: {claim.get('message','')}")
                        else:
                            logger.debug(f"Claim skip: pending={pr}")
                    last_claim = now
                
                # Status every 5 minutes
                if cycle_count > 0 and cycle_count % 20 == 0:
                    sync = api_call(session, 'sync_mining_state', init_data, tma, tg_id, {})
                    if sync.get('status') == 'success':
                        u2 = sync.get('user', {})
                        logger.info(f"📊 STATUS: Mined={u2.get('mined_balance',0)} Pending={sync.get('pending_reward',0)} "
                                   f"Total claimed={total_claimed:.4f} Exploits={boost_exploits}")
                
                time.sleep(3)
            
            logger.info("Mining loop ended, restarting in 10s...")
            time.sleep(10)
            
        except Exception as e:
            logger.error(f"Error: {e}")
            time.sleep(30)
    
    logger.info(f"FINAL: Total claimed={total_claimed:.4f} ATF, Exploits={boost_exploits}")

if __name__ == '__main__':
    run()
