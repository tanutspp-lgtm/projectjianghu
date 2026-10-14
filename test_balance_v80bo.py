"""PvP-first 60-level balance and 1000-action flood regression. Run: python test_balance_v80bo.py"""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import server

class Balance(unittest.TestCase):
 def setUp(self):
  server._remote_hp=None
  server._remote_attacks=None
  server.players.clear()
  server.monsters.clear()
  server.shots.clear()
 def test_hp_anchors(self):
  for level,hp in server.ANCHORS:self.assertEqual(server.hp_reference(level)['max_hp'],hp)
 def test_zones_every_level(self):
  for level in range(1,61):
   ref=server.hp_reference(level)
   for (mode,human),(lo,hi) in server.PCT.items():
    a,b=server.monster_attack_range(level,mode,human)
    self.assertGreater(a,0)
    self.assertLessEqual(a,b)
    min_pct=100*server.mitigate(a,ref['defense_7'])/ref['max_hp']
    max_pct=100*server.mitigate(b,ref['defense_0'])/ref['max_hp']
    self.assertAlmostEqual(min_pct,lo,delta=.3)
    self.assertAlmostEqual(max_pct,hi,delta=1.0)
 def test_defense(self):
  self.assertEqual(server.mitigate(501,197),280)
 def test_attack_burst_is_not_queued(self):
  p=server.Guest('unit',175,550,1300,1300)
  for _ in range(1000):server.perform_action(p,'attack')
  self.assertEqual(len(server.shots),1)
  p.cool=0
  for _ in range(500):server.perform_action(p,'attack')
  self.assertEqual(len(server.shots),1)
 def test_server_owns_level_and_armor(self):
  server.spawn_mobs()
  self.assertEqual(len(server.monsters),20)
  self.assertTrue(all(1<=m.level<=5 and m.zone_mode=='common' for m in server.monsters.values()))

if __name__=='__main__':unittest.main(verbosity=2)
