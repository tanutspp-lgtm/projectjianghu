"""Integration smoke test for v8.0BS private self/inventory + validation and cast events."""
import asyncio,subprocess,sys,time,os,json
from pathlib import Path
import websockets
from websockets.exceptions import ConnectionClosed
HERE=Path(__file__).resolve().parent
PORT=19603

def valid_avatar(name):return {'t':'join','avatar':name}
async def get(ws,kind,timeout=5):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  d=json.loads(await asyncio.wait_for(ws.recv(),end-time.monotonic()))
  if d.get('t')==kind:return d
 raise AssertionError('missing '+kind)
async def check():
 async with websockets.connect(f'ws://127.0.0.1:{PORT}/ws') as a,websockets.connect(f'ws://127.0.0.1:{PORT}/ws') as b:
  await a.send(json.dumps(valid_avatar('male_hair_01_black'))); await b.send(json.dumps(valid_avatar('female_hair_01_gold')))
  wa=await get(a,'welcome');wb=await get(b,'welcome')
  assert 'progression-v80bs' in wa['features'] and 'progression-v80bs' in wb['features']
  sa=await get(a,'snapshot');sb=await get(b,'snapshot')
  assert len(sa['players'])==2 and len(sb['players'])==2 and len(sa['mobs'])==20
  assert sa['self']['statPoints']==0 and sb['self']['skillPoints']==0
  assert sa['self']['expToNext']==3000 and sa['self']['stats']['vit']==0
  assert sa['self']['maxSp']==100 and sa['self']['maxSta']==100
  assert sa['inventory']==[] and sb['inventory']==[]
  assert not any('stats' in x or 'inventory' in x for x in sa['players'])
  await a.send(json.dumps({'t':'stat_add','stat':'vit','amount':1}));ack=await get(a,'progression_ack');assert ack['ok'] is False
  await a.send(json.dumps({'t':'skill_up','skill':'mastery','amount':1}));ack=await get(a,'progression_ack');assert ack['ok'] is False
  sa=await get(a,'snapshot')
  assert sa['self']['stats']['vit']==0 and sa['self']['skillRanks']['mastery']==0
  await a.send(json.dumps({'t':'input','seq':1,'buttons':0,'pressed':['attack']}))
  # Flute cast event is server-origin and visible; not fired client-side until accepted.
  end=time.monotonic()+5;cast=False
  while time.monotonic()<end:
   d=await get(a,'snapshot')
   if any(e.get('t')=='cast' and e.get('kind')=='attack' for e in d['events']):cast=True;break
  assert cast,'server cast event not delivered'
  print('PASS two guests, private progression/inventory, Lv1 threshold, invalid upgrades, authoritative flute cast')
if __name__=='__main__':
 proc=subprocess.Popen([sys.executable,'-u','server.py'],cwd=HERE,env={**os.environ,'PORT':str(PORT),'SUPABASE_URL':''},stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 try:
  time.sleep(.9)
  if proc.poll() is not None:raise RuntimeError(proc.stdout.read())
  asyncio.run(check())
 finally:
  proc.terminate()
  try:proc.wait(timeout=3)
  except subprocess.TimeoutExpired:proc.kill()
