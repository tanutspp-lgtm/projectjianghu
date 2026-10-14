import unittest,re,json
from pathlib import Path
import server

class TestMapAndRopePvE(unittest.TestCase):
    def test_static_map_rope_geometry_matches_browser(self):
        frontend=(Path(__file__).parent.parent/'jianghu_v80cb_front'/'index.html')
        if not frontend.exists():
            # Standalone GitHub/server ZIP must be testable without the 112MB client.
            self.assertEqual(server.CLIMBS,((510,235,550),(1170,390,550),(1590,235,550)))
            return
        html=frontend.read_text()
        cm=re.search(r'const climbs=\[(.*?)\];',html)
        self.assertIsNotNone(cm)
        client=[{'x':int(x),'top':int(y),'bottom':int(z)} for x,y,z in re.findall(r'x:(\d+),top:(\d+),bottom:(\d+)',cm.group(1))]
        server_=[{'x':c[0],'top':c[1],'bottom':c[2]} for c in server.CLIMBS]
        self.assertEqual(client,server_)
    def test_ladder_top_exit_not_in_the_sky(self):
        # The actual ladder X1170 ends at mid-floor Y390; no invisible extra segment to Y235.
        ladder=next(c for c in server.CLIMBS if c[0]==1170)
        self.assertEqual(ladder[1],390)
        p=server.Guest('climber',1170,398,1200,1200)
        server.prog.apply_derived_resources(p,server.hp_reference,full=True)
        p.climb=ladder;p.ground=False;p.buttons=4
        now=server.time.monotonic();p.last_input=now
        for i in range(30):
            server.update_guest(p,server.DT,now+i*server.DT)
            self.assertGreaterEqual(p.y,390)
            if p.climb is None:break
        self.assertIsNone(p.climb)
        self.assertTrue(p.ground)
        self.assertEqual(p.y,390)
        self.assertEqual(p.x,1217)
    def test_pve_projectiles_do_not_damage_other_players(self):
        a=server.Guest('a',175,550,1200,1200);b=server.Guest('b',215,550,1200,1200)
        for p in (a,b):server.prog.apply_derived_resources(p,server.hp_reference,full=True)
        orig_players=server.players.copy();orig_mons=server.monsters.copy();orig_shots=list(server.shots);orig_events=list(server.events)
        try:
            server.players.clear();server.players.update({'a':a,'b':b});server.monsters.clear();server.shots.clear();server.events.clear()
            a.face=1;a.sp=a.max_sp
            server.perform_action(a,'attack')
            self.assertTrue(server.shots)
            for i in range(15):server.update_shots(server.DT)
            self.assertEqual(b.hp,b.max_hp)
            self.assertEqual(b.down,0)
            self.assertEqual(b.stun,0)
        finally:
            server.players.clear();server.players.update(orig_players);server.monsters.clear();server.monsters.update(orig_mons)
            server.shots[:]=orig_shots;server.events[:]=orig_events
if __name__=='__main__':unittest.main(verbosity=2)
