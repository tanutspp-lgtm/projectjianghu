"""v8.0BY AOI/delta authoritative scope, resync, stable network and replay safety."""
import asyncio,json,os,subprocess,sys,time,unittest
from pathlib import Path
import server

class Delta(unittest.TestCase):
 def setUp(self):
  server.players.clear();server.monsters.clear();server.shots.clear();server.loot_drops.clear();server.events.clear()
  server.server_step=33
  self.p=server.Guest('a',120,550,1200,1200)
  self.p.protocol_delta=True
  server.players[self.p.id]=self.p
  self.b=server.Guest('b',1850,550,1200,1200)
  server.players[self.b.id]=self.b
  server.spawn_mobs()
 def tearDown(self):
  server.players.clear();server.monsters.clear();server.shots.clear();server.loot_drops.clear();server.events.clear()
 def test_scope_and_diff(self):
  world=server.snapshot()
  raw,old,full_tick,priv,inv=server.encode_aoi_delta(world,self.p,None,-1)
  message=json.loads(raw)
  self.assertTrue(message['full'])
  self.assertNotIn('b',[p['id'] for p in message['players']])
  self.assertIn('a',[p['id'] for p in message['players']])
  self.assertIn('inputAck',message['self'])
  server.server_step=36
  raw,new,full_tick2,priv2,inv2=server.encode_aoi_delta(server.snapshot(),self.p,old,full_tick,priv,inv)
  msg=json.loads(raw)
  self.assertTrue(msg['delta'])
  self.assertNotIn('inventory',msg,'identical bag should not reserialize')
  self.assertNotIn('stats',msg['self'],'unchanged stat points should not reserialize')
  self.b.x=190
  server.server_step=39
  msg=json.loads(server.encode_aoi_delta(server.snapshot(),self.p,new,full_tick,priv2,inv2)[0])
  self.assertIn('b',[p['id'] for p in msg['players']])
  # Diff must include complete new records for unseen entities.
  self.assertTrue(all('avatar' in p for p in msg['players'] if p['id']=='b'))
 def test_resume_full(self):
  world=server.snapshot(); _,old,baseline,priv,inv=server.encode_aoi_delta(world,self.p,None,-1)
  server.server_step+=160
  obj=json.loads(server.encode_aoi_delta(server.snapshot(),self.p,old,baseline,priv,inv)[0])
  self.assertTrue(obj.get('full'))
 def test_visual_scope_is_not_authority(self):
  world=server.snapshot(); v=server.aoi_view(world,self.p)
  self.assertNotIn('b',v['players'])
  self.assertIn('b',server.players,'remote player still exists for combat and simulation')
 def test_new_and_legacy_join_schema(self):
  self.assertTrue(server.valid_avatar('male_hair_01_black'))

if __name__=='__main__':unittest.main(verbosity=2)
