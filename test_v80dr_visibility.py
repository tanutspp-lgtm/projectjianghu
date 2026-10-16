"""v8.0DR loopback WebSocket integration: visibility must not depend on AUTO."""
import asyncio,json,unittest
import server
from websockets.asyncio.client import connect
from websockets.asyncio.server import serve
from websockets.extensions.permessage_deflate import ServerPerMessageDeflateFactory

async def collect_snapshots(client, seconds):
    packets=[]
    end=asyncio.get_running_loop().time()+seconds
    while True:
        remaining=end-asyncio.get_running_loop().time()
        if remaining<=0: break
        try:
            m=json.loads(await asyncio.wait_for(client.recv(),remaining))
            if m.get('t')=='snapshot':packets.append(m)
        except asyncio.TimeoutError: break
    return packets

async def test_visibility(deflate):
    server.players.clear();server.monsters.clear();server.shots.clear();server.loot_drops.clear();server.events.clear()
    server.server_step=0; server.spawn_mobs()
    extensions=[ServerPerMessageDeflateFactory(compress_settings={'level':1,'memLevel':5})] if deflate else None
    async with serve(server.handle_connection,'127.0.0.1',0,extensions=extensions,compression=None,ping_interval=None,max_size=2048) as srv:
        url=f"ws://127.0.0.1:{srv.sockets[0].getsockname()[1]}"
        async with connect(url,ping_interval=None) as ws:
            await ws.send(json.dumps({'t':'join','avatar':'male_hair_01_black','protocol':'aoi-delta-v80by'}))
            welcome=json.loads(await asyncio.wait_for(ws.recv(),3))
            assert 'view-mode-all-v80dr' in welcome['features']
            if deflate:assert ws.protocol.extensions
            simulation=asyncio.create_task(server.game_loop())
            guest=server.players[welcome['id']]
            try:
                # Idle/manual guest, tab hidden: should reduce without AUTO.
                await ws.send('{"t":"view_mode","mode":"background"}')
                hidden=await collect_snapshots(ws,2.25)
                assert guest.view_mode=='background' and guest.auto_state.enabled is False
                assert 1<=len(hidden)<=4,('idle hidden snapshots',len(hidden))
                # Foreground resumes at 10Hz without enabling AUTO.
                await ws.send('{"t":"view_mode","mode":"active"}')
                foreground=await collect_snapshots(ws,1.25)
                assert len(foreground)>=7,('idle active snapshots',len(foreground))
                # AUTO enabled in background, then disabled, must REMAIN background.
                await ws.send(json.dumps({'t':'auto','enabled':True}))
                await ws.send('{"t":"view_mode","mode":"background"}')
                auto_hidden=await collect_snapshots(ws,2.15)
                assert guest.auto_state.enabled is True
                assert guest.view_mode=='background'
                assert 1<=len(auto_hidden)<=4,('AUTO hidden snapshots',len(auto_hidden))
                await ws.send('{"t":"auto","enabled":false}')
                auto_off_hidden=await collect_snapshots(ws,2.1)
                assert guest.auto_state.enabled is False and guest.view_mode=='background',('auto off must not reactivate view')
                assert 1<=len(auto_off_hidden)<=4,('auto OFF hidden',len(auto_off_hidden))
                await ws.send('{"t":"view_mode","mode":"active"}')
                resumed=await collect_snapshots(ws,1.2)
                assert len(resumed)>=7,('resumed snapshots',len(resumed))
                return tuple(map(len,(hidden,foreground,auto_hidden,auto_off_hidden,resumed)))
            finally:
                simulation.cancel()
                try:await simulation
                except asyncio.CancelledError:pass

class VisibilityAllUsers(unittest.TestCase):
    def test_ws_no_compression(self): print('NO_DEFLATE',asyncio.run(test_visibility(False)))
    def test_ws_deflate(self): print('DEFLATE',asyncio.run(test_visibility(True)))

if __name__=='__main__':unittest.main(verbosity=2)
