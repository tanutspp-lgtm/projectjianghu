"""v8.0CA: Multiplayer Guest is PvE-only, including AUTO and guard-break AOE.
No client-supplied PK state is trusted; positive PvP cannot be enabled via a packet.
"""
import unittest
import server

class CooperativePVE(unittest.TestCase):
    def setUp(self):
        server.players.clear();server.monsters.clear();server.shots.clear();server.events.clear();server.loot_drops.clear()
        self.shooter=server.Guest('owner',140,550,1200,1200)
        self.friend=server.Guest('friend',185,550,1200,1200)
        server.players[self.shooter.id]=self.shooter
        server.players[self.friend.id]=self.friend
    def tearDown(self):
        server.players.clear();server.monsters.clear();server.shots.clear();server.events.clear();server.loot_drops.clear()
    def shot(self,kind='attack',x=185):
        return server.Shot(42,'owner',kind,x,466,0,80,1.0,99 if kind=='aoe' else 1)
    def test_direct_hit_rejects_player_even_when_guarding(self):
        self.friend.guard=True
        for kind in ('attack','aoe','break'):
            sh=self.shot(kind)
            self.assertFalse(server.apply_shot(sh,self.friend,False))
            self.assertEqual(self.friend.hp,1200)
            self.assertTrue(self.friend.guard)
            self.assertEqual(self.friend.broken,0)
            self.assertEqual(self.friend.stun,0)
            self.assertEqual(self.friend.down,0)
            self.assertEqual(sh.pierce,99 if kind=='aoe' else 1)
            self.assertNotIn('friend',sh.hit)
    def test_world_shots_ignore_friends_and_still_hit_monsters(self):
        self.friend.guard=True
        monster=server.Monster('wolf-test',189,550,400,400)
        self.assertGreater(monster.hp,0)
        server.monsters[monster.id]=monster
        sh=self.shot(x=185);server.shots.append(sh)
        server.update_shots(1/30)
        self.assertEqual(self.friend.hp,1200)
        self.assertEqual(self.friend.broken,0)
        self.assertLess(monster.hp,400)
        self.assertNotIn('friend',sh.hit)
    def test_aoe_cannot_knockdown_guests_even_in_same_location(self):
        for i in range(28):
            p=server.Guest(f'friend{i}',185,550,1200,1200)
            server.players[p.id]=p
        server.shots.append(self.shot('aoe'))
        server.update_shots(1/30)
        for p in server.players.values():
            self.assertEqual(p.hp,1200)
            self.assertEqual(p.down,0)
            self.assertEqual(p.stun,0)
    def test_projectile_passes_through_players_when_no_mobs(self):
        sh=self.shot(x=185);server.shots.append(sh)
        server.update_shots(1/30)
        self.assertIn(sh,server.shots,'guest collision must not consume projectile')
    def test_both_farm_and_manual_shots_use_same_pve_only_hit(self):
        for auto in (False,True):
            self.shooter.auto_state.enabled=auto
            sh=self.shot('break')
            self.assertFalse(server.apply_shot(sh,self.friend,False))
            self.assertEqual(self.friend.hp,1200)

if __name__=='__main__':unittest.main(verbosity=2)
