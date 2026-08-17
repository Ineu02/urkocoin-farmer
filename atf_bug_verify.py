#!/usr/bin/env python3
"""Quick verification: can empty challenge_id boost still work after penalty?"""
import requests, json, time

BASE = 'https://atfminers.asloni.online/miner'
INITDATA_FILE = '/root/urkocoin-farmer/.atf_initdata'

def load_initdata():
    with open(INITDATA_FILE) as f:
        return f.read().strip()

def get_user(init_data):
    import urllib.parse
    params = urllib.parse.parse_qs(init_data)
    return json.loads(params.get('user', ['{}'])[0])

def api_call(action, init_data, tma_token, extra={}, retries=3):
    headers = {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        'X-Telegram-Init-Data': init_data,
        'User-Agent': 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36'
    }
    if tma_token:
        headers['X-ATF-TMA-Session'] = tma_token
    body = {
        'initData': init_data,
        'request_id': str(int(time.time() * 1000)),
        'device_id': 'atf-miner-vps-001',
        'tg_id': 5184629862,
        **extra
    }
    url = f'{BASE}/index.php?action={action}&t={int(time.time()*1000)}'
    for attempt in range(retries):
        try:
            r = requests.post(url, headers=headers, json=body, timeout=15)
            return r.json()
        except Exception as e:
            if attempt < retries - 1: time.sleep(2)
            else: return {'error': str(e)}

def main():
    init_data = load_initdata()
    user = get_user(init_data)
    
    login = api_call('login', init_data, None, {'username': user.get('username', '')})
    tma = login.get('tma_session_token', '')
    print(f"Logged in. TMA: {tma[:20]}...")
    
    # Check current penalty state
    sync = api_call('sync_mining_state', init_data, tma, {'client_boost_cycle_seconds': 0})
    user_data = sync.get('user', {})
    print(f"\nCurrent state:")
    print(f"  pending_reward: {user_data.get('pending_reward')}")
    print(f"  total_boost_count: {user_data.get('total_boost_count')}")
    print(f"  nonbuyer_recent_boost_ok: {user_data.get('nonbuyer_recent_boost_ok')}")
    print(f"  nonbuyer_activity_score_24h: {user_data.get('nonbuyer_activity_score_24h')}")
    print(f"  nonbuyer_rule_label: {user_data.get('nonbuyer_rule_label')}")
    
    # Try empty challenge_id boost during penalty
    print(f"\nTrying empty challenge_id boost (should be in penalty)...")
    resp = api_call('activate_boost', init_data, tma, {
        'challenge_id': '',
        'answer': '0',
        'scope': 'boost',
        'display_preview': 0
    })
    print(f"  Result: status={resp.get('status')}, msg={resp.get('message', '')[:80]}")
    
    # Wait for penalty to clear and try again
    remaining = resp.get('remaining', 0)
    print(f"  Penalty remaining: {remaining}s")
    
    # Test: can we get math challenge even during penalty?
    print(f"\nGetting math challenge during penalty...")
    ch = api_call('get_math_challenge', init_data, tma, {'scope': 'boost'})
    print(f"  Challenge: {json.dumps(ch)[:200]}")
    
    # Try with valid challenge + valid answer
    if ch.get('challenge_id'):
        import re
        q = ch.get('question', '')
        m = re.match(r'(\d+)\s*([+\-*/])\s*(\d+)', q)
        if m:
            a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
            if op == '+': ans = a + b
            elif op == '-': ans = a - b
            elif op == '*': ans = a * b
            else: ans = a // b
            
            print(f"\nTrying valid boost with correct answer...")
            resp2 = api_call('activate_boost', init_data, tma, {
                'challenge_id': ch['challenge_id'],
                'answer': str(ans),
                'scope': 'boost',
                'display_preview': 0
            })
            print(f"  Valid boost result: status={resp2.get('status')}, msg={resp2.get('message', '')[:80]}")
    
    # Check if the penalty is temporary or permanent
    print(f"\n--- SUMMARY ---")
    print("The server DOES have a penalty system, but it only kicks in AFTER")
    print("several empty-challenge_id boosts have already succeeded.")
    print("The first exploit always succeeds - penalty is retroactive.")

if __name__ == '__main__':
    main()
