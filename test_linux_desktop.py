import os
import sys
import unittest
from linux_desktop import X11Windows, configure_qt_platform, display_error, visible_top_segments, map_top_segments


class PlatformPolicyTests(unittest.TestCase):
    def test_wayland_session_with_xwayland_selects_xcb(self):
        env = {"DISPLAY": ":1", "WAYLAND_DISPLAY": "wayland-0"}
        self.assertEqual(configure_qt_platform("linux", env), "xcb")
        self.assertEqual(display_error("linux", env), "")

    def test_explicit_backends_and_windows_are_preserved(self):
        env = {"DISPLAY": ":1", "QT_QPA_PLATFORM": "offscreen"}
        configure_qt_platform("linux", env)
        self.assertEqual(env["QT_QPA_PLATFORM"], "offscreen")
        env = {"DISPLAY": ":1"}
        configure_qt_platform("win32", env)
        self.assertNotIn("QT_QPA_PLATFORM", env)

    def test_pure_wayland_or_no_display_gets_actionable_error(self):
        self.assertIn("X11", display_error("linux", {}))
        self.assertIn("xcb", display_error("linux", {"QT_QPA_PLATFORM": "wayland", "DISPLAY": ":1"}))
        self.assertEqual(display_error("linux", {"QT_QPA_PLATFORM": "offscreen"}), "")


class WindowEdgeTests(unittest.TestCase):
    def test_partial_occlusion_keeps_both_exposed_edges(self):
        rect = (0, 100, 800, 600)
        self.assertEqual(visible_top_segments(rect, [(250, 50, 550, 300)]),
                         [(0, 100, 250, 600), (550, 100, 800, 600)])
        self.assertEqual(visible_top_segments(rect, [(0, 50, 900, 300)]), [])
        self.assertEqual(visible_top_segments(rect, [(0, 200, 900, 300)]), [rect])

    def test_mixed_scale_spanning_window_uses_monitor_origins(self):
        mappings = [((0, 0, 1920, 1080), (0, 0, 1920, 1080)),
                    ((1920, 0, 2560, 1440), (1920, 0, 1280, 720))]
        self.assertEqual(map_top_segments([(1800, 200, 2320, 600)], mappings),
                         [(1800, 200, 1920, 600), (1920, 100, 2120, 300)])
        self.assertEqual(map_top_segments([(300, 200, 900, 600)], (), 2),
                         [(150, 100, 450, 300)])

    def test_invalid_display_scale_is_rejected(self):
        for scale in (0, -1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                X11Windows().rectangles(scale=scale)

    def test_screenshot_verification_rejects_headless_backend(self):
        self.assertIn('visible', display_error('linux', {'QT_QPA_PLATFORM': 'offscreen'}, require_visible=True))


@unittest.skipUnless(sys.platform.startswith("linux") and os.environ.get("DISPLAY"), "requires Linux X11")
class X11WindowTests(unittest.TestCase):
    def test_real_window_position_frame_hidden_and_dock(self):
        from Xlib import X, Xatom, display
        connection = display.Display()
        root = connection.screen().root
        window = root.create_window(160, 250, 500, 180, 0, X.CopyFromParent)
        # This synthetic window represents an external client for PID filtering.
        window.change_property(connection.intern_atom("_NET_WM_PID"), Xatom.CARDINAL, 32, [os.getpid() + 1])
        window.change_property(connection.intern_atom("_NET_FRAME_EXTENTS"), Xatom.CARDINAL, 32, [3, 3, 24, 3])
        window.map()
        connection.sync()
        backend = X11Windows()
        try:
            self.assertIn((157, 226, 663, 433), backend.rectangles())
            self.assertNotIn((157, 226, 663, 433), backend.rectangles([window.id]))
            self.assertIn((78, 113, 332, 216), backend.rectangles(scale=2))
            window.change_property(connection.intern_atom("_NET_WM_WINDOW_TYPE"), Xatom.ATOM, 32,
                                   [connection.intern_atom("_NET_WM_WINDOW_TYPE_DOCK")])
            connection.sync()
            self.assertNotIn((157, 226, 663, 433), backend.rectangles())
            window.unmap()
            connection.sync()
            self.assertNotIn((157, 226, 663, 433), backend.rectangles())
        finally:
            window.destroy()
            connection.sync()
            connection.close()
            if backend.connection:
                backend.connection.close()


if __name__ == "__main__":
    unittest.main()

