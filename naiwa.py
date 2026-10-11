"""Customizable transparent desktop companions for Windows and Ubuntu."""
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
if __name__ == "__main__":
    startup_display_error = display_error(require_visible="--verify-startup-report" in sys.argv)
    if startup_display_error:
        raise SystemExit(startup_display_error)

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

from PySide6.QtCore import QPoint, QRectF, Qt, QTimer, QStandardPaths, QLockFile, QObject, QThread, Signal, Slot
from PySide6.QtGui import (QAction, QBitmap, QColor, QCursor, QFont, QIcon,
                           QImage, QPainter, QPainterPath, QPen, QPixmap, QRegion)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QGridLayout,
    QHBoxLayout, QLabel, QMenu, QPushButton, QScrollArea, QSlider, QSystemTrayIcon,
    QVBoxLayout, QWidget, QFileDialog)
from physics import Body, collide, step, substep_count, constrain
from project_info import APP_NAME, APP_ID, ORGANIZATION, LEGACY_APP_ID, LEGACY_ORGANIZATION
from pet_images import import_pet_image, load_custom_pet_image, reset_pet_image

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
        screens = [(screen.name(), screen.geometry().x(), screen.geometry().y(),
                    screen.geometry().width(), screen.geometry().height()) for screen in app.screens()]
        return X11.rectangles([int(w.winId()) for w in app.topLevelWidgets()], scale, screens=screens)
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
        self.setWindowTitle(APP_NAME)
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
            scale = b.r * 2 / max(self.club.sprite.width(), self.club.sprite.height())
            w, h = self.club.sprite.width() * scale, self.club.sprite.height() * scale
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
        self.setWindowTitle(APP_NAME + " · 控制室")
        self.setWindowIcon(QIcon(club.sprite))
        available = club.app.primaryScreen().availableGeometry()
        self.setMinimumWidth(min(440, max(240, available.width() - 32)))
        self.setStyleSheet("""
            QWidget {background:#111c29; color:#eaf0f7; font:14px 'Microsoft JhengHei';}
            QLabel#title {font:700 21px 'Segoe UI'; color:#ffe16b;}
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
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        content = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(content)
        outer_layout.addWidget(scroll)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(25, 23, 25, 23)
        layout.setSpacing(13)
        title = QLabel(APP_NAME)
        title.setWordWrap(True)
        title.setObjectName("title")
        layout.addWidget(title)
        sub = QLabel("抓起來，甩出去。讓今天多一點無用的快樂。")
        sub.setWordWrap(True)
        sub.setObjectName("sub")
        layout.addWidget(sub)
        self.notice = QLabel()
        self.notice.setWordWrap(True)
        self.notice.setStyleSheet("color:#ffe16b;")
        layout.addWidget(self.notice)
        if sys.platform.startswith("linux") and os.environ.get("WAYLAND_DISPLAY"):
            session_hint = QLabel("Wayland：桌寵功能可用；僅能在 XWayland 視窗頂端落地。")
            session_hint.setWordWrap(True)
            session_hint.setObjectName("sub")
            layout.addWidget(session_hint)
        self.status = QLabel()
        self.status.setObjectName("stats")
        layout.addWidget(self.status)
        self.modes = QComboBox()
        for key, name in MODES.items():
            self.modes.addItem(name, key)
        self.modes.setCurrentIndex(list(MODES).index(club.mode))
        self.modes.currentIndexChanged.connect(lambda _: club.set_mode(self.modes.currentData()))
        layout.addWidget(self.modes)
        self.setAcceptDrops(True)
        self.image_preview = QLabel()
        self.image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_preview.setStyleSheet("background:#24374b; border-radius:10px; padding:8px;")
        layout.addWidget(self.image_preview)
        self.auto_background = QCheckBox("匯入時自動去背（純色背景）")
        self.auto_background.setChecked(True)
        layout.addWidget(self.auto_background)
        tolerance_row = QHBoxLayout()
        self.tolerance_label = QLabel("去背容差：36")
        tolerance_row.addWidget(self.tolerance_label)
        self.background_tolerance = QSlider(Qt.Orientation.Horizontal)
        self.background_tolerance.setRange(0, 100)
        self.background_tolerance.setValue(36)
        self.background_tolerance.valueChanged.connect(lambda value: self.tolerance_label.setText(f"去背容差：{value}"))
        self.background_tolerance.setToolTip("提高容差可移除更多近似背景色；再次匯入原圖以重試。")
        tolerance_row.addWidget(self.background_tolerance)
        layout.addLayout(tolerance_row)
        image_actions = QHBoxLayout()
        self.import_button = QPushButton("匯入 PNG / JPG")
        self.import_button.clicked.connect(club.choose_pet_image)
        self.reset_image_button = QPushButton("還原預設角色")
        self.reset_image_button.clicked.connect(club.reset_image)
        image_actions.addWidget(self.import_button)
        image_actions.addWidget(self.reset_image_button)
        layout.addLayout(image_actions)
        self.image_status = QLabel("也可以將一張 PNG / JPG 拖入控制室。原始檔案不會被改動。")
        self.image_status.setWordWrap(True)
        self.image_status.setObjectName("sub")
        layout.addWidget(self.image_status)
        self.refresh_image_preview()
        grid = QGridLayout()
        actions = [("↗  全員發射", club.launch_all), ("♡  甜甜圈時間", club.feed),
                   ("＋  多一隻桌寵", club.add_pet), ("●  丟一顆球", club.add_ball),
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
            check.toggled.connect(lambda value, k=key: club.set_option(k, value))
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
        hint.setWordWrap(True)
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
        quit_button = QPushButton("退出程式")
        quit_button.clicked.connect(lambda: club.app.exit(0))
        layout.addWidget(quit_button)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(500)
        self.refresh()
        screen = club.app.primaryScreen().availableGeometry()
        self.resize(min(460, max(240, screen.width() - 32)), min(830, max(240, screen.height() - 32)))

    def refresh(self):
        c = self.club
        pets = [t for t in c.toys if t.kind == "pet"]
        hunger = round(sum(p.hunger for p in pets) / max(1, len(pets)))
        focus = ""
        if c.focus_until:
            seconds = max(0, int(c.focus_until - time.monotonic()))
            focus = f"\n專注倒數  {seconds // 60:02}:{seconds % 60:02}"
        self.status.setText(f"{len(pets)} 隻桌寵  ·  飽足 {hunger}%  ·  {'已暫停' if c.paused else MODES[c.mode]}\n"
            f"碰撞 {c.stats['bounces']}  ·  拋擲 {c.stats['throws']}  ·  最佳連擊 {c.stats['best_combo']}\n"
            f"摸摸 {c.stats['pets']}  ·  吃點心 {c.stats['snacks']}  ·  專注完成 {c.stats['focus_sessions']}{focus}")
        notices = "\n".join(filter(None, [c.notice, c.desktop_notice]))
        self.notice.setText(notices)
        self.notice.setVisible(bool(notices))
        self.pause_button.setText("▶  繼續" if c.paused else "Ⅱ  暫停")
        self.size_label.setText(f"桌寵大小  ·  {int(c.settings['size'] * 2)} px")
        self.modes.blockSignals(True)
        self.modes.setCurrentIndex(list(MODES).index(c.mode))
        self.modes.blockSignals(False)

    def refresh_image_preview(self):
        self.image_preview.setPixmap(self.club.sprite.scaled(96, 96,
            Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def dragEnterEvent(self, event):
        urls = event.mimeData().urls()
        if len(urls) == 1 and urls[0].isLocalFile() and Path(urls[0].toLocalFile()).suffix.lower() in {".png", ".jpg", ".jpeg"}:
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if len(urls) == 1 and urls[0].isLocalFile():
            self.club.import_image(urls[0].toLocalFile())
            event.acceptProposedAction()

    def closeEvent(self, event):
        event.ignore()
        self.hide()


class ImageImportWorker(QObject):
    completed = Signal(object)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, source, data_dir, remove_background, tolerance):
        super().__init__()
        self.source, self.data_dir = source, data_dir
        self.remove_background, self.tolerance = remove_background, tolerance

    def run(self):
        try:
            self.completed.emit(import_pet_image(self.source, self.data_dir,
                remove_background=self.remove_background, tolerance=self.tolerance))
        except Exception as error:
            self.failed.emit(str(error))
        finally:
            self.finished.emit()


class Club(QObject):
    def __init__(self, app, data_dir=None):
        super().__init__(app)
        self.app = app
        self.data_dir = Path(data_dir or QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.settings = {"size": 64, "windows": True, "trails": True, "low_gravity": False}
        self.stats = dict.fromkeys(["bounces", "throws", "best_combo", "pets", "snacks", "focus_sessions"], 0)
        self.load()
        self.mode, self.paused = "wander", False
        self.notice = ""
        self.desktop_notice = ""
        self.toys = []
        self.sprite = QPixmap(str(ROOT / "assets" / "naiwa.png"))
        if self.sprite.isNull():
            raise RuntimeError("找不到 assets/naiwa.png，請重新解壓完整下載檔。")
        self.default_sprite = self.sprite.scaled(320, 320, Qt.AspectRatioMode.KeepAspectRatio,
                                         Qt.TransformationMode.SmoothTransformation)
        custom_image = load_custom_pet_image(self.data_dir)
        self.sprite = (QPixmap.fromImage(custom_image).scaled(320, 320,
            Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            if custom_image is not None else self.default_sprite)
        self.import_thread = self.import_worker = None
        self.focus_until = 0
        self.antigravity_until = 0
        self.window_rects = []
        self.last = time.monotonic()
        self.accumulator = 0
        self.menu = None
        self.tray = QSystemTrayIcon(QIcon(self.sprite), app)
        self.tray.setToolTip(APP_NAME + " · 左鍵控制室，右鍵更多")
        self.tray.activated.connect(self.tray_activated)
        self.tray_menu = self.context_menu()
        self.tray.setContextMenu(self.tray_menu)
        self.tray.show()  # Qt also registers it if the tray appears later.
        self.panel = Panel(self)
        self.add_pet()
        self.panel.refresh()
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
        self.app.aboutToQuit.connect(self.finish_import)
        self.app.screenAdded.connect(lambda _: self.rescue())
        self.app.screenRemoved.connect(lambda _: QTimer.singleShot(150, self.rescue))

    def choose_pet_image(self):
        if self.import_thread is not None:
            return
        source, _ = QFileDialog.getOpenFileName(self.panel, "匯入角色圖片", "",
            "Pet images (*.png *.jpg *.jpeg *.PNG *.JPG *.JPEG)")
        if source:
            self.import_image(source)

    def import_image(self, source):
        if self.import_thread is not None:
            self.panel.image_status.setText("正在處理圖片，請稍候。")
            return
        self.panel.import_button.setEnabled(False)
        self.panel.reset_image_button.setEnabled(False)
        self.panel.image_status.setText("正在匯入並處理圖片…桌寵仍可操作。")
        thread = QThread(self.app)
        worker = ImageImportWorker(source, self.data_dir, self.panel.auto_background.isChecked(),
                                   self.panel.background_tolerance.value())
        self.import_thread, self.import_worker = thread, worker
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.completed.connect(self.image_imported)
        worker.failed.connect(self.image_failed)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(self.import_finished)
        thread.finished.connect(thread.deleteLater)
        thread.start()

    @Slot(str)
    def image_failed(self, message):
        self.panel.image_status.setText("匯入失敗：" + message)

    @Slot()
    def import_finished(self):
        self.import_thread = self.import_worker = None
        self.panel.import_button.setEnabled(True)
        self.panel.reset_image_button.setEnabled(True)

    @Slot(object)
    def image_imported(self, result):
        decoded = load_custom_pet_image(self.data_dir)
        image = QPixmap.fromImage(decoded) if decoded is not None else QPixmap()
        if image.isNull():
            self.panel.image_status.setText("匯入後的圖片無法載入，原角色仍保留。")
            return
        self.sprite = image.scaled(320, 320, Qt.AspectRatioMode.KeepAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)
        self.update_image_icons()
        self.panel.image_status.setText("已套用到所有桌寵。" + result.message)
        self.say_all("新造型，出發！")

    def update_image_icons(self):
        icon = QIcon(self.sprite)
        self.tray.setIcon(icon)
        self.panel.setWindowIcon(icon)
        self.panel.refresh_image_preview()
        for toy in self.toys:
            toy.render_frame(0)

    def reset_image(self):
        if self.import_thread is not None:
            return
        try:
            reset_pet_image(self.data_dir)
        except OSError as error:
            self.panel.image_status.setText("無法還原角色：" + str(error))
            return
        self.sprite = self.default_sprite
        self.update_image_icons()
        self.panel.image_status.setText("已還原預設角色。")

    def finish_import(self):
        # Finish bounded image processing before Qt destroys its worker thread.
        if self.import_thread is not None and self.import_thread.isRunning():
            self.import_thread.quit()
            self.import_thread.wait()

    def load(self):
        try:
            data = json.loads((self.data_dir / "settings.json").read_text(encoding="utf-8"))
            raw = data.get("settings", {})
            if type(raw.get("size")) in (int, float) and math.isfinite(raw["size"]):
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

    def set_option(self, key, value):
        self.settings[key] = value
        if key == "windows":
            self.scan_windows()
        self.save()

    def set_size(self, size):
        size = int(clamp(size, 38, 100))
        self.settings["size"] = size
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
        self.notice = ""
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
        screen = self.app.screenAt(QCursor.pos()) or self.app.primaryScreen()
        area = screen.availableGeometry()
        self.panel.setMinimumWidth(min(440, max(240, area.width() - 32)))
        self.panel.resize(min(460, max(240, area.width() - 32)), min(830, max(240, area.height() - 32)))
        self.panel.move(area.left() + max(0, (area.width() - self.panel.width()) // 2),
                        area.top() + max(0, (area.height() - self.panel.height()) // 2))
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
        action("桌寵控制室", self.show_panel)
        action("全員發射！", self.launch_all)
        action("餵甜甜圈", self.feed)
        action("增加桌寵", self.add_pet)
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
        action("退出程式", lambda: self.app.exit(0))
        self.menu = menu  # Keep popup alive beyond mousePressEvent.
        return menu

    def scan_windows(self):
        self.window_rects = desktop_windows() if self.settings["windows"] and not self.paused else []
        self.desktop_notice = ("其他視窗偵測暫時中斷，正在重試；桌寵仍可操作。"
            if sys.platform.startswith("linux") and self.settings["windows"] and not self.paused and X11.failed else "")

    def tick(self):
        now = time.monotonic()
        elapsed = min(.08, now - self.last)
        self.last = now
        if self.focus_until and now >= self.focus_until:
            self.focus_until = 0
            self.stats["focus_sessions"] += 1
            self.mode = "wander"
            self.say_all("完成了！休息一下，喝口水 ♥")
            self.notice = "專注完成！伸展一下，喝口水吧。"
            self.panel.refresh()
            if QSystemTrayIcon.isSystemTrayAvailable() and QSystemTrayIcon.supportsMessages():
                self.tray.showMessage(APP_NAME, self.notice, QSystemTrayIcon.MessageIcon.Information, 6000)
            else:
                self.show_panel()
            self.save()
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
        count = substep_count([toy.body for toy in self.toys], dt, gravity)
        for _ in range(count):
            self._simulate_step(dt / count, now)

    def _simulate_step(self, dt, now):
        gravity = -450 if now < self.antigravity_until else (270 if self.settings["low_gravity"] else 1250)
        cursor = QCursor.pos()
        foods = [t for t in self.toys if t.kind == "food"]
        supports = {}
        for t in self.toys[:]:
            b = t.body
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
                    b.vx *= .92 ** (dt * 120)
                    b.angle = (b.angle + ((-b.angle + 180) % 360 - 180) * dt * 6) % 360
                    b.spin *= .9 ** (dt * 120)
            hits = step(b, self.bounds(b), dt, gravity, .83 if t.kind == "ball" else .69, drive,
                        platforms=self.window_rects if self.settings["windows"] else ())
            for _, speed, _, _ in hits:
                t.impact(speed)
            if b.grounded and not b.held and self.settings["windows"] and gravity > 0:
                for left, top, right, bottom in self.window_rects:
                    if left <= b.x <= right and abs(b.y + b.r - top) < .1:
                        supports[t] = (left, top, right)
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
        for food in consumed:
            self.remove(food)
        # A later pair can displace an earlier contact; iterate the small toy set.
        for iteration in range(3):
            toys = self.toys[:]
            for i, a in enumerate(toys):
                for b in toys[i + 1:]:
                    if {a.kind, b.kind} == {"food", "pet"}:
                        continue
                    speed = collide(a.body, b.body)
                    if iteration == 0 and speed > 120:
                        a.impact(speed)
                        b.impact(speed)
            for toy in toys:
                constrain(toy.body, self.bounds(toy.body))
                support = supports.get(toy)
                if support is not None:
                    left, top, right = support
                    body = toy.body
                    if left <= body.x <= right and body.y + body.r > top:
                        body.y = top - body.r
                        body.vy = min(0, body.vy)
                        body.grounded = body.vy == 0


def migrate_legacy_settings(data_dir, legacy_data_dir):
    """Copy old settings without replacing either an existing setup or the source."""
    target = data_dir / "settings.json"
    source = legacy_data_dir / "settings.json"
    if target.exists() or not source.is_file():
        return
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return
        temp = data_dir / "migration.tmp"
        temp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        temp.replace(target)
    except (OSError, ValueError, TypeError):
        pass


def main():
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--panel", action="store_true", help="show the control room")
    parser.add_argument("--verify-startup-report", help=argparse.SUPPRESS)
    args = parser.parse_args()
    app = QApplication(sys.argv[:1])
    app.setApplicationName(LEGACY_APP_ID)
    app.setOrganizationName(LEGACY_ORGANIZATION)
    legacy_data_dir = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))
    app.setApplicationName(APP_ID)
    app.setApplicationDisplayName(APP_NAME)
    app.setOrganizationName(ORGANIZATION)
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
                          "platform": app.platformName(), "window_rects": club.window_rects,
                          "panel_height": club.panel.height(),
                          "screen_height": app.primaryScreen().availableGeometry().height()}
                STARTUP_REPORT.parent.mkdir(parents=True, exist_ok=True)
                club.panel.grab().save(str(STARTUP_REPORT.with_suffix(".png")))
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
    lock = QLockFile(str(data_dir / "app.lock"))
    lock.setStaleLockTime(0)
    request_path = data_dir / "activate.request"
    if not lock.tryLock(100):
        try:
            request_path.write_text(str(time.time_ns()), encoding="ascii")
        except OSError as error:
            print("Could not reopen the control room: " + str(error), file=sys.stderr)
            return 1
        return 0
    request_path.unlink(missing_ok=True)
    migrate_legacy_settings(data_dir, legacy_data_dir)
    club = Club(app)
    def activate_existing():
        if request_path.exists():
            try:
                request_path.unlink()
            except OSError:
                return
            club.show_panel()
    activation_timer = QTimer(app)
    activation_timer.timeout.connect(activate_existing)
    activation_timer.start(250)
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
