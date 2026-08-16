#!/usr/bin/env python3
"""urkocoin game auto-player — plays all active games (ludo, blackjack, parcheesi)"""
import requests, json, time, sys

# Load credentials
env = {}
with open('/root/urkocoin-farmer/.env') as f:
    for line in f:
        if '=' in line and not line.startswith('#'):
            k, v = line.strip().split('=', 1)
            env[k] = v

LP = env['URKO_COIN_INITDATA']
H = {'Content-Type': 'application/json', 'launch-params': LP}
B = 'https://api.urko.io/v1'

def api(ep, body):
    try:
        r = requests.post(f'{B}/game/{ep}', headers=H, json=body, timeout=8)
        return r.json()
    except:
        return {'status': 'error'}

def play_blackjack(pid):
    """Play one blackjack hand with basic strategy"""
    r = api('estado', {'partidaId': pid})
    d = r.get('payload', {})
    legales = d.get('legales', [])
    tab = d.get('tablero', {})
    
    if 'hit' in legales:
        # Count hand value
        hand = tab.get('manos', {}).get('0', [])
        vals = []
        aces = 0
        for c in hand:
            v = (c % 13) + 1
            if v == 1:
                aces += 1
                vals.append(11)
            elif v >= 10:
                vals.append(10)
            else:
                vals.append(v)
        total = sum(vals)
        while total > 21 and aces:
            total -= 10
            aces -= 1
        
        if total < 17:
            return 'hit'
        return 'stand'
    return 'stand'

def play_ludo_or_parcheesi(pid, legales, tab):
    """Pick the best move for ludo/parcheesi"""
    # Just pick the first legal move (server validates legality)
    return legales[0] if legales else None

def play_game(pid, game_type):
    """Play a single game to completion"""
    wins = 0
    losses = 0
    for turn in range(200):
        r = api('estado', {'partidaId': pid})
        d = r.get('payload', {})
        
        if d.get('estado') == 'fin' or d.get('fin'):
            fin = d.get('fin', {})
            gold = d.get('miGold', '?')
            motivo = fin.get('motivo', '?')
            premio = fin.get('premio', 0)
            print(f"  Game {pid} ENDED: motivo={motivo} premio={premio} gold={gold}")
            return premio
        
        legales = d.get('legales', [])
        if not legales:
            time.sleep(1)
            continue
        
        if game_type == 'blackjack':
            move = play_blackjack(pid)
        else:
            move = play_ludo_or_parcheesi(pid, legales, d.get('tablero', {}))
        
        if not move:
            time.sleep(1)
            continue
        
        r2 = api('mover', {'partidaId': pid, 'jugada': move})
        payload = r2.get('payload', {})
        fin = payload.get('fin') if isinstance(payload, dict) else None
        if fin:
            gold = payload.get('miGold', '?') if isinstance(payload, dict) else '?'
            if isinstance(fin, dict):
                premio = fin.get('premio', 0)
            elif isinstance(fin, str):
                premio = 0
            else:
                premio = 0
            print(f"  Game {pid} ENDED: premio={premio} gold={gold}")
            return premio
        
        time.sleep(0.3)
    
    print(f"  Game {pid}: timeout after 200 turns")
    return 0

def main():
    # Get active games
    r = api('mias', {})
    games = r.get('payload', {}).get('partidas', [])
    gold_before = r.get('payload', {}).get('gold', 0)
    print(f"Active games: {len(games)} | Gold: {gold_before}")
    
    total_won = 0
    for g in games:
        pid = g['partidaId']
        jtype = g['juego']
        print(f"\nPlaying {jtype} (ID:{pid})...")
        won = play_game(pid, jtype)
        total_won += won
        time.sleep(0.5)
    
    # Check final gold
    r2 = api('mias', {})
    gold_after = r2.get('payload', {}).get('gold', 0)
    remaining = r2.get('payload', {}).get('partidas', [])
    print(f"\n=== RESULTS ===")
    print(f"Gold: {gold_before} → {gold_after} (change: {gold_after - gold_before})")
    print(f"Total premio: {total_won}")
    print(f"Remaining games: {len(remaining)}")

if __name__ == '__main__':
    main()
