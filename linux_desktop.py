"""Linux/X11 integration. Window enumeration is read-only."""
import json
import math
import os
import sys
import time
from project_info import APP_NAME


def configure_qt_platform(platform=None, environ=None):
    platform = sys.platform if platform is None else platform
    environ = os.environ if environ is None else environ
    if platform.startswith("linux") and environ.get("DISPLAY"):
        # Both Xorg and XWayland permit moving small desktop windows.
        environ.setdefault("QT_QPA_PLATFORM", "xcb")
    return environ.get("QT_QPA_PLATFORM", "")


def display_error(platform=None, environ=None, require_visible=False):
    platform = sys.platform if platform is None else platform
    environ = os.environ if environ is None else environ
    if not platform.startswith("linux"):
        return ""
    backend = environ.get("QT_QPA_PLATFORM", "")
    if backend in {"offscreen", "minimal"}:
        return "A visible X11/xcb desktop is required for screenshot verification." if require_visible else ""
    if backend.startswith("wayland"):
        return f"{APP_NAME} needs X11/XWayland window positioning. Use QT_QPA_PLATFORM=xcb with XWayland, or sign in to an Xorg session."
    if not environ.get("DISPLAY"):
        return f"No X11 display found. Run {APP_NAME} in an Ubuntu/Mint graphical X11 or XWayland session (not a bare terminal/SSH session)."
    return ""


def visible_top_segments(rect, occluders):
    """Preserve each exposed part of an edge, including partially covered windows."""
    left, top, right, bottom = rect
    spans = [(left, right)]
    for cover_left, cover_top, cover_right, cover_bottom in occluders:
        if not cover_top <= top < cover_bottom:
            continue
        remaining = []
        for start, end in spans:
            if cover_right <= start or cover_left >= end:
                remaining.append((start, end))
            else:
                if start < cover_left:
                    remaining.append((start, cover_left))
                if cover_right < end:
                    remaining.append((cover_right, end))
        spans = remaining
        if not spans:
            break
    return [(start, top, end, bottom) for start, end in spans if end > start]


def map_top_segments(rectangles, screen_mappings=(), scale=1):
    """Map native X11 edges into Qt logical screen space; split spanning edges."""
    result = []
    for left, top, right, bottom in rectangles:
        mapped = False
        for native, logical in screen_mappings:
            nx, ny, nw, nh = native
            lx, ly, lw, lh = logical
            if min(nw, nh, lw, lh) <= 0 or not ny <= top < ny + nh:
                continue
            start, end = max(left, nx), min(right, nx + nw)
            if end <= start:
                continue
            transformed = (round(lx + (start - nx) * lw / nw),
                           round(ly + (top - ny) * lh / nh),
                           round(lx + (end - nx) * lw / nw),
                           round(ly + (bottom - ny) * lh / nh))
            if transformed[2] > transformed[0] and transformed[3] > transformed[1]:
                result.append(transformed)
            mapped = True
        if not mapped:
            result.append(tuple(round(value / scale) for value in (left, top, right, bottom)))
    return result


