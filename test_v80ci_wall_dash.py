"""v8.0CI: world wall must be resolved before ground support at full dash speed."""
import unittest
import time
import server

class WallDashRegression(unittest.TestCase):
    def actor(self, x, y=550):
        p=server.Guest('wall-dash-test', x,y,1200,1200)
        server.prog.apply_derived_resources(p,server.hp_reference,full=True)
        return p

    def test_dash_left_and_right_along_ground_never_tunnels(self):
        for face,start in [(-1,27),(1,server.WORLD_W-27)]:
            with self.subTest(face=face):
                p=self.actor(start)
                p.face=face
                p.sta=100
                server.perform_action(p,'dash')
                expected_hp=p.hp
                self.assertEqual(p.action,'dash')
                now=time.monotonic()
                for i in range(65):
                    # Full authoritative player update with held input and normal animation.
                    p.last_input=now+i*server.DT
                    p.buttons=1 if face<0 else 2
                    server.update_guest(p,server.DT,now+i*server.DT)
                    self.assertEqual(p.y,550,(face,i,p.x,p.y))
                    self.assertTrue(p.ground,(face,i,p.x,p.y))
                    self.assertGreaterEqual(p.x,27)
                    self.assertLessEqual(p.x,server.WORLD_W-27)
                self.assertGreaterEqual(p.hp,expected_hp)

    def test_outward_fast_knockback_never_drops_ground(self):
        for face,start in [(-1,27),(1,server.WORLD_W-27)]:
            with self.subTest(face=face):
                p=self.actor(start)
                p.kb_time=.35
                p.kb_dir=face
                now=time.monotonic()
                for i in range(25):
                    p.last_input=now+i*server.DT
                    server.update_guest(p,server.DT,now+i*server.DT)
                    self.assertEqual(p.y,550,(face,i,p.x,p.y))
                    self.assertTrue(p.ground)

    def test_jump_then_dash_wall_falls_normally_onto_ground(self):
        for face,start in [(-1,27),(1,server.WORLD_W-27)]:
            with self.subTest(face=face):
                p=self.actor(start)
                p.face=face
                server.perform_action(p,'jump')
                self.assertFalse(p.ground)
                server.perform_action(p,'dash')
                now=time.monotonic()
                saw_air=False
                for i in range(110):
                    p.last_input=now+i*server.DT
                    p.buttons=1 if face<0 else 2
                    server.update_guest(p,server.DT,now+i*server.DT)
                    saw_air |= p.y<550
                    self.assertGreaterEqual(p.x,27)
                    self.assertLessEqual(p.x,server.WORLD_W-27)
                    self.assertLessEqual(p.y,550,(face,i,p.x,p.y))
                self.assertTrue(saw_air)
                self.assertEqual(p.y,550)
                self.assertTrue(p.ground)

if __name__=='__main__':unittest.main()
