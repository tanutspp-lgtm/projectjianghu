"""Guest AUTO PvE smoke + protocol safety checks, no fake damage/coords permitted."""
import asyncio, json, os, subprocess, sys, time
import websockets
from websockets.exceptions import ConnectionClosed
PORT=19556
URL=f'ws://127.0.0.1:{PORT}/ws'
async def typed(ws, type_, limit=4):
    end=time.monotonic()+limit
    while time.monotonic()<end:
        pkt=json.loads(await asyncio.wait_for(ws.recv(), max(.1,end-time.monotonic())))
        if pkt.get('t')==type_:return pkt
    raise AssertionError(type_+' timeout')
async def suite():
    async with websockets.connect(URL) as w1, websockets.connect(URL) as w2:
        await w1.send(json.dumps({'t':'join','avatar':'male_hair_01_black'}))
        await w2.send(json.dumps({'t':'join','avatar':'female_hair_02_gold'}))
        hello=await typed(w1,'welcome'); await typed(w2,'welcome')
        assert 'auto' in hello['features']
        await w1.send(json.dumps({'t':'auto','enabled':True}))
        seen_auto=False; started=None; progress=False; other_lost=False
        until=time.monotonic()+7
        while time.monotonic()<until:
            snap=await typed(w2,'snapshot')
            me=next(p for p in snap['players'] if p['id']==hello['id'])
            if me['auto']:seen_auto=True
            target=next(m for m in snap['mobs'] if m['id']=='m2')
            if started is None:started=(me['x'],target['hp'])
            if target['hp']<started[1]: progress=True;break
        assert seen_auto,'auto state absent'
        assert progress,'auto did not chase and attack monster using authoritative server'
        await w1.send(json.dumps({'t':'auto','enabled':False}))
        for i in range(4):
            snap=await typed(w2,'snapshot')
            me=next(p for p in snap['players'] if p['id']==hello['id'])
            if not me['auto']:break
        assert not me['auto'],'did not turn off'
        # Invalid auto packet cannot smuggle client coordinates.
        await w1.send(json.dumps({'t':'auto','enabled':True,'x':200000,'damage':999999}))
        try:
            for i in range(20): await asyncio.wait_for(w1.recv(),.5)
        except ConnectionClosed as e: assert e.code==1008,e.code
        else: raise AssertionError('illegal autopacket accepted')
    async with websockets.connect(URL) as w:
        await w.send(json.dumps({'t':'join','avatar':'male_hair_01_black'}))
        await typed(w,'welcome')
        await w.send(json.dumps({'t':'auto','enabled':True}))
        await w.send(json.dumps({'t':'input','seq':1,'buttons':2,'pressed':[]}))
        for _ in range(10):
            snap=await typed(w,'snapshot');p=snap['players'][0]
            if not p['auto']:break
        assert not p['auto'],'manual input failed to override AUTO'
    print('AUTO TESTS PASSED: authoritative chase/attack, toggle, spoof-reject, manual override')
if __name__=='__main__':
    env={**os.environ,'PORT':str(PORT)}
    proc=subprocess.Popen([sys.executable,'-u','server.py'],cwd=os.path.dirname(__file__),env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    try:
        time.sleep(.65)
        if proc.poll() is not None:raise RuntimeError(proc.stdout.read())
        asyncio.run(suite())
    finally:
        proc.terminate()
        try:proc.wait(3)
        except subprocess.TimeoutExpired:proc.kill()