class X11Windows:
    def __init__(self):
        self.connection = None
        self.failed = False
        self.retry_at = 0
        self.last_error = ""

    def rectangles(self, exclude_ids=(), scale=1, screens=()):
        return [top for window in self.snapshots(exclude_ids, scale, screens) for top in window["tops"]]

    def snapshots(self, exclude_ids=(), scale=1, screens=()):
        if not isinstance(scale, (int, float)) or not math.isfinite(scale) or scale <= 0:
            raise ValueError("Display scale must be finite and positive.")
        if time.monotonic() < self.retry_at or not os.environ.get("DISPLAY"):
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
            # Optional QScreen descriptors: (name, logical_x, logical_y, width, height).
            # Match names to actual RandR monitor geometry, not guessed scaled origins.
            screen_mappings = []
            if screens and hasattr(root, "xrandr_get_monitors"):
                try:
                    native_monitors = root.xrandr_get_monitors().monitors
                    logical_by_name = {item[0]: tuple(item[1:]) for item in screens}
                    for monitor in native_monitors:
                        logical = logical_by_name.get(connection.get_atom_name(monitor.name))
                        if logical is not None:
                            screen_mappings.append(((monitor.x, monitor.y, monitor.width_in_pixels, monitor.height_in_pixels), logical))
                except error.XError:
                    pass  # Older RandR servers retain the existing uniform-scale fallback.
            pid_atom = atom("_NET_WM_PID")
            type_atom = atom("_NET_WM_WINDOW_TYPE")
            state_atom = atom("_NET_WM_STATE")
            frame_atom = atom("_NET_FRAME_EXTENTS")
            current = root.get_full_property(atom("_NET_CURRENT_DESKTOP"), X.AnyPropertyType)
            current_desktop = int(current.value[0]) if current is not None and len(current.value) else None
            excluded_types = {atom("_NET_WM_WINDOW_TYPE_DESKTOP"), atom("_NET_WM_WINDOW_TYPE_DOCK")}
            hidden_state = atom("_NET_WM_STATE_HIDDEN")
            excluded = set(int(i) for i in exclude_ids)
            records = []
            occluders = []
            for window in windows:
                try:
                    if window.id in excluded or window.get_attributes().map_state != X.IsViewable:
                        continue
                    pid = window.get_full_property(pid_atom, X.AnyPropertyType)
                    if pid is not None and len(pid.value) and int(pid.value[0]) == os.getpid():
                        continue
                    types = window.get_full_property(type_atom, X.AnyPropertyType)
                    if types is not None and excluded_types.intersection(types.value):
                        continue
                    state = window.get_full_property(state_atom, X.AnyPropertyType)
                    if state is not None and hidden_state in state.value:
                        continue
                    desktop = window.get_full_property(atom("_NET_WM_DESKTOP"), X.AnyPropertyType)
                    if desktop is not None and len(desktop.value) and current_desktop is not None and int(desktop.value[0]) not in {current_desktop, 0xffffffff}:
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
                    rect = (left, top, right, bottom)
                    left, top, right, bottom = rect
                    if right - left > 100 * scale and bottom - top > 80 * scale:
                        tops = map_top_segments(visible_top_segments(rect, occluders), screen_mappings, scale)
                        regions = map_top_segments([rect], screen_mappings, scale)
                        if regions:
                            bounds = (min(r[0] for r in regions), min(r[1] for r in regions),
                                      max(r[2] for r in regions), max(r[3] for r in regions))
                            records.append({"id": f"x11:{window.id}", "rect": bounds,
                                            "regions": regions, "tops": tops, "source": "x11"})
                    occluders.append(rect)
                except error.XError:
                    continue  # The user may close a window during enumeration.
            self.failed = False
            self.last_error = ""
            return records
        except Exception as exc:
            # Losing an X connection must not crash the physics timer.
            if self.connection is not None:
                try:
                    self.connection.close()
                except Exception:
                    pass
            self.connection = None
            self.failed = True
            self.last_error = str(exc)
            self.retry_at = time.monotonic() + 5
            return []


X11 = X11Windows()

GNOME_BRIDGE_NAME = "org.desktoppets.WindowGeometry"
GNOME_BRIDGE_PATH = "/org/desktoppets/WindowGeometry"
GNOME_BRIDGE_UUID = "window-geometry@desktoppets.local"


def parse_gnome_snapshot(payload, excluded_pid=None, scale=1, screens=()):
    """Validate the read-only bridge reply before it enters the physics engine."""
    if not isinstance(scale, (int, float)) or not math.isfinite(scale) or scale <= 0:
        raise ValueError("Display scale must be finite and positive.")
    if not isinstance(payload, str) or len(payload) > 1_000_000:
        raise ValueError("Invalid GNOME geometry reply.")
    data = json.loads(payload)
    if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("windows"), list):
        raise ValueError("Unsupported GNOME geometry protocol.")
    screen_mappings = []
    logical_by_name = {item[0]: tuple(item[1:]) for item in screens}
    monitors = data.get("monitors", [])
    if isinstance(monitors, list):
        for monitor in monitors[:64]:
            if not isinstance(monitor, dict):
                continue
            native = monitor.get("rect")
            if not isinstance(native, list) or len(native) != 4 or any(
                    not isinstance(v, (int, float)) or not math.isfinite(v) for v in native) or min(native[2:]) <= 0:
                continue
            names = monitor.get("names", [])
            logical = next((logical_by_name[name] for name in names
                            if isinstance(name, str) and name in logical_by_name), None) if isinstance(names, list) else None
            if logical is None and len(monitors) == 1 and len(screens) == 1:
                logical = tuple(screens[0][1:])
            if logical is None:
                # An exact geometry match is safe even when XWayland renames connectors.
                logical = next((geometry for geometry in logical_by_name.values()
                                if tuple(native) == geometry), None)
            if logical is not None:
                screen_mappings.append((tuple(native), logical))
    records, occluders = [], []
    for window in data["windows"][:512]:
        if not isinstance(window, dict):
            continue
        if excluded_pid is not None and window.get("pid") == excluded_pid:
            continue
        rect = window.get("rect")
        if not isinstance(rect, list) or len(rect) != 4 or any(
                isinstance(value, bool) or not isinstance(value, (int, float)) or
                not math.isfinite(value) or abs(value) > 10_000_000 for value in rect):
            continue
        left, top, right, bottom = rect
        if right <= left or bottom <= top:
            continue
        rect = tuple(rect)
        tops = map_top_segments(visible_top_segments(rect, occluders), screen_mappings, scale)
        regions = map_top_segments([rect], screen_mappings, scale)
        occluders.append(rect)
        bounds = (min(r[0] for r in regions), min(r[1] for r in regions),
                  max(r[2] for r in regions), max(r[3] for r in regions))
        identity = window.get("id")
        if not isinstance(identity, str) or not identity or len(identity) > 128:
            continue
        records.append({"id": "gnome:" + identity, "rect": bounds, "regions": regions,
                        "tops": tops, "source": "gnome"})
    return records


