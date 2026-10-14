import asyncio,json,os,subprocess,sys,time
from pathlib import Path
import websockets
HERE=Path(__file__).resolve().parent;PORT=19607
async def read(ws,kind='snapshot',timeout=5):
    until=time.monotonic()+timeout
    while time.monotonic()<until:
        m=json.loads(await asyncio.wait_for(ws.recv(),max(.01,until-time.monotonic())))
        if m.get('t')==kind:return m
    raise TimeoutError(kind)
async def command(ws,msg):
    await ws.send(json.dumps(msg))
    ack=await read(ws,'sandbox_ack')
    assert ack['ok'],(msg,ack)
async def check():
    async with websockets.connect(f'ws://127.0.0.1:{PORT}/ws') as a,websockets.connect(f'ws://127.0.0.1:{PORT}/ws') as b:
        await a.send(json.dumps({'t':'join','avatar':'male_hair_01_black'}))
        await b.send(json.dumps({'t':'join','avatar':'female_hair_01_gold'}))
        wa=await read(a,'welcome');wb=await read(b,'welcome')
        assert 'sandbox-loadouts-v80bt' in wa['features']
        await command(a,{'t':'sandbox_level','level':60})
        await command(a,{'t':'qi_equip','id':'flute_echo','enabled':True})
        await command(a,{'t':'qi_rank','id':'flute_echo','kind':'training','value':20})
        await command(a,{'t':'qi_rank','id':'flute_echo','kind':'enhance','value':5})
        await command(a,{'t':'gear_preset','level':40})
        await command(a,{'t':'gear_enhance','value':7})
        await command(a,{'t':'gear_affix','name':'defRow','value':7})
        for _ in range(3):sa=await read(a)
        for _ in range(3):sb=await read(b)
        pa=sa['self'];pb=sb['self']
        assert pa['effectiveLevel']==40 and next(x for x in sa['players'] if x['id']==wa['id'])['level']==1 and pa['expWithinLevel']==0
        assert pa['gear']['level']==40 and pa['gear']['defRow']==7
        assert pa['qiEquipped'][0]=='flute_echo' and pa['qiRanks']['flute_echo']=={'training':20,'enhance':5}
        assert pa['derived']['defense']==267,pa['derived']
        assert pa['derived']['weaponAttack']==103,pa['derived']
        assert pa['derived']['magicDamageBonus']==53+2*(40-1),pa['derived']
        assert pb['effectiveLevel']==1 and pb['derived']['defense']==0
        assert not any('qiEquipped' in x or 'gear' in x for x in sa['players'])
        await a.send(json.dumps({'t':'gear_preset','level':40,'maxHp':999999999}))
        ack=await read(a,'sandbox_ack');assert ack['ok'] is False
        await command(a,{'t':'gear_clear'})
        for _ in range(3):sa=await read(a)
        assert sa['self']['derived']['defense']==0
        print('PASS online Guest server-owned Qi/Gear, independent guests, equip/unequip, no forged bonuses')
if __name__=='__main__':
    env={**os.environ,'PORT':str(PORT),'SUPABASE_URL':''}
    proc=subprocess.Popen([sys.executable,'-u','server.py'],cwd=HERE,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    try:
        time.sleep(.8)
        if proc.poll() is not None:raise RuntimeError(proc.stdout.read())
        asyncio.run(check())
    finally:
        proc.terminate()
        try:proc.wait(timeout=3)
        except subprocess.TimeoutExpired:proc.kill()
