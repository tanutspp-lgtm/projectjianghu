"""Server monster behavior and actual 30-client authoritative world snapshots."""
import asyncio, json, os, subprocess, sys, time
from pathlib import Path
import server
import websockets
PORT=19556

def unit():
    server.players.clear();server.monsters.clear();server.shots.clear();server.spawn_mobs()
    assert len(server.monsters)==20
    assert {m.species for m in server.monsters.values()}=={'wolf','boar'}
    assert sum(m.species=='boar' for m in server.monsters.values())==6
    assert sum(m.species=='wolf' for m in server.monsters.values())==14
    for _ in range(30*12):
        for m in server.monsters.values():server.update_mob(m,1/30)
    assert all(server.own_lane(m) is not None for m in server.monsters.values())
    # The same server hit recoil that Offline relies on.
    p=server.Guest('test',200,550,1300,1300)
    server.hurt(p,75,230,550,'monster')
    assert p.kb_time==.28 and p.kb_dir==-1 and p.inv==1.12 and p.vy==-240
    # Offline synchronized wave mechanic: never respawn immediately.
    m=next(iter(server.monsters.values()));server.hurt(m,m.hp,200,550,'attack')
    assert m.dead>=5.0
    assert m.bite_started_at<0
    print('PASS: 20 slots, 14 wolves / 6 boars, valid platforms, bite recoil, wave respawn')

async def recv_kind(ws,t,timeout=4):
    end=time.monotonic()+timeout
    while True:
        r=json.loads(await asyncio.wait_for(ws.recv(),end-time.monotonic()))
        if r.get('t')==t:return r

async def recv_full_world(ws,timeout=8):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        msg=json.loads(await asyncio.wait_for(ws.recv(),end-time.monotonic()))
        if msg.get('t')=='snapshot' and len(msg['players'])==30 and len(msg['mobs'])==20:
            return msg
    raise AssertionError('world never reached 30 players + 20 beasts')

async def integration():
    wslist=[]
    try:
        for i in range(30):
            ws=await websockets.connect(f'ws://127.0.0.1:{PORT}/ws',compression=None)
            wslist.append(ws)
            await ws.send(json.dumps({'t':'join','avatar':'male_hair_01_black'}))
            w=await recv_kind(ws,'welcome')
            assert 'beast-v80bq' in w.get('features',[])
        snaps=await asyncio.gather(*(recv_full_world(ws) for ws in wslist))
        assert all(len(s['players'])==30 and len(s['mobs'])==20 for s in snaps)
        assert all(sum(m['species']=='boar' for m in s['mobs'])==6 for s in snaps)
        for i,ws in enumerate(wslist):
            await ws.send(json.dumps({'t':'input','seq':1,'buttons':2 if i%2 else 1,'pressed':['attack']}))
        snaps=await asyncio.gather(*(recv_full_world(ws) for ws in wslist))
        print('PASS: 30 WebSockets, 30 players + 20 server monsters, attack intents and snapshots')
        print('snapshot_bytes_30_players_20_monsters:',len(json.dumps(snaps[0])))
    finally:
        await asyncio.gather(*(ws.close() for ws in wslist),return_exceptions=True)

def run():
    unit()
    proc=subprocess.Popen([sys.executable,'-u','server.py'],cwd=Path(__file__).parent,env={**os.environ,'PORT':str(PORT),'SUPABASE_URL':''},stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    try:
        time.sleep(.75)
        if proc.poll() is not None:raise RuntimeError(proc.stdout.read())
        asyncio.run(integration())
    finally:
        proc.terminate()
        try:proc.wait(timeout=3)
        except subprocess.TimeoutExpired:proc.kill()
if __name__=='__main__':run()
