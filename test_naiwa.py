import json
import math
import os
from pathlib import Path
import tempfile
import time
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from physics import Body, collide, step
from naiwa import Club


class PhysicsTests(unittest.TestCase):
    def test_fast_throw_stays_in_bounds_and_rolls(self):
        b = Body(400, 200, 64, vx=1900, vy=-1700, spin=900)
        hits = []
        for _ in range(1200):
            hits.extend(step(b, (0, 0, 900, 600), 1 / 120))
            self.assertTrue(64 <= b.x <= 836 and 64 <= b.y <= 536)
            self.assertTrue(math.isfinite(b.angle))
        self.assertGreater(len(hits), 2)
        self.assertTrue(b.grounded)

    def test_unequal_size_collision_conserves_momentum(self):
        a, b = Body(0, 0, 60, vx=300), Body(85, 0, 30, vx=-100)
        before = a.r ** 2 * a.vx + b.r ** 2 * b.vx
        self.assertGreater(collide(a, b), 0)
        self.assertAlmostEqual(a.r ** 2 * a.vx + b.r ** 2 * b.vx, before)
        self.assertGreaterEqual(b.x - a.x, a.r + b.r - .001)

    def test_held_pet_is_fixed_and_coincident_centers_are_safe(self):
        a, b = Body(100, 100, held=True), Body(100, 100, vx=-300)
        collide(a, b)
        self.assertEqual((a.x, a.y), (100, 100))
        self.assertGreaterEqual(abs(b.x - a.x), 128)

    def test_negative_monitor_and_tiny_work_area(self):
        b = Body(-150, 50, 90, vx=900, vy=-500)
        for _ in range(200):
            step(b, (-800, -100, 0, 500), 1 / 120, gravity=-450)
        self.assertTrue(-710 <= b.x <= -90 and -10 <= b.y <= 410)
        step(b, (0, 0, 100, 100), 1 / 120)
        self.assertEqual((b.x, b.y), (50, 50))


class InteractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.club = Club(self.app, self.temp.name)
        self.club.timer.stop()
        self.club.window_timer.stop()
        self.club.save_timer.stop()
        self.pet = self.club.toys[0]

    def tearDown(self):
        for toy in self.club.toys[:]:
            toy.hide()
            toy.deleteLater()
        self.club.panel.timer.stop()
        self.club.panel.hide()
        self.club.panel.deleteLater()
        self.club.tray.hide()
        self.app.aboutToQuit.disconnect(self.club.save)
        self.temp.cleanup()

    def test_click_double_click_and_render(self):
        QTest.mouseClick(self.pet, Qt.MouseButton.LeftButton, pos=QPoint(int(self.pet.cx), int(self.pet.cy)))
        self.assertEqual(self.club.stats["pets"], 1)
        self.assertLess(self.pet.body.vy, 0)
        QTest.mouseDClick(self.pet, Qt.MouseButton.LeftButton, pos=QPoint(int(self.pet.cx), int(self.pet.cy)))
        self.assertEqual(abs(self.pet.body.spin), 1050)
        self.pet.render_frame(1 / 60)
        self.assertFalse(self.pet.buffer.isNull())
        self.assertEqual(self.pet.buffer.pixelColor(0, 0).alpha(), 0)
        self.assertGreater(len(self.pet.particles), 0)

    def test_snack_consumption_and_limits(self):
        self.club.feed()
        food = next(t for t in self.club.toys if t.kind == "food")
        food.body.x, food.body.y = self.pet.body.x, self.pet.body.y
        before = self.pet.hunger
        self.club.simulate(1 / 120, time.monotonic())
        self.assertNotIn(food, self.club.toys)
        self.assertGreater(self.pet.hunger, before)
        self.assertEqual(self.club.stats["snacks"], 1)
        for _ in range(10):
            self.club.add_pet()
        self.assertEqual(sum(t.kind == "pet" for t in self.club.toys), 6)

    def test_drag_throw_and_stopped_release(self):
        center = QPoint(int(self.pet.cx), int(self.pet.cy))
        QTest.mousePress(self.pet, Qt.MouseButton.LeftButton, pos=center)
        QTest.qWait(20)
        QTest.mouseMove(self.pet, center + QPoint(35, -10))
        QTest.qWait(20)
        QTest.mouseMove(self.pet, center + QPoint(95, -40))
        QTest.mouseRelease(self.pet, Qt.MouseButton.LeftButton, pos=center + QPoint(95, -40))
        self.assertFalse(self.pet.body.held)
        self.assertGreater(self.pet.body.vx, 200)
        self.assertLess(self.pet.body.vy, -100)
        self.assertEqual(self.club.stats["throws"], 1)
        QTest.mousePress(self.pet, Qt.MouseButton.LeftButton, pos=center)
        QTest.mouseMove(self.pet, center + QPoint(60, 0))
        QTest.qWait(170)
        QTest.mouseRelease(self.pet, Qt.MouseButton.LeftButton, pos=center + QPoint(60, 0))
        self.assertEqual(self.pet.body.vx, 0)

    def test_window_landing_and_upward_pass(self):
        self.club.window_rects = [(0, 260, 700, 500)]
        b = self.pet.body
        b.x, b.y, b.vy = 350, 195, 600
        self.club.simulate(1 / 120, time.monotonic())
        self.assertEqual(b.y, 260 - b.r)
        self.assertLess(b.vy, 0)
        b.y, b.vy = 210, -600
        self.club.simulate(1 / 120, time.monotonic())
        self.assertLess(b.y, 210)
        self.assertLess(b.vy, 0)

    def test_focus_completion_pause_and_settings(self):
        self.club.start_focus(5)
        self.club.focus_until = time.monotonic() - 1
        self.club.tick()
        self.assertEqual(self.club.stats["focus_sessions"], 1)
        self.assertEqual(self.club.mode, "wander")
        self.club.toggle_pause()
        before = (self.pet.body.x, self.pet.body.y)
        self.club.last -= .08
        self.club.tick()
        self.assertEqual((self.pet.body.x, self.pet.body.y), before)
        self.club.set_size(82)
        self.club.save()
        data = json.loads((Path(self.temp.name) / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual(data["settings"]["size"], 82)
        self.club.settings["size"] = 64
        self.club.load()
        self.assertEqual(self.club.settings["size"], 82)


if __name__ == "__main__":
    unittest.main()
