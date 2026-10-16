import asyncio,json,unittest
from unittest import mock
import server
from websockets.asyncio.client import connect
from websockets.asyncio.server import serve
from websockets.extensions.permessage_deflate import ServerPerMessageDeflateFactory

async def run_test(deflate=False):
    server.players.clear();server.monsters.clear();server.shots.clear();server.loot_drops.clear();server.events.clear()
    server.server_step=0
    server.spawn_mobs()
    ext=[ServerPerMessageDeflateFactory(compress_settings={'level':1,'memLevel':5})] if deflate else None
    async with serve(server.handle_connection,'127.0.0.1',0,extensions=ext,compression=None,ping_interval=None,max_size=2048) as wsserver:
        port=wsserver.sockets[0].getsockname()[1]
        async with connect(f'ws://127.0.0.1:{port}',ping_interval=None) as client:
            await client.send(json.dumps({'t':'join','avatar':'male_hair_01_black','protocol':'aoi-delta-v80by'}))
            welcome=json.loads(await asyncio.wait_for(client.recv(),3)); assert welcome['t']=='welcome',welcome
            assert 'view-mode-v80dp' in welcome['features']
            server_task=asyncio.create_task(server.game_loop())
            try:
                await client.send(json.dumps({'t':'auto','enabled':True}))
                await client.send(json.dumps({'t':'view_mode','mode':'background'}))
                # Count background stream for >2s, at 1Hz target.
                bg=[]
                end=asyncio.get_running_loop().time()+2.25
                while asyncio.get_running_loop().time()<end:
                    try:
                        msg=json.loads(await asyncio.wait_for(client.recv(),end-asyncio.get_running_loop().time()))
                        if msg.get('t')=='snapshot':bg.append(msg)
                    except asyncio.TimeoutError:break
                assert 1<=len(bg)<=4,('background snapshot count',len(bg))
                assert server.players[welcome['id']].auto_state.enabled is True
                assert server.players[welcome['id']].view_mode=='background'
                await client.send(json.dumps({'t':'view_mode','mode':'active'}))
                active=[]
                end=asyncio.get_running_loop().time()+1.25
                while asyncio.get_running_loop().time()<end:
                    try:
                        msg=json.loads(await asyncio.wait_for(client.recv(),end-asyncio.get_running_loop().time()))
                        if msg.get('t')=='snapshot':active.append(msg)
                    except asyncio.TimeoutError:break
                assert len(active)>=7,('active snapshot count',len(active))
                assert server.players[welcome['id']].view_mode=='active'
                # No crash with negotiated deflate.
                if deflate: assert client.protocol.extensions,('no negotiated compression')
                return len(bg),len(active)
            finally:
                server_task.cancel()
                try:await server_task
                except asyncio.CancelledError:pass
    server.players.clear()

class AllDayAuto(unittest.TestCase):
    def test_ws_mode_no_compression(self):self.assertIsInstance(asyncio.run(run_test(False)),tuple)
    def test_ws_mode_with_deflate(self):self.assertIsInstance(asyncio.run(run_test(True)),tuple)

if __name__=='__main__':unittest.main(verbosity=2)
