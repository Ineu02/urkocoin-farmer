#!/usr/bin/env python3.12
"""urkocoin auto-tapper — WebSocket CLICKS with energy cooldown"""
import websocket, json, time, threading, requests, urllib.parse, sys

ENV_FILE = "/root/urkocoin-farmer/.env"
API = "https://api.urko.io/v1"
WS_URL = "wss://api.urko.io/socket.io/?EIO=4&transport=websocket"
ENERGY_MAX = 1500  # L1 energy boost
CLICKS_PER_BATCH = 50
RECHARGE_WAIT = 1800  # 30 min between full energy bars

def load_env():
    env = {}
    with open(ENV_FILE) as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                k, v = line.strip().split('=', 1)
                env[k] = v
    return env

def get_balance(LP):
    r = requests.post(f'{API}/deposit/mios',
                      headers={'Content-Type': 'application/json', 'launch-params': LP},
                      json={}, timeout=10)
    return r.json()['payload']['balances']

def tap_session(LP, user_id, count=50, rounds=30):
    clicks_sent = [0]
    done = threading.Event()
    
    def on_message(ws, message):
        if message.startswith('0'):
            auth = json.dumps({"launchParams": LP, "userId": str(user_id), "version": "v1"})
            ws.send(f'40{auth}')
        elif message.startswith('40'):
            for i in range(rounds):
                msg = json.dumps(['CLICKS', {'count': count}])
                ws.send(f'42{msg}')
                clicks_sent[0] += count
                time.sleep(0.3)
            time.sleep(2)
            done.set()
            ws.close()
        elif message.startswith('2'):
            ws.send('2')
    
    ws = websocket.WebSocketApp(WS_URL, on_message=on_message)
    t = threading.Thread(target=ws.run_forever, kwargs={'ping_timeout': 15})
    t.daemon = True
    t.start()
    done.wait(timeout=30)
    try: ws.close()
    except: pass
    return clicks_sent[0]

def main():
    env = load_env()
    LP = env['URKO_COIN_INITDATA']
    parsed = urllib.parse.parse_qs(LP)
    user_raw = parsed.get('user', ['{}'])[0]
    user_data = json.loads(user_raw)
    user_id = user_data['id']
    
    b = get_balance(LP)
    print(f"Gold: {b['gold']} | URKO: {b['urko']}", flush=True)
    
    # Tap session: 1500 clicks (full energy bar)
    clicks = tap_session(LP, user_id, count=CLICKS_PER_BATCH, rounds=30)
    
    time.sleep(2)
    b2 = get_balance(LP)
    earned = b2['gold'] - b['gold']
    print(f"Tap: {clicks} clicks → Gold {b['gold']} → {b2['gold']} (+{earned})", flush=True)
    print(f"Total: {b2['gold']} gold | {b2['urko']} URKO", flush=True)

if __name__ == '__main__':
    main()
