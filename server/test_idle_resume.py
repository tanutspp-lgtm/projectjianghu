"""Four idle guest tabs + resume and session security regression."""
import asyncio, json, os, subprocess, sys, time
import websockets
from websockets.exceptions import ConnectionClosed
PORT=19556
URI=f'ws://127.0.0.1:{PORT}/ws'
async def receive_kind(ws, kind, timeout=4):
  end=time.monotonic()+timeout
  while time.monotonic()<end:
    m=json.loads(await asyncio.wait_for(ws.recv(), timeout=max(.1,end-time.monotonic())))
    if m.get('t')==kind:return m
  raise AssertionError('missing '+kind)
async def main():
  conns=[]
  try:
    for idx in range(4):
      ws=await websockets.connect(URI, max_queue=4)
      await ws.send(json.dumps({'t':'join','avatar':'female_hair_02_red' if idx%2 else 'male_hair_01_black'}))
      wel=await receive_kind(ws,'welcome')
      snap=await receive_kind(ws,'snapshot')
      conns.append((ws,wel))
    assert len({w['id'] for _,w in conns})==4
    assert all('resume' in w for _,w in conns)
    print('4 simultaneous guests: OK', flush=True)
    first,wel=conns[0]
    await first.send(json.dumps({'t':'input','seq':1,'buttons':2,'pressed':[]}))
    await asyncio.sleep(.23)
    await first.send(json.dumps({'t':'input','seq':2,'buttons':0,'pressed':[]}))
    snap=await receive_kind(first,'snapshot')
    x_start=next(p['x'] for p in snap['players'] if p['id']==wel['id'])
    await asyncio.sleep(3)
    snap=await receive_kind(first,'snapshot')
    x_still=next(p['x'] for p in snap['players'] if p['id']==wel['id'])
    assert abs(x_still-x_start)<40,(x_start,x_still)
    print('AFK does not keep moving: OK', flush=True)
    # A background tab sends NO user inputs. Browser sockets that can still receive
    # snapshots should stay connected; a truly suspended tab reconnects on focus.
    latest=[None]*len(conns)
    async def consume(i,ws):
      try:
        async for raw in ws:
          msg=json.loads(raw)
          if msg.get('t')=='snapshot':latest[i]=msg
      except ConnectionClosed:
        pass
    watchers=[asyncio.create_task(consume(i,ws)) for i,(ws,_) in enumerate(conns)]
    await asyncio.sleep(26)
    for i,(ws,w) in enumerate(conns):
      assert latest[i] is not None,(i,'no snapshots')
      assert len(latest[i]['players'])==4,(w['id'],len(latest[i]['players']))
      waiter=await ws.ping();await asyncio.wait_for(waiter,2)
    print('4 idle guests for 29+ seconds (with no user input): OK',flush=True)
    # A secret cannot displace its owner while still connected.
    async with websockets.connect(URI) as attacker:
      await attacker.send(json.dumps({'t':'join','avatar':'male_hair_01_black','resume':wel['resume']}))
      try: await receive_kind(attacker,'welcome',timeout=1)
      except ConnectionClosed as err: assert err.code==1013,err
      else: raise AssertionError('active session stolen')
    print('Live session token takeover rejected: OK',flush=True)
    p1=next(p for p in latest[0]['players'] if p['id']==wel['id'])
    await first.close()
    # Ensure old socket is fully closed server side before connecting again.
    await asyncio.sleep(.2)
    recovered=await websockets.connect(URI)
    await recovered.send(json.dumps({'t':'join','avatar':'male_hair_01_black','resume':wel['resume']}))
    wel2=await receive_kind(recovered,'welcome')
    assert wel2['id']==wel['id'],(wel2,wel)
    assert wel2['resume']==wel['resume']
    snap=await receive_kind(recovered,'snapshot')
    p2=next(p for p in snap['players'] if p['id']==wel['id'])
    assert abs(p1['x']-p2['x'])<30,(p1['x'],p2['x'])
    print('Reconnect restored same guest and coordinates: OK',flush=True)
    await recovered.close()
    for w in watchers:w.cancel()
    await asyncio.gather(*watchers,return_exceptions=True)
  finally:
    for ws,_ in conns:
      await ws.close()

def run():
  env={**os.environ,'PORT':str(PORT)}
  proc=subprocess.Popen([sys.executable,'-u','server.py'],cwd=os.path.dirname(__file__),env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
  try:
    time.sleep(1.25)
    if proc.poll() is not None: raise RuntimeError(proc.stdout.read())
    asyncio.run(main())
  finally:
    proc.terminate()
    try:proc.wait(3)
    except subprocess.TimeoutExpired:proc.kill()
    print('server terminated',flush=True)
if __name__=='__main__':run()
