"""BZ performance invariants: spatial target selection, cached immutable stats, metrics."""
import unittest,random,json,time
import server

class PerformanceRegression(unittest.TestCase):
 def setUp(self):
  server.players.clear();server.monsters.clear();server.shots.clear()
  server.events.clear();server.loot_drops.clear();server.server_step=3
 def tearDown(self):
  server.players.clear();server.monsters.clear();server.shots.clear()
  server.events.clear();server.loot_drops.clear()
 def test_spatial_grid_matches_full_scan_across_random_30(self):
  rng=random.Random(42)
  server.spawn_mobs()
  for i in range(30):
   x=rng.uniform(27,2030);y=rng.choice([235.,390.,550.])
   server.players[str(i)]=server.Guest(str(i),x,y,1200,1200)
  for _ in range(25):
   for p in server.players.values():
    p.x=rng.uniform(27,2030)
    p.y=rng.choice([235.,390.,550.])
   grid=server.index_players_by_x()
   for m in server.monsters.values():
    a=min((p for p in server.players.values() if server.reachable_player(m,p) and abs(p.x-m.x)<server.BEAST_AGGRO+65),key=lambda p:abs(p.x-m.x),default=None)
    b=min((p for p in server.candidate_players_by_x(m,grid) if server.reachable_player(m,p) and abs(p.x-m.x)<server.BEAST_AGGRO+65),key=lambda p:abs(p.x-m.x),default=None)
    self.assertEqual(a.id if a else None,b.id if b else None)
 def test_private_derived_cache_invalidated_when_stats_and_gear_change(self):
  p=server.Guest('p',175,550,1200,1200)
  a=server.derived_for_snapshot(p)
  self.assertIs(a,server.derived_for_snapshot(p))
  p.stats['int']+=1
  b=server.derived_for_snapshot(p)
  self.assertIsNot(a,b)
  self.assertEqual(b['effectiveStats']['int'],a['effectiveStats']['int']+1)
  p.gear_enhancement+=1
  self.assertIsNot(b,server.derived_for_snapshot(p))
 def test_deltas_do_not_send_static_character_data_every_time(self):
  p=server.Guest('p',175,550,1200,1200)
  server.players[p.id]=p
  server.spawn_mobs()
  raw,old,full_tick,prev,inv=server.encode_aoi_delta(server.snapshot(),p,None,-1)
  self.assertIn('performance',json.loads(raw)['self'])
  server.server_step+=3
  raw,*_=server.encode_aoi_delta(server.snapshot(),p,old,full_tick,prev,inv)
  body=json.loads(raw)
  self.assertNotIn('derived',body.get('self',{}))
  self.assertNotIn('performance',body.get('self',{}))
 def test_perf_rollup_safe_when_no_ticks(self):
  server.perf_ticks.clear()
  server.perf_last_report=time.monotonic()-2
  server.performance_rollup(time.monotonic())
  self.assertEqual(server.perf_data['tickP95Ms'],0)

if __name__=='__main__':unittest.main(verbosity=2)
