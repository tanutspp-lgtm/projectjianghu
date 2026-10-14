import unittest
import server

class TestLadderRttV80CE(unittest.TestCase):
    def build(self,x,y):
        p=server.Guest('t',x,y,1200,1200)
        server.prog.apply_derived_resources(p,server.hp_reference,full=True)
        return p
    def test_hold_up_from_bottom_for_10_seconds_never_climbs_sky(self):
        # Full actual server movement loop: pressing UP after ladder exit must
        # never create a new climb state above the middle landing.
        p=self.build(1170,550)
        p.buttons=4
        now=server.time.monotonic()
        seen_exit=False
        for i in range(300):
            p.last_input=now+i*server.DT
            server.update_guest(p,server.DT,now+i*server.DT)
            self.assertGreaterEqual(p.y,390, f'tick {i}: middle ladder sky climb')
            if i>60:
                seen_exit=True
                self.assertIsNone(p.climb,'holding UP must stay exited')
                self.assertEqual(p.y,390)
                self.assertTrue(p.ground)
        self.assertTrue(seen_exit)
        self.assertAlmostEqual(p.x,1217)
    def test_up_from_upper_end_does_not_regrab(self):
        p=self.build(1170,390)
        p.buttons=4;p.ground=True
        p.last_input=server.time.monotonic()
        server.update_guest(p,server.DT,p.last_input)
        self.assertIsNone(p.climb)
        self.assertEqual(p.y,390)
    def test_other_ropes_still_reach_correct_top(self):
        for cx,top,_ in server.CLIMBS:
            p=self.build(cx,550);p.buttons=4
            now=server.time.monotonic()
            for i in range(95):
                p.last_input=now+i*server.DT
                server.update_guest(p,server.DT,now+i*server.DT)
                self.assertGreaterEqual(p.y,top)
            self.assertEqual(p.y,top)
            self.assertIsNone(p.climb)
    def test_feature_marker(self):
        self.assertEqual(server.CLIMBS,((510,235,550),(1170,390,550),(1590,235,550)))
        self.assertTrue(server.PORT>0)

if __name__=='__main__':unittest.main()
