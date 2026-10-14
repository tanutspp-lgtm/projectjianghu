"""Isolated local WebSocket red-team regression: AUTO spoofing, malformed inputs,
public Guest QA escalation, authoritative HP/DEF and 30 concurrent AUTO players.
"""
import asyncio,json,os,sys,time,subprocess
from pathlib import Path
import websockets
from websockets.exceptions import ConnectionClosed
ROOT=Path(__file__).resolve().parent;PORT=19666;URI=f'ws://127.0.0.1:{PORT}/ws'
JOIN={'t':'join','avatar':'male_hair_01_black'}
async def receive(ws,kind='snapshot',timeout=6):
    stop=time.monotonic()+timeout
    while time.monotonic()<stop:
        m=json.loads(await asyncio.wait_for(ws.recv(),max(.01,stop-time.monotonic())))
        if m.get('t')==kind:return m
    raise AssertionError('missing '+kind)
async def expect_reject(msg):
    async with websockets.connect(URI) as ws:
        await ws.send(json.dumps(JOIN));await receive(ws,'welcome')
        await ws.send(json.dumps(msg))
        try:
            while True:await asyncio.wait_for(ws.recv(),2)
        except ConnectionClosed as exc:assert exc.code==1008,(msg,exc.code)
async def run():
    for bad in ({'t':'auto','enabled':True,'x':999999,'damage':999999},
                {'t':'auto','enabled':'true'},
                {'t':'input','seq':1,'buttons':0,'pressed':[{}]},
                {'t':'input','seq':1,'buttons':0,'pressed':[['attack']]},
                {'t':'gear_preset','level':40}):
        await expect_reject(bad)
    print('PASS forged AUTO position/damage, bad toggles, unhashable actions, disabled QA gear rejected')
    ws=await websockets.connect(URI)
    try:
        await ws.send(json.dumps(JOIN));welcome=await receive(ws,'welcome')
        assert 'auto' in welcome['features'] and 'sandbox-loadouts-v80bt' not in welcome['features']
        await ws.send(json.dumps({'t':'auto','enabled':True}))
        snap=await receive(ws)
        while not snap['self']['auto']:snap=await receive(ws)
        assert snap['self']['autoTarget'] is not None
        for m in snap['mobs']:
            assert (m['level'],m['max'],m['defense'])==(5,339,4)
        initial=snap['self']['autoTarget']
        # Client tries to move manually: cancels AUTO rather than overriding server-owned position.
        await ws.send(json.dumps({'t':'input','seq':1,'buttons':2,'pressed':[]}))
        for i in range(10):
            s=await receive(ws)
            if not s['self']['auto']:break
        assert not s['self']['auto']
        print('PASS server AUTO destination and monster stats, manual input cancels AUTO')
    finally:await ws.close()
    clients=[await websockets.connect(URI) for _ in range(30)]
    try:
        for ws in clients:await ws.send(json.dumps(JOIN))
        await asyncio.gather(*(receive(ws,'welcome') for ws in clients))
        await asyncio.gather(*(ws.send(json.dumps({'t':'auto','enabled':True})) for ws in clients))
        snaps=await asyncio.gather(*(receive(ws) for ws in clients))
        assert len(snaps[0]['players'])==30 and len(snaps[0]['mobs'])==20
        assert any(s['self']['auto'] for s in snaps)
        print('PASS 30 simultaneous Guest sockets, 20 authoritative monsters, server AUTO enabled')
    finally:
        await asyncio.gather(*(ws.close() for ws in clients),return_exceptions=True)
def main():
    env={**os.environ,'PORT':str(PORT),'SUPABASE_URL':'','ENABLE_GUEST_SANDBOX':'0','MONSTER_PRESET_LEVEL':'5'}
    proc=subprocess.Popen([sys.executable,'-u','server.py'],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    try:
        time.sleep(.9)
        if proc.poll()!=None:raise RuntimeError(proc.stdout.read())
        asyncio.run(run())
    finally:
        proc.terminate()
        try:proc.wait(timeout=3)
        except subprocess.TimeoutExpired:proc.kill()
if __name__=='__main__':main()
