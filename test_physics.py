"""Collision regressions without a display server or Qt dependency."""
import unittest
from physics import Body, collide, constrain, step, substep_count


class CollisionTests(unittest.TestCase):
    def test_fast_small_discs_do_not_pass_through_each_other(self):
        a = Body(300, 200, 16, vx=12000)
        b = Body(400, 200, 16, vx=-12000)
        count = substep_count([a, b], 1 / 120, gravity=0)
        impacts = []
        for _ in range(count):
            for body in (a, b):
                step(body, (0, 0, 1000, 600), 1 / 120 / count, gravity=0)
            impacts.append(collide(a, b))
        self.assertTrue(any(speed > 0 for speed in impacts))
        self.assertLess(a.x, b.x)
        self.assertLess(a.vx, 0)
        self.assertGreater(b.vx, 0)

    def test_held_body_retains_velocity_spin_and_position(self):
        a = Body(200, 200, 30, vx=900, vy=80, spin=25, held=True)
        b = Body(250, 200, 30, vx=-600)
        self.assertGreater(collide(a, b), 0)
        self.assertEqual((a.x, a.y, a.vx, a.vy, a.spin), (200, 200, 900, 80, 25))
        self.assertGreater(b.vx, 0)

    def test_window_landing_uses_earliest_top_regardless_of_scan_order(self):
        b = Body(200, 100, 20, vy=3000)
        step(b, (0, 0, 900, 600), .1, gravity=0.1,
             platforms=[(0, 300, 400, 500), (0, 200, 400, 250)])
        self.assertEqual(b.y, 180)
        self.assertLess(b.vy, 0)

    def test_window_top_is_one_way_and_resting_contact_is_stable(self):
        platforms = [(100, 200, 400, 500)]
        rising = Body(200, 220, 20, vy=-900)
        step(rising, (0, 0, 900, 600), .08, platforms=platforms)
        self.assertLess(rising.y, 180)
        resting = Body(200, 180, 20)
        for _ in range(100):
            step(resting, (0, 0, 900, 600), 1 / 120, platforms=platforms)
        self.assertEqual(resting.y, 180)
        self.assertEqual(resting.vy, 0)
        self.assertTrue(resting.grounded)
        resting.x = 401
        step(resting, (0, 0, 900, 600), 1 / 120, platforms=platforms)
        self.assertGreater(resting.y, 180)
        self.assertFalse(resting.grounded)

    def test_collision_correction_cannot_leave_screen(self):
        a = Body(30, 200, 30)
        b = Body(70, 200, 30)
        collide(a, b)
        constrain(a, (0, 0, 900, 600))
        self.assertEqual(a.x, 30)
        tiny = Body(20, 20, 90, vx=100)
        constrain(tiny, (0, 0, 100, 100))
        self.assertEqual((tiny.x, tiny.y, tiny.vx), (50, 50, 0))

    def test_unequal_mass_impulse_conserves_momentum(self):
        a, b = Body(0, 0, 60, vx=300), Body(85, 0, 30, vx=-100)
        momentum = a.r ** 2 * a.vx + b.r ** 2 * b.vx
        self.assertGreater(collide(a, b), 0)
        self.assertAlmostEqual(a.r ** 2 * a.vx + b.r ** 2 * b.vx, momentum)

    def test_antigravity_settles_at_ceiling(self):
        b = Body(200, 100, 20)
        for _ in range(600):
            step(b, (0, 0, 900, 600), 1 / 120, gravity=-450)
        self.assertEqual(b.y, 20)
        self.assertEqual(b.vy, 0)
        self.assertTrue(b.grounded)


if __name__ == "__main__":
    unittest.main()
