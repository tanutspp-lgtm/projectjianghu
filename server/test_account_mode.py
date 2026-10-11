"""Authenticated WebSocket create/relog/restart integration without live credentials."""
import asyncio
import json
import tempfile
import time
from pathlib import Path

import websockets
from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed

import server
from auth import VerifiedIdentity
from persistence import LocalSqliteStore


PORT = 19557
URI = f'ws://127.0.0.1:{PORT}/ws'
TOKEN = 'test-token-' + ('x' * 64)


class FakeVerifier:
    async def verify(self, access_token):
        assert access_token == TOKEN
        return VerifiedIdentity('user-account-test', 'test@example.invalid', int(time.time()) + 3600)


async def receive_kind(ws, kind, timeout=3):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        message = json.loads(await asyncio.wait_for(ws.recv(), max(.1, end - time.monotonic())))
        if message.get('t') == kind:
            return message
    raise AssertionError('missing ' + kind)


async def join_account(name='หลินอิง', avatar='female_hair_02_red'):
    ws = await websockets.connect(URI)
    await ws.send(json.dumps({
        't': 'join',
        'avatar': avatar,
        'auth': {'access_token': TOKEN},
        'character_name': name,
    }))
    return ws, await receive_kind(ws, 'welcome')


async def suite():
    server.players.clear(); server.guest_tokens.clear(); server.monsters.clear(); server.shots.clear(); server.events.clear()
    server.spawn_mobs()
    server.auth_verifier = FakeVerifier()
    with tempfile.TemporaryDirectory() as temp:
        database = Path(temp) / 'account.sqlite3'
        server.character_store = LocalSqliteStore(database, server.balance)
        loop_task = asyncio.create_task(server.game_loop())
        try:
            async with serve(server.handle_connection, '127.0.0.1', PORT, max_size=16384, process_request=server.process_request):
                first, welcome = await join_account()
                assert welcome['guest'] is False and 'account' in welcome['features']
                assert welcome['character']['name'] == 'หลินอิง'
                character_id = welcome['character']['id']
                actor = server.players[welcome['id']]
                monster = server.monsters['m2']
                monster.hp = monster.max_hp = 100; monster.dead = 0; monster.contributions.clear()
                shot = server.Shot(999, actor.id, 'attack', monster.x, monster.y - 78, 0, 165, 1, 1)
                server.apply_shot(shot, monster, True)
                if server.pending_persistence_tasks:
                    await asyncio.gather(*list(server.pending_persistence_tasks))
                assert (actor.level, actor.total_exp) == (1, 25)
                await first.close(); await asyncio.sleep(.1)

                # Authenticated relog does not depend on a browser resume token.
                relog, welcome2 = await join_account('ชื่อใหม่ใช้ไม่ได้', 'male_hair_01_gold')
                assert welcome2['character']['id'] == character_id
                assert welcome2['character']['avatar'] == 'female_hair_02_red'
                assert welcome2['character']['totalExp'] == 25
                await relog.close(); await asyncio.sleep(.1)

                # Simulate a process restart: clear in-memory actors and reopen the same DB.
                server.players.clear(); server.guest_tokens.clear()
                server.character_store = LocalSqliteStore(database, server.balance)
                restarted, welcome3 = await join_account('เปลี่ยนอีกครั้ง', 'male_hair_03_white')
                assert welcome3['character']['id'] == character_id
                assert welcome3['character']['totalExp'] == 25
                await restarted.send(json.dumps({'t': 'input', 'seq': 1, 'buttons': 0, 'pressed': [], 'exp': 999999}))
                try:
                    while True:
                        await asyncio.wait_for(restarted.recv(), .5)
                except ConnectionClosed as error:
                    assert error.code == 1008
                else:
                    raise AssertionError('client-provided EXP was accepted')
        finally:
            loop_task.cancel()
            await asyncio.gather(loop_task, return_exceptions=True)
    print('ACCOUNT MODE TESTS PASSED: create, relog, restart load, EXP injection rejection')


if __name__ == '__main__':
    asyncio.run(suite())
