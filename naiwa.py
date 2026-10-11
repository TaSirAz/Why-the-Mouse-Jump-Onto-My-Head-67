"""Naiwa Roll Club — a transparent Windows / Linux desktop companion."""
import argparse
import ctypes
import json
import math
import os
from pathlib import Path
import random
import sys
import time
from collections import deque
from linux_desktop import X11, configure_qt_platform, display_error

configure_qt_platform()
if __name__ == "__main__" and display_error():
    raise SystemExit(display_error())

# The distributed executable's startup check must also report import failures,
# which happen before QApplication or argparse can run.
STARTUP_REPORT = None
STARTUP_ERRORS = []
if "--verify-startup-report" in sys.argv:
    report_index = sys.argv.index("--verify-startup-report") + 1
    if report_index < len(sys.argv):
        STARTUP_REPORT = Path(sys.argv[report_index]).resolve()

        def report_startup_failure(error_type, error, tb):
            import traceback
            STARTUP_ERRORS.append("".join(traceback.format_exception(error_type, error, tb)))
            STARTUP_REPORT.parent.mkdir(parents=True, exist_ok=True)
            STARTUP_REPORT.write_text(json.dumps({"ok": False,
                "error": "\n".join(STARTUP_ERRORS)}), encoding="utf-8")

        sys.excepthook = report_startup_failure

from PySide6.QtCore import QPoint, QRectF, Qt, QTimer, QStandardPaths, QLockFile
from PySide6.QtGui import (QAction, QBitmap, QColor, QCursor, QFont, QIcon,
                           QImage, QPainter, QPainterPath, QPen, QPixmap, QRegion)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QGridLayout,
    QHBoxLayout, QLabel, QMenu, QPushButton, QSlider, QSystemTrayIcon,
    QVBoxLayout, QWidget)
from physics import Body, collide, step

ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
MODES = {"wander": "自由翻滾", "follow": "追著滑鼠跑", "party": "暴走派對",
         "sleep": "乖乖睡覺", "focus": "專注陪伴"}
PALETTE = ["#ffe16b", "#8ef1dd", "#ff9ac2", "#aaa2ff", "#97cfff", "#ffbb86"]
UI_FONT = "Microsoft JhengHei" if sys.platform == "win32" else "Noto Sans CJK TC"
DISPLAY_FONT = "Segoe UI" if sys.platform == "win32" else "DejaVu Sans"


def clamp(value, low, high):
    return max(low, min(value, high))


def desktop_windows():
    """Read only visible external window top edges; never move external windows."""
    if sys.platform.startswith("linux"):
        app = QApplication.instance()
        if not app or app.platformName() != "xcb":
            return []
        scale = app.primaryScreen().devicePixelRatio()
        return X11.rectangles([int(w.winId()) for w in app.topLevelWidgets()], scale)
    if sys.platform != "win32":
        return []
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsIconic.argtypes = [wintypes.HWND]
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    windows = []

    @callback_type
    def collect(hwnd, _):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == os.getpid() or not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
            return True
        name = ctypes.create_unicode_buffer(128)
        user32.GetClassNameW(hwnd, name, 128)
        if name.value in {"Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd"}:
            return True
        rect = wintypes.RECT()
        if user32.GetWindowRect(hwnd, ctypes.byref(rect)) and rect.right - rect.left > 100 and rect.bottom - rect.top > 80:
            # EnumWindows visits frontmost first. Ignore tops occluded by earlier windows.
            if not any(l <= (rect.left + rect.right) / 2 <= r and t <= rect.top < b
                       for l, t, r, b in windows):
                windows.append((rect.left, rect.top, rect.right, rect.bottom))
        return True

    user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    user32.EnumWindows(collect, 0)
    return windows


