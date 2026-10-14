"""Offline server regression: client sockets stalled must not slow world tick."""
import asyncio
import unittest
import server
class SlowSocket:
    def __init__(self):self.sent=0;self.closed=False
    async def send(self,s):self.sent+=1;await asyncio.sleep(2.0)
    async def close(self,**kw):self.closed=True

async def suite():
    server.players.clear();server.monsters.clear();server.shots.clear();server.events.clear()
    server.server_step=0;server.spawn_mobs()
    clients=[]
    for i in range(30):
        p=server.Guest(id='sim-'+str(i),x=180+i*2,y=550,hp=1200,max_hp=1200,ws=SlowSocket())
        server.players[p.id]=p
        p.snapshot_task=asyncio.create_task(server.snapshot_writer(p))
        clients.append(p)
    task=asyncio.create_task(server.game_loop())
    await asyncio.sleep(.55)
    tick=server.server_step
    task.cancel()
    try:await task
    except asyncio.CancelledError:pass
    for p in clients:
        assert p.snapshot_outbox.qsize()<=1
        p.snapshot_task.cancel()
        try:await p.snapshot_task
        except asyncio.CancelledError:pass
    server.players.clear();server.monsters.clear();server.shots.clear()
    assert tick>=11, ('slow clients stalled authoritative loop',tick)
    print('PASS 30 stalled WS clients; %s ticks in 0.55s (~%.1f Hz), bounded queue <=1' %(tick,tick/.55))

if __name__=='__main__':asyncio.run(suite())
