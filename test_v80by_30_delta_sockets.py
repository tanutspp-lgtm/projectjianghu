"""BY 30 independent local WS connections; server-owned auto and 10Hz snapshots."""
import asyncio,json,os,subprocess,sys,time
import websockets

PORT=19682
async def guest(i):
    async with websockets.connect(f'ws://127.0.0.1:{PORT}/ws',max_size=1_000_000) as ws:
        await ws.send(json.dumps({'t':'join','avatar':'male_hair_01_black','protocol':'aoi-delta-v80by'}))
        j=json.loads(await asyncio.wait_for(ws.recv(),4))
        assert j['t']=='welcome',(i,j)
        await ws.send(json.dumps({'t':'auto','enabled':True}))
        received=0;bytes_read=0;auto=False
        end=time.monotonic()+2.2
        while time.monotonic()<end:
            raw=await asyncio.wait_for(ws.recv(),4)
            if raw.startswith('{"t":"snapshot"'):
                received+=1;bytes_read+=len(raw)
                if received==1:
                    d=json.loads(raw)
                    own=next(p for p in d['players'] if p['id']==j['id'])
                    auto=bool(d.get('self',{}).get('auto'))
        return received,bytes_read,auto

async def suite():
    results=await asyncio.wait_for(asyncio.gather(*(guest(i) for i in range(30))),timeout=18)
    count=sum(x[0] for x in results);size=sum(x[1] for x in results)
    assert all(x[0]>=12 and x[2] for x in results),[x for x in results if x[0]<12 or not x[2]]
    print(f'PASS 30 real WS clients with server AUTO; {count} snapshots in ~2.2s; {size/1024/1024:.2f} MiB total received; min {min(x[0] for x in results)}')

def run():
    env={**os.environ,'PORT':str(PORT),'SUPABASE_URL':'','PYTHONDONTWRITEBYTECODE':'1'}
    proc=subprocess.Popen([sys.executable,'-u','server.py'],cwd=os.path.dirname(__file__),env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    try:
        time.sleep(1.2)
        if proc.poll() is not None:raise RuntimeError(proc.stdout.read())
        asyncio.run(suite())
    finally:
        proc.terminate()
        try:proc.wait(timeout=3)
        except subprocess.TimeoutExpired:proc.kill()
if __name__=='__main__':run()