class Toy(QWidget):
    def __init__(self, club, x, y, kind="pet"):
        super().__init__(None, Qt.WindowType.FramelessWindowHint |
                         Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.club, self.kind = club, kind
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setWindowTitle("Naiwa Roll Club")
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.body = Body(x, y, club.settings["size"] if kind == "pet" else (23 if kind == "ball" else 16))
        self.color = QColor(PALETTE[len(club.toys) % len(PALETTE)])
        self.particles = []
        self.trail = deque(maxlen=12)
        self.drag_samples = deque(maxlen=10)
        self.drag_offset = QPoint()
        self.press_at = QPoint()
        self.moved = False
        self.bubble, self.bubble_until = "", 0
        self.squash = 0
        self.next_action = time.monotonic() + random.uniform(1, 4)
        self.hunger, self.energy = 70.0, 90.0
        self.combo = 0
        self.last_hit = 0
        self.buffer = QImage()
        self.refresh_size()
        self.show()
        if kind == "pet":
            self.say(random.choice(["Naiwa 報到！", "今天也要滾起來！", "把我抓起來丟！"]), 3)

    def refresh_size(self):
        diameter = int(self.body.r * 2 + 140)
        self.resize(diameter, diameter + 55)
        self.cx, self.cy = diameter / 2, diameter / 2 + 40

    def say(self, text, seconds=2.3):
        self.bubble, self.bubble_until = text, time.monotonic() + seconds

    def burst(self, force=300, hearts=False):
        for _ in range(min(22, 7 + int(force / 90))):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(35, min(250, 70 + force / 4))
            self.particles.append([0., 0., math.cos(angle) * speed,
                                   math.sin(angle) * speed, random.uniform(.35, .75), hearts])
        self.particles = self.particles[-65:]
        self.squash = min(.24, force / 3500)

    def impact(self, speed):
        if speed < 120 or self.kind != "pet":
            return
        now = time.monotonic()
        self.combo = self.combo + 1 if now - self.last_hit < 2.5 else 1
        self.last_hit = now
        self.club.stats["bounces"] += 1
        self.club.stats["best_combo"] = max(self.club.stats["best_combo"], self.combo)
        self.burst(speed)
        if self.combo >= 3:
            self.say(f"{self.combo} HIT！再來！", 1.3)
        elif speed > 800:
            self.say(random.choice(["飛起來啦！", "這就是物理！", "我沒事，真的。"]), 1.7)

    def render_frame(self, dt):
        b = self.body
        self.move(round(b.x - self.cx), round(b.y - self.cy))
        image = QImage(self.size(), QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        p = QPainter(image)
        p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        p.translate(self.cx, self.cy)
        speed = math.hypot(b.vx, b.vy)
        if self.club.settings["trails"] and speed > 380:
            self.trail.append((b.x, b.y))
        else:
            if self.trail:
                self.trail.popleft()
        for i, (x, y) in enumerate(self.trail):
            c = QColor(self.color)
            c.setAlpha(int(65 * (i + 1) / max(1, len(self.trail))))
            p.setBrush(c)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPoint(round(x - b.x), round(y - b.y)), 6 + i, 6 + i)
        for particle in self.particles[:]:
            particle[0] += particle[2] * dt
            particle[1] += particle[3] * dt
            particle[3] += 200 * dt
            particle[4] -= dt
            if particle[4] <= 0:
                self.particles.remove(particle)
                continue
            c = QColor("#ff80ae" if particle[5] else self.color)
            c.setAlpha(int(min(1, particle[4] * 3) * 240))
            p.setPen(c)
            if particle[5]:
                p.setFont(QFont(DISPLAY_FONT, 15))
                p.drawText(QPoint(round(particle[0]), round(particle[1])), "♥")
            else:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(c)
                p.drawEllipse(QPoint(round(particle[0]), round(particle[1])), 3, 3)
        p.save()
        p.rotate(b.angle)
        self.squash *= math.exp(-dt * 13)
        p.scale(1 + self.squash, 1 - self.squash)
        if self.kind == "pet":
            h = b.r * 2
            w = h * self.club.sprite.width() / self.club.sprite.height()
            p.drawPixmap(QRectF(-w / 2, -h / 2, w, h), self.club.sprite, self.club.sprite.rect())
        elif self.kind == "ball":
            p.setPen(QPen(QColor("#fff9d9"), 2))
            p.setBrush(self.color)
            p.drawEllipse(QRectF(-b.r, -b.r, b.r * 2, b.r * 2))
            p.setPen(QPen(QColor("#426c76"), 3))
            p.drawLine(-int(b.r), 0, int(b.r), 0)
            p.drawLine(0, -int(b.r), 0, int(b.r))
        else:
            p.setBrush(QColor("#f1bb71"))
            p.setPen(QPen(QColor("#fff0bd"), 2))
            p.drawEllipse(QRectF(-15, -15, 30, 30))
            p.setBrush(QColor("#ff99b8"))
            p.drawEllipse(QRectF(-12, -12, 24, 21))
            p.setBrush(QColor("#925943"))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QRectF(-4, -4, 8, 8))
        p.restore()
        now = time.monotonic()
        if self.kind == "pet" and self.club.mode in {"sleep", "focus"}:
            p.setPen(QColor("#a9d5ff"))
            p.setFont(QFont(DISPLAY_FONT, 16, QFont.Weight.Bold))
            p.drawText(QPoint(int(b.r * .5), -int(b.r)), "z Z")
        if self.bubble and now < self.bubble_until:
            p.setFont(QFont(UI_FONT, 10, QFont.Weight.DemiBold))
            width = min(self.width() - 10, p.fontMetrics().horizontalAdvance(self.bubble) + 24)
            rect = QRectF(-width / 2, -self.cy + 6, width, 35)
            p.setPen(QPen(self.color, 1.5))
            p.setBrush(QColor("#192635"))
            p.drawRoundedRect(rect, 12, 12)
            p.setPen(QColor("#fff8dc"))
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.bubble)
        p.end()
        self.buffer = image
        # Only visible pixels receive clicks; the transparent margin never blocks work.
        self.setMask(QRegion(QBitmap.fromImage(image.createAlphaMask())))
        self.update()

    def paintEvent(self, _):
        painter = QPainter(self)
        painter.drawImage(0, 0, self.buffer)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.club.context_menu(self).popup(event.globalPosition().toPoint())
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self.body.held = True
        self.body.vx = self.body.vy = 0
        self.press_at = event.globalPosition().toPoint()
        self.drag_offset = self.press_at - QPoint(round(self.body.x), round(self.body.y))
        self.drag_samples.clear()
        self.drag_samples.append((time.monotonic(), self.body.x, self.body.y))
        self.moved = False
        self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if not self.body.held:
            return
        pos = event.globalPosition().toPoint()
        self.moved |= (pos - self.press_at).manhattanLength() > 6
        point = pos - self.drag_offset
        self.body.x, self.body.y = point.x(), point.y()
        self.body.angle *= .85
        self.drag_samples.append((time.monotonic(), self.body.x, self.body.y))

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or not self.body.held:
            return
        self.body.held = False
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        if not self.moved:
            self.pet()
            return
        now = time.monotonic()
        samples = [s for s in self.drag_samples if now - s[0] < .13]
        # Include the release time: stopping before release does not create a stale throw.
        samples.append((now, self.body.x, self.body.y))
        if len(samples) >= 2:
            elapsed = max(.015, samples[-1][0] - samples[0][0])
            self.body.vx = clamp((samples[-1][1] - samples[0][1]) / elapsed, -1900, 1900)
            self.body.vy = clamp((samples[-1][2] - samples[0][2]) / elapsed, -1900, 1900)
            self.body.spin = self.body.vx * .6
            if self.kind == "pet":
                self.club.stats["throws"] += 1
                self.say("咻～～～！")

    def pet(self):
        if self.kind != "pet":
            self.body.vy = -450
            return
        self.energy = min(100, self.energy + 8)
        self.club.stats["pets"] += 1
        self.body.vy = -360
        self.body.spin += random.choice([-180, 180])
        self.burst(220, hearts=True)
        self.say(random.choice(["摸摸收到 ♥", "再摸一下嘛！", "好耶！", "你今天也很棒。"] ))

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.body.held = False
            self.body.vy = -850
            self.body.spin = random.choice([-1050, 1050])
            self.burst(700)
            self.say("Naiwa 旋風！")

    def wheelEvent(self, event):
        if self.kind == "pet":
            self.club.set_size(clamp(self.body.r + event.angleDelta().y() / 120 * 4, 38, 100))