class GnomeWindows:
    """Asynchronous geometry reads; absence of the extension never blocks Qt."""
    def __init__(self):
        self.pending = None
        self.records = []
        self.last_update = 0
        self.retry_at = 0
        self.last_error = "GNOME geometry extension not connected."
        self.failed = False
        self.screens = ()

    @property
    def available(self):
        return self.last_update > 0 and time.monotonic() - self.last_update < 1.5 and not self.failed

    def snapshots(self, scale=1, screens=()):
        now = time.monotonic()
        if self.pending is None and now >= self.retry_at:
            try:
                from PySide6.QtCore import QCoreApplication
                from PySide6.QtDBus import QDBusConnection, QDBusMessage, QDBusPendingCallWatcher
                if QCoreApplication.instance() is None:
                    return []
                connection = QDBusConnection.sessionBus()
                if not connection.isConnected():
                    raise RuntimeError("Desktop session D-Bus is unavailable.")
                message = QDBusMessage.createMethodCall(GNOME_BRIDGE_NAME, GNOME_BRIDGE_PATH,
                                                       GNOME_BRIDGE_NAME, "GetWindows")
                message.setArguments([os.getpid(), json.dumps([screen[0] for screen in screens])])
                message.setAutoStartService(False)
                self.screens = screens
                self.pending = QDBusPendingCallWatcher(connection.asyncCall(message, 600))
                self.pending.finished.connect(self._finished)
            except Exception as exc:
                self.failed = True
                self.last_error = str(exc)
                self.retry_at = now + 5
        return self.records if self.available else []

    def _finished(self, *args):
        watcher = self.pending
        self.pending = None
        try:
            if watcher.isError():
                raise RuntimeError(watcher.error().message())
            reply = watcher.reply().arguments()
            if len(reply) != 1:
                raise ValueError("Invalid GNOME geometry response.")
            self.records = parse_gnome_snapshot(reply[0], os.getpid(), screens=self.screens)
            self.last_update = time.monotonic()
            self.failed = False
            self.last_error = ""
        except Exception as exc:
            self.records = []
            self.failed = True
            self.last_error = str(exc)
            self.retry_at = time.monotonic() + 5
        finally:
            if watcher is not None:
                watcher.deleteLater()


class DesktopWindows:
    """Prefer the optional GNOME bridge; otherwise keep reliable X11 fallback."""
    def __init__(self):
        self.gnome = GnomeWindows()
        self.source = "x11"

    @property
    def last_error(self):
        if self.source == "gnome":
            return self.gnome.last_error
        return X11.last_error

    @property
    def bridge_status(self):
        return "connected" if self.gnome.available else self.gnome.last_error

    def snapshots(self, exclude_ids=(), scale=1, screens=()):
        if "GNOME" in os.environ.get("XDG_CURRENT_DESKTOP", "").upper():
            records = self.gnome.snapshots(scale, screens)
            if self.gnome.available:
                self.source = "gnome"
                return records
        self.source = "x11"
        return X11.snapshots(exclude_ids, scale, screens)

    def rectangles(self, exclude_ids=(), scale=1, screens=()):
        return [top for window in self.snapshots(exclude_ids, scale, screens) for top in window["tops"]]


DESKTOP = DesktopWindows()
