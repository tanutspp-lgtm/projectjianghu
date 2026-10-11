"""Local smoke/security tests. Run from this directory: python test_security.py"""
import asyncio, json, os, subprocess, sys, time
import websockets
from websockets.exceptions import ConnectionClosed

PORT = 19555
URI = f'ws://127.0.0.1:{PORT}/ws'

async def recv_type(ws, typ, timeout=3):
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        payload = json.loads(await asyncio.wait_for(ws.recv(), max(.1, until-time.monotonic())))
        if payload.get('t') == typ: return payload
    raise AssertionError('message missing '+typ)

async def rejected(data, description, initial=None):
    async with websockets.connect(URI) as ws:
        if initial:
            await ws.send(json.dumps(initial))
            await recv_type(ws,'welcome')
        await ws.send(json.dumps(data))
        try:
            for _ in range(15):
                await asyncio.wait_for(ws.recv(), .5)
        except ConnectionClosed as e:
            assert e.code==1008,(description,e.code)
        else:raise AssertionError(description+' accepted!')

async def suite():
    await rejected({'t':'join','avatar':'male_hair_98_gold'},'invented sprite')
    await rejected({'t':'join','avatar':'male_hair_01_black','admin':True},'join extra field')
    valid={'t':'join','avatar':'male_hair_01_black'}
    await rejected({'t':'input','seq':1,'buttons':0,'pressed':[], 'x':100000,'hp':999999,'damage':999999},'teleport HP damage injection',valid)
    await rejected({'t':'input','seq':1,'buttons':32,'pressed':[]},'invalid control bits',valid)
    await rejected({'t':'input','seq':1,'buttons':0,'pressed':['spawn_mobs']},'monsters manipulation',valid)
    await rejected({'t':'input','seq':1,'buttons':0,'pressed':['attack','attack']},'duplicate actions',valid)
    async with websockets.connect(URI) as ws:
        await ws.send(json.dumps(valid)); await recv_type(ws,'welcome')
        await ws.send(json.dumps({'t':'input','seq':1,'buttons':2,'pressed':[]}))
        await ws.send(json.dumps({'t':'input','seq':1,'buttons':2,'pressed':[]}))
        try:
            while True:await asyncio.wait_for(ws.recv(),1)
        except ConnectionClosed as e:
            assert e.code==1008,('sequence replay', e.code)
    async with websockets.connect(URI) as a, websockets.connect(URI) as b:
        await a.send(json.dumps(valid))
        await b.send(json.dumps({'t':'join','avatar':'female_hair_03_red'}))
        await recv_type(a,'welcome'); await recv_type(b,'welcome')
        snap=await recv_type(a,'snapshot')
        assert len(snap['players'])==2 and len(snap['mobs'])==5
        before=snap['mobs'][0]['x']
        await a.send(json.dumps({'t':'input','seq':1,'buttons':2,'pressed':[]}))
        await asyncio.sleep(.23)
        snap=await recv_type(b,'snapshot')
        assert len(snap['players'])==2
        assert 0 <= snap['mobs'][0]['x'] <= 2060
        print('two players synchronized; server still owns monster positions',before)
    print('SECURITY TESTS PASSED: malformed packets, spoofed stats/coords, invalid actions, replay, shared state')

def run():
    env={**os.environ, 'PORT':str(PORT)}
    proc=subprocess.Popen([sys.executable,'-u','server.py'],cwd=os.path.dirname(__file__),env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    try:
        time.sleep(1)
        if proc.poll() is not None:raise RuntimeError(proc.stdout.read())
        asyncio.run(suite())
    finally:
        proc.terminate()
        try:proc.wait(3)
        except subprocess.TimeoutExpired:proc.kill()

if __name__=='__main__':run()