class Panel(QWidget):
    def __init__(self, club):
        super().__init__()
        self.club = club
        self.setWindowTitle("Naiwa Roll Club · 控制室")
        self.setWindowIcon(QIcon(club.sprite))
        self.setMinimumWidth(440)
        self.setStyleSheet("""
            QWidget {background:#111c29; color:#eaf0f7; font:14px 'Microsoft JhengHei';}
            QLabel#title {font:700 29px 'Segoe UI'; color:#ffe16b;}
            QLabel#sub {color:#9dacbc; font-size:13px;}
            QLabel#stats {background:#1c2c3e; padding:16px; border-radius:14px; line-height:1.6;}
            QPushButton {background:#24374b; border:1px solid #344a61; border-radius:10px;
                         padding:11px 13px; text-align:left;}
            QPushButton:hover {background:#344d65; border-color:#ffe16b;}
            QPushButton#primary {background:#ffe16b; color:#1c2630; font-weight:700;}
            QComboBox {background:#24374b; border:1px solid #344a61; border-radius:8px; padding:8px;}
            QSlider::groove:horizontal {background:#304255; height:5px; border-radius:2px;}
            QSlider::handle:horizontal {background:#ffe16b; width:16px; margin:-6px 0; border-radius:8px;}
            QCheckBox {spacing:8px; padding:4px;} QCheckBox::indicator {width:17px; height:17px;}
        """.replace("Microsoft JhengHei", UI_FONT).replace("Segoe UI", DISPLAY_FONT))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 23, 25, 23)
        layout.setSpacing(13)
        title = QLabel("NAIWA ROLL CLUB")
        title.setObjectName("title")
        layout.addWidget(title)
        sub = QLabel("抓起來，甩出去。讓今天多一點無用的快樂。")
        sub.setObjectName("sub")
        layout.addWidget(sub)
        self.status = QLabel()
        self.status.setObjectName("stats")
        layout.addWidget(self.status)
        self.modes = QComboBox()
        for key, name in MODES.items():
            self.modes.addItem(name, key)
        self.modes.setCurrentIndex(list(MODES).index(club.mode))
        self.modes.currentIndexChanged.connect(lambda _: club.set_mode(self.modes.currentData()))
        layout.addWidget(self.modes)
        grid = QGridLayout()
        actions = [("↗  全員發射", club.launch_all), ("♡  甜甜圈時間", club.feed),
                   ("＋  多一隻 Naiwa", club.add_pet), ("●  丟一顆球", club.add_ball),
                   ("✦  反重力 10 秒", club.antigravity), ("⌂  全員回家", club.rescue)]
        for i, (text, action) in enumerate(actions):
            button = QPushButton(text)
            if i == 0:
                button.setObjectName("primary")
            button.clicked.connect(lambda checked=False, fn=action: fn())
            grid.addWidget(button, i // 2, i % 2)
        layout.addLayout(grid)
        self.size_label = QLabel()
        layout.addWidget(self.size_label)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(38, 100)
        self.slider.setValue(int(club.settings["size"]))
        self.slider.valueChanged.connect(club.set_size)
        layout.addWidget(self.slider)
        for key, label in [("windows", "在其他視窗頂端落地 / 翻滾"),
                           ("trails", "高速殘影與碰撞粒子"), ("low_gravity", "月球重力")]:
            check = QCheckBox(label)
            check.setChecked(club.settings[key])
            check.toggled.connect(lambda value, k=key: club.settings.__setitem__(k, value))
            layout.addWidget(check)
        focus = QHBoxLayout()
        self.focus_minutes = QComboBox()
        for minutes in [5, 15, 25, 50]:
            self.focus_minutes.addItem(f"{minutes} 分鐘", minutes)
        self.focus_minutes.setCurrentIndex(2)
        focus.addWidget(self.focus_minutes)
        start = QPushButton("◷  開始專注")
        start.clicked.connect(lambda: club.start_focus(self.focus_minutes.currentData()))
        focus.addWidget(start)
        layout.addLayout(focus)
        hint = QLabel("左鍵摸摸 · 拖曳拋擲 · 雙擊旋風 · 滾輪改大小\n右鍵更多功能 · 系統托盤可以暫停、找回或退出")
        hint.setObjectName("sub")
        layout.addWidget(hint)
        bottom = QHBoxLayout()
        self.pause_button = QPushButton("Ⅱ  暫停 / 繼續")
        self.pause_button.clicked.connect(club.toggle_pause)
        bottom.addWidget(self.pause_button)
        hide = QPushButton("收起控制室")
        hide.clicked.connect(self.hide)
        bottom.addWidget(hide)
        layout.addLayout(bottom)
        quit_button = QPushButton("退出 Naiwa")
        quit_button.clicked.connect(lambda: club.app.exit(0))
        layout.addWidget(quit_button)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(500)
        self.refresh()

    def refresh(self):
        c = self.club
        pets = [t for t in c.toys if t.kind == "pet"]
        hunger = round(sum(p.hunger for p in pets) / max(1, len(pets)))
        focus = ""
        if c.focus_until:
            seconds = max(0, int(c.focus_until - time.monotonic()))
            focus = f"\n專注倒數  {seconds // 60:02}:{seconds % 60:02}"
        self.status.setText(f"{len(pets)} 隻 Naiwa  ·  飽足 {hunger}%  ·  {'已暫停' if c.paused else MODES[c.mode]}\n"
            f"碰撞 {c.stats['bounces']}  ·  拋擲 {c.stats['throws']}  ·  最佳連擊 {c.stats['best_combo']}\n"
            f"摸摸 {c.stats['pets']}  ·  吃點心 {c.stats['snacks']}  ·  專注完成 {c.stats['focus_sessions']}{focus}")
        self.size_label.setText(f"Naiwa 大小  ·  {int(c.settings['size'] * 2)} px")
        self.modes.blockSignals(True)
        self.modes.setCurrentIndex(list(MODES).index(c.mode))
        self.modes.blockSignals(False)

    def closeEvent(self, event):
        event.ignore()
        self.hide()


class Club:
    def __init__(self, app, data_dir=None):
        self.app = app
        self.data_dir = Path(data_dir or QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.settings = {"size": 64, "windows": True, "trails": True, "low_gravity": False}
        self.stats = dict.fromkeys(["bounces", "throws", "best_combo", "pets", "snacks", "focus_sessions"], 0)
        self.load()
        self.mode, self.paused = "wander", False
        self.toys = []
        self.sprite = QPixmap(str(ROOT / "assets" / "naiwa.png"))
        if self.sprite.isNull():
            raise RuntimeError("找不到 assets/naiwa.png，請重新解壓完整下載檔。")
        self.sprite = self.sprite.scaled(320, 320, Qt.AspectRatioMode.KeepAspectRatio,
                                         Qt.TransformationMode.SmoothTransformation)
        self.focus_until = 0
        self.antigravity_until = 0
        self.window_rects = []
        self.last = time.monotonic()
        self.accumulator = 0
        self.menu = None
        self.tray = QSystemTrayIcon(QIcon(self.sprite), app)
        self.tray.setToolTip("Naiwa Roll Club · 左鍵控制室，右鍵更多")
        self.tray.activated.connect(self.tray_activated)
        self.tray.setContextMenu(self.context_menu())
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()
        self.panel = Panel(self)
        self.add_pet()
        self.timer = QTimer()
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.timeout.connect(self.tick)
        self.timer.start(16)
        self.window_timer = QTimer()
        self.window_timer.timeout.connect(self.scan_windows)
        self.window_timer.start(350)
        self.save_timer = QTimer()
        self.save_timer.timeout.connect(self.save)
        self.save_timer.start(30000)
        self.app.aboutToQuit.connect(self.save)
        self.app.screenAdded.connect(lambda _: self.rescue())
        self.app.screenRemoved.connect(lambda _: QTimer.singleShot(150, self.rescue))

    def load(self):
        try:
            data = json.loads((self.data_dir / "settings.json").read_text(encoding="utf-8"))
            raw = data.get("settings", {})
            if isinstance(raw.get("size"), (int, float)):
                self.settings["size"] = clamp(raw["size"], 38, 100)
            for key in ["windows", "trails", "low_gravity"]:
                if isinstance(raw.get(key), bool):
                    self.settings[key] = raw[key]
            for key in self.stats:
                value = data.get("stats", {}).get(key)
                if isinstance(value, int) and value >= 0:
                    self.stats[key] = value
        except (OSError, ValueError, TypeError, AttributeError):
            pass

    def save(self):
        try:
            temp = self.data_dir / "settings.tmp"
            temp.write_text(json.dumps({"settings": self.settings, "stats": self.stats}, ensure_ascii=False), encoding="utf-8")
            temp.replace(self.data_dir / "settings.json")
        except OSError:
            pass

    def bounds(self, body):
        point = QPoint(round(body.x), round(body.y))
        screen = self.app.screenAt(point)
        if screen is None:
            screens = self.app.screens()
            screen = min(screens, key=lambda s: (s.availableGeometry().center() - point).manhattanLength())
        rect = screen.availableGeometry()
        return rect.left(), rect.top(), rect.right() + 1, rect.bottom() + 1

    def spawn_point(self):
        screen = self.app.screenAt(QCursor.pos()) or self.app.primaryScreen()
        rect = screen.availableGeometry()
        return rect.center().x() + random.randint(-130, 130), rect.top() + 130

    def add_pet(self):
        if sum(t.kind == "pet" for t in self.toys) >= 6:
            self.say_all("六隻就已經很鬧了！")
            return
        t = Toy(self, *self.spawn_point())
        t.body.vx, t.body.spin = random.uniform(-180, 180), random.uniform(-180, 180)
        self.toys.append(t)

    def add_ball(self):
        if sum(t.kind == "ball" for t in self.toys) >= 4:
            return
        t = Toy(self, *self.spawn_point(), "ball")
        t.body.vx = random.choice([-260, 260])
        self.toys.append(t)

    def feed(self):
        pets = [t for t in self.toys if t.kind == "pet"]
        capacity = 8 - sum(t.kind == "food" for t in self.toys)
        for pet in pets[:max(0, capacity)]:
            l, top, r, bottom = self.bounds(pet.body)
            food = Toy(self, clamp(pet.body.x + random.choice([-130, 130]), l + 20, r - 20),
                       clamp(pet.body.y - 160, top + 20, bottom - 20), "food")
            self.toys.append(food)
            pet.say("聞到甜甜圈了！")

    def remove(self, toy):
        if toy.kind == "pet" and sum(t.kind == "pet" for t in self.toys) == 1:
            toy.say("最後一隻不想走～")
            return
        if toy in self.toys:
            self.toys.remove(toy)
            toy.close()
            toy.deleteLater()

    def set_size(self, size):
        self.settings["size"] = int(size)
        for toy in self.toys:
            if toy.kind == "pet":
                toy.body.r = size
                toy.refresh_size()
        if hasattr(self, "panel"):
            self.panel.slider.blockSignals(True)
            self.panel.slider.setValue(int(size))
            self.panel.slider.blockSignals(False)

    def say_all(self, text):
        for t in self.toys:
            if t.kind == "pet":
                t.say(text)

    def set_mode(self, mode):
        if mode not in MODES:
            return
        self.mode = mode
        if mode != "focus":
            self.focus_until = 0
        if mode in {"sleep", "focus"}:
            for toy in self.toys:
                toy.body.vx = toy.body.spin = 0
                toy.body.angle = 0
        self.say_all(MODES[mode])

    def start_focus(self, minutes):
        self.set_mode("focus")
        self.focus_until = time.monotonic() + minutes * 60
        self.say_all("我陪你，慢慢做就好。")

    def antigravity(self):
        self.antigravity_until = time.monotonic() + 10
        self.say_all("重力請假十秒！")

    def launch_all(self):
        self.paused = False
        if self.mode in {"sleep", "focus"}:
            self.set_mode("wander")
        for t in self.toys:
            if not t.body.held:
                t.body.vx = random.choice([-1, 1]) * random.uniform(550, 1100)
                t.body.vy = -random.uniform(600, 1050)
                t.body.spin = random.choice([-900, 900])
                t.burst(850)
                t.say("發射！")

    def rescue(self):
        for i, t in enumerate(self.toys):
            screen = self.app.screenAt(QCursor.pos()) or self.app.primaryScreen()
            rect = screen.availableGeometry()
            t.body.x = clamp(rect.center().x() + (i - 2) * 145, rect.left() + t.body.r, rect.right() - t.body.r)
            t.body.y = rect.top() + 150
            t.body.vx = t.body.vy = t.body.spin = t.body.angle = 0
            t.body.held = False
            t.say("安全回家！")

    def toggle_pause(self):
        self.paused = not self.paused
        self.say_all("休息一下。" if self.paused else "繼續滾！")

    def show_panel(self):
        self.panel.show()
        self.panel.raise_()
        self.panel.activateWindow()

    def tray_activated(self, reason):
        if reason in {QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick}:
            self.show_panel()

    def context_menu(self, toy=None):
        menu = QMenu()
        menu.setStyleSheet("QMenu {background:#192635; color:#f5f3e7; padding:6px;} QMenu::item {padding:8px 20px;} QMenu::item:selected {background:#3a526a;}")
        def action(text, fn):
            a = QAction(text, menu)
            a.triggered.connect(lambda checked=False: fn())
            menu.addAction(a)
        action("Naiwa 控制室", self.show_panel)
        action("全員發射！", self.launch_all)
        action("餵甜甜圈", self.feed)
        action("增加 Naiwa", self.add_pet)
        action("丟一顆球", self.add_ball)
        action("反重力十秒", self.antigravity)
        modes = menu.addMenu("心情模式")
        for key, label in MODES.items():
            a = QAction(label, modes)
            a.triggered.connect(lambda checked=False, k=key: self.set_mode(k))
            modes.addAction(a)
        menu.addSeparator()
        if toy:
            action("摸摸 / 彈一下", toy.pet)
            action("送這一隻回家", lambda: self.remove(toy))
        action("暫停 / 繼續", self.toggle_pause)
        action("找回所有桌寵", self.rescue)
        action("清掉球與點心", lambda: [self.remove(t) for t in self.toys[:] if t.kind != "pet"])
        action("退出 Naiwa", lambda: self.app.exit(0))
        self.menu = menu  # Keep popup alive beyond mousePressEvent.
        return menu

    def scan_windows(self):
        self.window_rects = desktop_windows() if self.settings["windows"] and not self.paused else []

    def tick(self):
        now = time.monotonic()
        elapsed = min(.08, now - self.last)
        self.last = now
        if self.focus_until and now >= self.focus_until:
            self.focus_until = 0
            self.stats["focus_sessions"] += 1
            self.mode = "wander"
            self.say_all("完成了！休息一下，喝口水 ♥")
            self.tray.showMessage("Naiwa 陪你完成了", "專注時間結束。伸展一下，喝口水吧！", QSystemTrayIcon.MessageIcon.Information, 6000)
            for t in self.toys:
                t.burst(300, True)
        if not self.paused:
            self.accumulator += elapsed
            while self.accumulator >= 1 / 120:
                self.simulate(1 / 120, now)
                self.accumulator -= 1 / 120
        else:
            self.accumulator = 0
        for t in self.toys[:]:
            t.render_frame(elapsed)

    def simulate(self, dt, now):
        gravity = -450 if now < self.antigravity_until else (270 if self.settings["low_gravity"] else 1250)
        cursor = QCursor.pos()
        foods = [t for t in self.toys if t.kind == "food"]
        for t in self.toys[:]:
            b = t.body
            previous_y = b.y
            drive = 0
            if t.kind == "pet" and not b.held:
                t.hunger = max(0, t.hunger - dt * .025)
                t.energy = clamp(t.energy + dt * (.3 if self.mode in {"sleep", "focus"} else -.01), 0, 100)
                if self.mode not in {"sleep", "focus"}:
                    target = min(foods, key=lambda f: math.hypot(f.body.x - b.x, f.body.y - b.y)) if foods else None
                    if target or self.mode == "follow":
                        x = target.body.x if target else cursor.x()
                        drive = clamp((x - b.x) * 3 - b.vx * 2.5, -650, 650)
                    if now >= t.next_action:
                        t.next_action = now + random.uniform(2, 5) / (2 if self.mode == "party" else 1)
                        if b.grounded or self.mode == "party":
                            b.vx += random.choice([-1, 1]) * random.uniform(80, 230)
                            if self.mode == "party" or random.random() < .28:
                                b.vy = -random.uniform(350, 680)
                                b.spin += random.choice([-360, 360])
                elif b.grounded:
                    b.vx *= .92
                    b.angle = (b.angle + ((-b.angle + 180) % 360 - 180) * dt * 6) % 360
                    b.spin *= .9
            hits = step(b, self.bounds(b), dt, gravity, .83 if t.kind == "ball" else .69, drive)
            for _, speed, _, _ in hits:
                t.impact(speed)
            if self.settings["windows"] and gravity > 0 and not b.held and b.vy >= 0:
                for left, top, right, bottom in self.window_rects:
                    # A top edge is one-way: passing upward through it is allowed.
                    if left + 8 < b.x < right - 8 and previous_y + b.r <= top + 2 and b.y + b.r >= top:
                        speed = b.vy
                        b.y = top - b.r
                        b.vy = -speed * .58 if speed > 100 else 0
                        b.grounded = speed <= 100
                        b.vx *= .992
                        t.impact(speed)
                        break
        toys = self.toys[:]
        consumed = set()
        for i, a in enumerate(toys):
            for b in toys[i + 1:]:
                if a in consumed or b in consumed:
                    continue
                if {a.kind, b.kind} == {"food", "pet"}:
                    pet, food = (a, b) if a.kind == "pet" else (b, a)
                    if math.hypot(a.body.x - b.body.x, a.body.y - b.body.y) < a.body.r + b.body.r + 6:
                        consumed.add(food)
                        pet.hunger = min(100, pet.hunger + 25)
                        pet.energy = min(100, pet.energy + 10)
                        self.stats["snacks"] += 1
                        pet.say(random.choice(["好吃！再一個？", "甜甜圈是圓的，我也是。", "補充翻滾燃料 ♥"]))
                        pet.burst(200, True)
                else:
                    speed = collide(a.body, b.body)
                    if speed > 120:
                        a.impact(speed)
                        b.impact(speed)
        for food in consumed:
            self.remove(food)


def main():
    parser = argparse.ArgumentParser(description="Naiwa Roll Club")
    parser.add_argument("--panel", action="store_true", help="show the control room")
    parser.add_argument("--verify-startup-report", help=argparse.SUPPRESS)
    args = parser.parse_args()
    app = QApplication(sys.argv[:1])
    app.setApplicationName("NaiwaRollClub")
    app.setOrganizationName("Naiwa")
    app.setQuitOnLastWindowClosed(False)
    if args.verify_startup_report:
        import tempfile
        from PySide6.QtCore import qVersion
        with tempfile.TemporaryDirectory(prefix="naiwa-check-") as temporary_data:
            club = Club(app, temporary_data)
            club.show_panel()
            def finish_check():
                club.scan_windows()
                pet = club.toys[0]
                pet.render_frame(1 / 60)
                report = {"ok": not STARTUP_ERRORS and not pet.buffer.isNull() and club.panel.isVisible(),
                          "error": "\n".join(STARTUP_ERRORS),
                          "qt": qVersion(), "pet_visible": pet.isVisible(),
                          "frames_rendered": True, "windows_scan": True,
                          "platform": app.platformName(), "window_rects": club.window_rects}
                STARTUP_REPORT.parent.mkdir(parents=True, exist_ok=True)
                STARTUP_REPORT.write_text(json.dumps(report), encoding="utf-8")
                app.exit(0)
            QTimer.singleShot(1200, finish_check)
            result = app.exec()
            report = json.loads(STARTUP_REPORT.read_text(encoding="utf-8"))
            report["event_loop_exited"] = True
            STARTUP_REPORT.write_text(json.dumps(report), encoding="utf-8")
            return result
    data_dir = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))
    data_dir.mkdir(parents=True, exist_ok=True)
    lock = QLockFile(str(data_dir / "naiwa.lock"))
    lock.setStaleLockTime(0)
    if not lock.tryLock(100):
        return 0  # Existing instance remains available through its tray icon.
    club = Club(app)
    if args.panel or not QSystemTrayIcon.isSystemTrayAvailable():
        club.show_panel()
    club.say_all("右鍵我，或點托盤開控制室！")
    return app.exec()


if __name__ == "__main__":
    exit_code = main()
    if STARTUP_REPORT and STARTUP_REPORT.exists():
        report = json.loads(STARTUP_REPORT.read_text(encoding="utf-8"))
        report["main_returned"] = True
        STARTUP_REPORT.write_text(json.dumps(report), encoding="utf-8")
    raise SystemExit(exit_code)
