import unittest
import server
class TestCastVisualMetadata(unittest.TestCase):
    def setUp(self):
        server.players.clear();server.monsters.clear();server.shots.clear();server.events.clear()
        self.guest=server.Guest('self',175,550,1200,1200)
        server.players[self.guest.id]=self.guest
        server.prog.apply_derived_resources(self.guest,server.hp_reference,full=True)
    def tearDown(self):
        server.players.clear();server.monsters.clear();server.shots.clear();server.events.clear()
    def test_projectile_metadata_is_visual_only_and_matches_real_shot(self):
        self.guest.sp=self.guest.max_sp=100
        server.perform_action(self.guest,'attack')
        assert server.shots,'server must create a real authoritative shot'
        shot=server.shots[-1]
        cast=next(e for e in server.events if e['t']=='cast')
        self.assertEqual(cast['shotId'],str(shot.id))
        self.assertEqual(cast['owner'],self.guest.id)
        self.assertEqual(cast['shotX'],round(shot.x,1))
        self.assertEqual(cast['shotY'],round(shot.y,1))
        self.assertEqual(cast['shotDir'],1 if shot.vx>0 else -1)
        self.assertGreater(cast['shotSpeed'],0)
        self.assertFalse(any(key in cast for key in ('damage','hp','hit')))
if __name__=='__main__':unittest.main(verbosity=2)
