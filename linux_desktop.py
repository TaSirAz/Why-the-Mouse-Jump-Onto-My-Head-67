"""Linux/X11 integration. Window enumeration is read-only."""
import os
import sys


def configure_qt_platform(platform=None, environ=None):
    platform = sys.platform if platform is None else platform
    environ = os.environ if environ is None else environ
    if platform.startswith("linux") and environ.get("DISPLAY"):
        # Both Xorg and XWayland permit moving small desktop windows.
        environ.setdefault("QT_QPA_PLATFORM", "xcb")
    return environ.get("QT_QPA_PLATFORM", "")


def display_error(platform=None, environ=None):
    platform = sys.platform if platform is None else platform
    environ = os.environ if environ is None else environ
    if not platform.startswith("linux"):
        return ""
    backend = environ.get("QT_QPA_PLATFORM", "")
    if backend in {"offscreen", "minimal"}:
        return ""  # Explicit test-only backends.
    if backend.startswith("wayland"):
        return "Naiwa needs X11/XWayland window positioning. Use QT_QPA_PLATFORM=xcb with XWayland, or sign in to an Xorg session."
    if not environ.get("DISPLAY"):
        return "No X11 display found. Run Naiwa in an Ubuntu/Mint graphical X11 or XWayland session (not a bare terminal/SSH session)."
    return ""


class X11Windows:
    def __init__(self):
        self.connection = None
        self.failed = False

    def rectangles(self, exclude_ids=(), scale=1):
        if self.failed or not os.environ.get("DISPLAY"):
            return []
        try:
            from Xlib import X, display, error
            if self.connection is None:
                self.connection = display.Display()
            connection = self.connection
            root = connection.screen().root
            atom = connection.intern_atom
            stacking = root.get_full_property(atom("_NET_CLIENT_LIST_STACKING"), X.AnyPropertyType)
            if stacking is not None:
                windows = [connection.create_resource_object("window", int(i)) for i in reversed(stacking.value)]
            else:
                windows = list(reversed(root.query_tree().children))
            pid_atom = atom("_NET_WM_PID")
            type_atom = atom("_NET_WM_WINDOW_TYPE")
            state_atom = atom("_NET_WM_STATE")
            frame_atom = atom("_NET_FRAME_EXTENTS")
            current = root.get_full_property(atom("_NET_CURRENT_DESKTOP"), X.AnyPropertyType)
            current_desktop = int(current.value[0]) if current is not None else None
            excluded_types = {atom("_NET_WM_WINDOW_TYPE_DESKTOP"), atom("_NET_WM_WINDOW_TYPE_DOCK")}
            hidden_state = atom("_NET_WM_STATE_HIDDEN")
            excluded = set(int(i) for i in exclude_ids)
            rectangles = []
            for window in windows:
                try:
                    if window.id in excluded or window.get_attributes().map_state != X.IsViewable:
                        continue
                    pid = window.get_full_property(pid_atom, X.AnyPropertyType)
                    if pid is not None and int(pid.value[0]) == os.getpid():
                        continue
                    types = window.get_full_property(type_atom, X.AnyPropertyType)
                    if types is not None and excluded_types.intersection(types.value):
                        continue
                    state = window.get_full_property(state_atom, X.AnyPropertyType)
                    if state is not None and hidden_state in state.value:
                        continue
                    desktop = window.get_full_property(atom("_NET_WM_DESKTOP"), X.AnyPropertyType)
                    if desktop is not None and current_desktop is not None and int(desktop.value[0]) not in {current_desktop, 0xffffffff}:
                        continue
                    geometry = window.get_geometry()
                    origin = root.translate_coords(window, 0, 0)
                    left, top = origin.x, origin.y
                    right, bottom = left + geometry.width, top + geometry.height
                    frame = window.get_full_property(frame_atom, X.AnyPropertyType)
                    if frame is not None and len(frame.value) == 4:
                        left -= int(frame.value[0])
                        right += int(frame.value[1])
                        top -= int(frame.value[2])
                        bottom += int(frame.value[3])
                    rect = tuple(round(v / scale) for v in (left, top, right, bottom))
                    left, top, right, bottom = rect
                    if right - left <= 100 or bottom - top <= 80:
                        continue
                    if not any(l <= (left + right) / 2 <= r and t <= top < b for l, t, r, b in rectangles):
                        rectangles.append(rect)
                except error.XError:
                    continue  # The user may close a window during enumeration.
            return rectangles
        except (ImportError, OSError):
            self.failed = True
            return []
        except Exception:
            # Losing an X connection must not crash the physics timer.
            if self.connection is not None:
                try:
                    self.connection.close()
                except Exception:
                    pass
            self.connection = None
            self.failed = True
            return []


X11 = X11Windows()
