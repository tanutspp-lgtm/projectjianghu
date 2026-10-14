import unittest
import server

class TestV80CDProtocol(unittest.TestCase):
    def test_ladder_geometry(self):
        self.assertEqual(server.CLIMBS,((510,235,550),(1170,390,550),(1590,235,550)))
    def test_shot_wire_id_and_delta(self):
        orig_players=server.players.copy();orig_shots=list(server.shots);orig_events=list(server.events);orig_monsters=server.monsters.copy()
        try:
            server.players.clear();server.shots.clear();server.events.clear();server.monsters.clear()
            a=server.Guest('g-test',175,550,1200,1200)
            server.prog.apply_derived_resources(a,server.hp_reference,full=True)
            server.players[a.id]=a
            server.perform_action(a,'attack')
            self.assertTrue(server.shots)
            shot=server.shots[-1]
            obj=server.snapshot()
            self.assertEqual(obj['shots'][0]['id'],str(shot.id))
            self.assertEqual(type(obj['shots'][0]['id']),str)
            event=next(x for x in obj['events'] if x['t']=='cast')
            self.assertEqual(event['shotId'],str(shot.id))
            visible=server.aoi_view(obj,a)
            self.assertIn(str(shot.id),visible['shots'])
            # The next snapshots must retain identity and updated x for the very same projectile.
            server.update_shots(server.DT)
            moved=server.aoi_view(server.snapshot(),a)
            self.assertIn(str(shot.id),moved['shots'])
            self.assertNotEqual(moved['shots'][str(shot.id)]['x'],visible['shots'][str(shot.id)]['x'])
        finally:
            server.players.clear();server.players.update(orig_players)
            server.shots[:]=orig_shots;server.events[:]=orig_events
            server.monsters.clear();server.monsters.update(orig_monsters)

if __name__=='__main__':unittest.main(verbosity=2)
