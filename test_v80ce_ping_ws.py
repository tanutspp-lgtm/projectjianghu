"""Executable integration: true websocket RTT probe, no simulation authority."""
import asyncio,json,os,subprocess,sys,time
import websockets
PORT=19873
async def do_test():
    uri=f'ws://127.0.0.1:{PORT}/ws'
    async with websockets.connect(uri,max_size=2_000_000) as ws:
        await ws.send(json.dumps({'t':'join','avatar':'male_hair_01_black','protocol':'aoi-delta-v80by'}))
        got=json.loads(await asyncio.wait_for(ws.recv(),3))
        assert got['t']=='welcome' and 'rtt-probe-v80ce' in got['features'],got
        await ws.send(json.dumps({'t':'ping','nonce':107}))
        replies=[]
        while len(replies)<1:
            m=json.loads(await asyncio.wait_for(ws.recv(),3))
            if m.get('t')=='pong':replies.append(m)
        assert replies==[{'t':'pong','nonce':107}],replies
        # RTT measurement never mutates the authoritative actor or input seq.
        await ws.send(json.dumps({'t':'input','seq':1,'buttons':2,'pressed':[]}))
        await ws.send(json.dumps({'t':'ping','nonce':108}))
        while True:
            m=json.loads(await asyncio.wait_for(ws.recv(),3))
            if m.get('t')=='pong':
                assert m['nonce']==108
                break
        await ws.send(json.dumps({'t':'ping','nonce':-1}))
        try:
            await asyncio.wait_for(ws.recv(),3)
            # buffered snapshot may arrive before close; next recv must close
            await asyncio.wait_for(ws.recv(),3)
        except websockets.exceptions.ConnectionClosed as e:
            assert e.code==1008,e
            print('PASS v8.0CE WS RTT ping/nonce, input interoperability, invalid probe closed')
            return
        raise AssertionError('bad ping payload must close connection')

def main():
    env={**os.environ,'PORT':str(PORT),'SUPABASE_URL':'','PYTHONDONTWRITEBYTECODE':'1'}
    proc=subprocess.Popen([sys.executable,'-u','server.py'],cwd=os.path.dirname(__file__),env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    try:
        time.sleep(.85)
        if proc.poll() is not None:raise RuntimeError(proc.stdout.read())
        asyncio.run(do_test())
    finally:
        proc.terminate()
        try:proc.wait(3)
        except subprocess.TimeoutExpired:proc.kill()
if __name__=='__main__':main()
