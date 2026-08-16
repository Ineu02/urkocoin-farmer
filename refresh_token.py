#!/usr/bin/env python3
"""Refresh urkocoin initData via Telethon and update .env"""
import asyncio, urllib.parse, os

async def refresh():
    from telethon import TelegramClient
    from telethon.tl.functions.messages import RequestWebViewRequest
    
    API_ID = 30433417
    API_HASH = 'ffafe69700630e329def865b52fc5596'
    ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    
    client = TelegramClient('/root/.agent/telegram_virtex_session', API_ID, API_HASH)
    await client.start()
    
    bot = await client.get_entity('urkocoin_bot')
    result = await client(RequestWebViewRequest(
        peer=bot, bot=bot,
        url='https://tap.urko.io',
        platform='android',
        from_bot_menu=False, silent=False
    ))
    
    parsed = urllib.parse.urlparse(result.url)
    params = urllib.parse.parse_qs(parsed.fragment)
    tg_data = urllib.parse.unquote(params.get('tgWebAppData', [''])[0])
    
    # Update .env
    lines = []
    updated = False
    with open(ENV_FILE) as f:
        for line in f:
            if line.startswith('URKO_COIN_INITDATA='):
                lines.append(f'URKO_COIN_INITDATA={tg_data}\n')
                updated = True
            else:
                lines.append(line)
    
    if not updated:
        lines.append(f'URKO_COIN_INITDATA={tg_data}\n')
    
    with open(ENV_FILE, 'w') as f:
        f.writelines(lines)
    
    print(f'OK {len(tg_data)}')
    await client.disconnect()

asyncio.run(refresh())
