"""CK regression: 30 real WS AUTO join and close, no ghost guests, normal 10Hz streams.
Uses actual server code on isolated localhost; never hits live Render.
"""
import asyncio,json,os,subprocess,sys,time
import websockets
PORT=19741
URL=f'ws://127.0.0.1:{PORT}/ws'

async def suite():
    async with websockets.connect(URL,max_size=1_000_000) as observer:
        await observer.send(json.dumps({'t':'join','avatar':'female_hair_01_black','protocol':'aoi-delta-v80by'}))
        j=json.loads(await asyncio.wait_for(observer.recv(),3));assert j['t']=='welcome'
        def full_state(x):
            return x.get('self',{}).get('performance',{}).get('playerCount')
        clients=await asyncio.gather(*(websockets.connect(URL,max_size=1_000_000) for _ in range(30)))
        async def prep(i,ws):
            await ws.send(json.dumps({'t':'join','avatar':'male_hair_01_black','protocol':'aoi-delta-v80by'}))
            m=json.loads(await asyncio.wait_for(ws.recv(),5));assert m['t']=='welcome', (i,m)
            await ws.send(json.dumps({'t':'auto','enabled':True}))
        await asyncio.gather(*(prep(i,w) for i,w in enumerate(clients)))
        async def watch(ws):
            try:
                async for raw in ws:pass # local client consumes without JSON parsing, like browser stress test
            except websockets.ConnectionClosed:pass
        reader_tasks=[asyncio.create_task(watch(w)) for w in clients]
        seen_max=0
        before=time.monotonic()+4
        while time.monotonic()<before:
            msg=json.loads(await asyncio.wait_for(observer.recv(),4))
            if msg.get('t')=='snapshot' and (v:=full_state(msg)) is not None:seen_max=max(seen_max,v)
            if seen_max>=31:break
        assert seen_max>=31, f'Expected >=31 server clients before Clear: {seen_max}'
        start=time.monotonic()
        await asyncio.wait_for(asyncio.gather(*(ws.close(code=1000,reason='Load test stop') for ws in clients)),10)
        await asyncio.gather(*reader_tasks)
        seen=[]
        deadline=time.monotonic()+10
        while time.monotonic()<deadline:
            msg=json.loads(await asyncio.wait_for(observer.recv(),3))
            if msg.get('t')=='snapshot' and (v:=full_state(msg)) is not None:
                seen.append(v)
                if v==1:break
        assert seen and seen[-1]==1, f'ghost guests after Clear: {seen[-10:]}'
        print(f'PASS 30 real AUTO websocket guests; serverCount {seen_max}->1 after clear in {time.monotonic()-start:.2f}s; no ghost clients')

def run():
    env={**os.environ,'PORT':str(PORT),'SUPABASE_URL':'','PYTHONDONTWRITEBYTECODE':'1'}
    p=subprocess.Popen([sys.executable,'-u','server.py'],cwd=os.path.dirname(__file__),env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    try:
        time.sleep(1.0)
        if p.poll() is not None:raise RuntimeError(p.stdout.read())
        asyncio.run(asyncio.wait_for(suite(),20))
    finally:
        p.terminate()
        try:p.wait(timeout=3)
        except subprocess.TimeoutExpired:p.kill()
if __name__=='__main__':run()
