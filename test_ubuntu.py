"""Regressions for Ubuntu startup, desktop recovery and GNOME reminders."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage, QColor
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from pet_images import custom_pet_path
from naiwa import Club, migrate_legacy_settings
from linux_desktop import X11Windows
from linux_setup import desktop_entry

ROOT = Path(__file__).resolve().parent


class UbuntuTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.club = Club(self.app, self.temp.name)
        for timer in (self.club.timer, self.club.window_timer, self.club.save_timer, self.club.panel.timer):
            timer.stop()

    def tearDown(self):
        self.club.finish_import()
        self.app.aboutToQuit.disconnect(self.club.save)
        self.app.aboutToQuit.disconnect(self.club.finish_import)
        for toy in self.club.toys:
            toy.hide()
            toy.deleteLater()
        self.club.panel.hide()
        self.club.panel.deleteLater()
        self.club.tray.hide()
        self.temp.cleanup()

    def test_focus_without_tray_opens_panel_and_persists_completion(self):
        self.club.start_focus(5)
        self.club.focus_until = time.monotonic() - 1
        self.club.paused = True
        with patch('naiwa.QSystemTrayIcon.isSystemTrayAvailable', return_value=False):
            self.club.tick()
        self.assertTrue(self.club.panel.isVisible())
        self.assertIn('專注完成', self.club.panel.notice.text())
        data = json.loads((Path(self.temp.name) / 'settings.json').read_text())
        self.assertEqual(data['stats']['focus_sessions'], 1)
        self.club.start_focus(5)
        self.assertEqual(self.club.notice, '')

    def test_disable_window_collisions_clears_stale_platforms(self):
        self.club.window_rects = [(0, 100, 900, 600)]
        self.club.set_option('windows', False)
        self.assertEqual(self.club.window_rects, [])
        self.assertFalse(json.loads((Path(self.temp.name) / 'settings.json').read_text())['settings']['windows'])

    def test_invalid_saved_size_does_not_break_rendering(self):
        for value in [float('nan'), float('inf'), True]:
            (Path(self.temp.name) / 'settings.json').write_text(json.dumps({'settings': {'size': value}}))
            self.club.load()
            self.assertEqual(self.club.settings['size'], 64)
        self.club.set_size(1000)
        self.assertEqual(self.club.toys[0].body.r, 100)

    def test_tray_menu_survives_pet_context_menu(self):
        original = self.club.tray_menu
        self.club.context_menu(self.club.toys[0])
        self.assertIs(self.club.tray.contextMenu(), original)
        self.assertGreater(len(original.actions()), 0)

    def test_async_image_import_updates_all_pets_and_reset(self):
        source = Path(self.temp.name) / 'wide-pet.png'
        image = QImage(200, 60, QImage.Format.Format_ARGB32)
        image.fill(QColor('white'))
        for x in range(40, 160):
            for y in range(10, 50):
                image.setPixelColor(x, y, QColor('red'))
        image.save(str(source))
        self.club.add_pet()
        self.club.import_image(str(source))
        self.assertFalse(self.club.panel.import_button.isEnabled())
        deadline = time.monotonic() + 5
        while self.club.import_thread is not None and time.monotonic() < deadline:
            QTest.qWait(20)
        self.assertIsNone(self.club.import_thread)
        self.assertTrue(self.club.panel.import_button.isEnabled())
        self.assertTrue(custom_pet_path(self.temp.name).is_file())
        self.assertAlmostEqual(self.club.sprite.width() / self.club.sprite.height(), 3, delta=.1)
        for toy in self.club.toys:
            toy.bubble_until = 0
            toy.render_frame(0)
            self.assertFalse(toy.buffer.isNull())
        self.club.reset_image()
        self.assertFalse(custom_pet_path(self.temp.name).exists())
        self.assertEqual(self.club.sprite.cacheKey(), self.club.default_sprite.cacheKey())

    def test_rename_migration_preserves_old_and_existing_settings(self):
        legacy = Path(self.temp.name) / 'legacy'
        legacy.mkdir()
        old = legacy / 'settings.json'
        old.write_text('{"settings":{"size":82},"stats":{"pets":9}}')
        target = Path(self.temp.name) / 'renamed'
        target.mkdir()
        migrate_legacy_settings(target, legacy)
        self.assertEqual(json.loads((target / 'settings.json').read_text())['stats']['pets'], 9)
        self.assertTrue(old.exists())
        (target / 'settings.json').write_text('{"stats":{"pets":17}}')
        migrate_legacy_settings(target, legacy)
        self.assertEqual(json.loads((target / 'settings.json').read_text())['stats']['pets'], 17)

    def test_supported_pet_cannot_be_pushed_through_window_top(self):
        self.club.add_pet()
        lower, upper = self.club.toys
        self.club.bounds = lambda body: (0, 0, 1000, 600)
        self.club.window_rects = [(100, 300, 900, 500)]
        self.club.mode = 'sleep'
        lower.body.x, lower.body.y = 350, 300 - lower.body.r
        upper.body.x, upper.body.y = 350, 150
        for toy in (lower, upper):
            toy.body.vx = toy.body.vy = 0
        for _ in range(120):
            self.club.simulate(1 / 120, time.monotonic())
            self.assertLessEqual(lower.body.y + lower.body.r, 300.001)
        self.assertGreaterEqual(lower.body.y - upper.body.y, 125)

    def test_integrated_fast_ball_contacts_do_not_tunnel(self):
        self.club.toys[0].body.x = 50
        self.club.toys[0].body.y = 50
        self.club.toys[0].body.held = True
        self.club.add_ball()
        self.club.add_ball()
        a, b = self.club.toys[-2:]
        self.club.bounds = lambda body: (0, 0, 1000, 600)
        a.body.x, b.body.x = 300, 400
        a.body.y = b.body.y = 200
        a.body.vx, b.body.vx = 12000, -12000
        self.club.simulate(1 / 120, time.monotonic())
        self.assertLess(a.body.x, b.body.x)
        self.assertLess(a.body.vx, 0)
        self.assertGreater(b.body.vx, 0)


class StartupTests(unittest.TestCase):
    def test_x11_retries_after_transient_failure_with_backoff(self):
        backend = X11Windows()
        with patch.dict(os.environ, {'DISPLAY': ':test'}), patch('linux_desktop.time.monotonic', return_value=10), patch('Xlib.display.Display', side_effect=OSError('disconnected')) as connect:
            self.assertEqual(backend.rectangles(), [])
            self.assertTrue(backend.failed)
            backend.rectangles()
            self.assertEqual(connect.call_count, 1)
        with patch.dict(os.environ, {'DISPLAY': ':test'}), patch('linux_desktop.time.monotonic', return_value=16), patch('Xlib.display.Display', side_effect=OSError('still disconnected')) as connect:
            backend.rectangles()
            self.assertEqual(connect.call_count, 1)

    def test_packaged_launcher_does_not_use_pip_and_handles_spaces(self):
        with tempfile.TemporaryDirectory(prefix='naiwa space ') as directory:
            root = Path(directory)
            (root / 'start.sh').write_text((ROOT / 'start.sh').read_text())
            exe = root / 'Naiwa'
            exe.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\n')
            exe.chmod(0o755)
            result = subprocess.run(['bash', str(root / 'start.sh')], env={**os.environ, 'DISPLAY': ':test', 'QT_QPA_PLATFORM': 'xcb'}, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), '--panel')
            missing = subprocess.run(['bash', str(root / 'start.sh')], env={**os.environ, 'DISPLAY': ''}, text=True, capture_output=True)
            self.assertNotEqual(missing.returncode, 0)
            self.assertIn('XWayland', missing.stderr)

    def test_desktop_entry_escapes_paths(self):
        text = desktop_entry(Path('/tmp/pet space/$literal%name'))
        self.assertIn('%%name', text)
        self.assertIn('\\\\$literal', text)
        self.assertIn('Terminal=false', text)

    def test_second_launch_activates_existing_panel(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / 'opened'
            env = {**os.environ, 'XDG_DATA_HOME': directory, 'QT_QPA_PLATFORM': 'offscreen'}
            script = ('import naiwa; from pathlib import Path; '
                      'original=naiwa.Club.show_panel; '
                      f'naiwa.Club.show_panel=lambda club: (Path({str(marker)!r}).write_text("open"), original(club)); '
                      'raise SystemExit(naiwa.main())')
            process = subprocess.Popen([os.sys.executable, '-c', script, '--panel'], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            try:
                deadline = time.monotonic() + 8
                while not marker.exists() and time.monotonic() < deadline and process.poll() is None:
                    time.sleep(.05)
                self.assertTrue(marker.exists(), 'First instance did not start')
                marker.unlink()
                result = subprocess.run([os.sys.executable, 'naiwa.py', '--panel'], cwd=ROOT, env=env, capture_output=True, text=True, timeout=8)
                self.assertEqual(result.returncode, 0, result.stderr)
                deadline = time.monotonic() + 3
                while not marker.exists() and time.monotonic() < deadline:
                    time.sleep(.05)
                self.assertTrue(marker.exists(), 'Second launch did not activate the first instance')
            finally:
                process.terminate()
                process.wait(timeout=5)


if __name__ == '__main__':
    unittest.main()
