"""WUXIA guest-server protocol regression tests. Run: python test_security.py"""
import asyncio, json, os, subprocess, sys, time
from pathlib import Path
import websockets
from websockets.exceptions import ConnectionClosed
PORT=19555
URI=f'ws://127.0.0.1:{PORT}/ws'
ROOT=Path(__file__).resolve().parent

async def recv_type(ws, kind, timeout=5):
    until=time.monotonic()+timeout
    while time.monotonic()<until:
        msg=json.loads(await asyncio.wait_for(ws.recv(), max(.1,until-time.monotonic())))
        if msg.get('t')==kind:return msg
    raise AssertionError('missing '+kind)

async def rejected(message, description, valid_join=None):
    async with websockets.connect(URI) as ws:
        if valid_join is not None:
            await ws.send(json.dumps(valid_join));await recv_type(ws,'welcome')
        await ws.send(json.dumps(message))
        try:
            while True:await asyncio.wait_for(ws.recv(),2)
        except ConnectionClosed as exc:
            assert exc.code==1008,(description,exc.code)

async def suite():
    join={'t':'join','avatar':'male_hair_01_black'}
    await rejected({'t':'join','avatar':'male_hair_98_gold'},'invented avatar')
    await rejected({'t':'join','avatar':'male_hair_01_black','hp':99999},'join HP injection')
    await rejected({'t':'input','seq':1,'buttons':0,'pressed':[], 'hp':999999,'damage':999999},'HP/damage injection',join)
    await rejected({'t':'input','seq':1,'buttons':32,'pressed':[]},'invalid buttons',join)
    await rejected({'t':'input','seq':1,'buttons':0,'pressed':['spawn_mobs']},'invalid action',join)
    await rejected({'t':'input','seq':1,'buttons':0,'pressed':['attack','attack']},'duplicate actions',join)
    async with websockets.connect(URI) as ws:
        await ws.send(json.dumps(join));await recv_type(ws,'welcome')
        await ws.send(json.dumps({'t':'input','seq':1,'buttons':2,'pressed':[]}))
        await ws.send(json.dumps({'t':'input','seq':1,'buttons':2,'pressed':[]}))
        try:
            while True:await asyncio.wait_for(ws.recv(),2)
        except ConnectionClosed as exc:
            assert exc.code==1008,('sequence replay',exc.code)
    async with websockets.connect(URI) as a, websockets.connect(URI) as b:
        await a.send(json.dumps(join));await b.send(json.dumps({'t':'join','avatar':'female_hair_03_red'}))
        await recv_type(a,'welcome');await recv_type(b,'welcome')
        snap=await recv_type(a,'snapshot')
        assert len(snap['players'])==2 and len(snap['mobs'])==5
        assert all(p['max']==1300 and p['level']==5 for p in snap['players'])
        print('PASS two guest clients share server-authoritative Lv5 world')
    async with websockets.connect(URI) as ws:
        await ws.send(json.dumps(join));await recv_type(ws,'welcome')
        for seq in range(1,25):
            await ws.send(json.dumps({'t':'input','seq':seq,'buttons':0,'pressed':['attack']}))
        try:
            while True:await asyncio.wait_for(ws.recv(),2)
        except ConnectionClosed as exc:
            assert exc.code==1008,('rate limit',exc.code)
        print('PASS flood disconnected by server')
    print('SECURITY TESTS PASSED')

def run():
    env={**os.environ,'PORT':str(PORT),'SUPABASE_URL':''}
    proc=subprocess.Popen([sys.executable,'-u','server.py'],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    try:
        time.sleep(1.1)
        if proc.poll() is not None:raise RuntimeError(proc.stdout.read())
        asyncio.run(suite())
    finally:
        proc.terminate()
        try:proc.wait(timeout=3)
        except subprocess.TimeoutExpired:proc.kill()
if __name__=='__main__':run()
