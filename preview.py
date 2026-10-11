"""Render the real UI and physics animation onto a clean demonstration desktop."""
from pathlib import Path
import tempfile
import time
from PySide6.QtCore import QPoint, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen
from PySide6.QtWidgets import QApplication
from naiwa import Club


def main():
    app = QApplication([])
    app.setApplicationName("NaiwaPreview")
    app.setQuitOnLastWindowClosed(False)
    output = Path("verification")
    output.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as data:
        club = Club(app, data)
        for timer in [club.timer, club.window_timer, club.save_timer]:
            timer.stop()
        club.add_pet()
        club.add_ball()
        club.panel.show()
        app.processEvents()
        club.panel.grab().save(str(output / "control-room.png"))
        club.panel.hide()
        club.settings["windows"] = True
        club.window_rects = [(170, 355, 670, 530)]
        club.bounds = lambda body: (0, 0, 1040, 650)
        for i, toy in enumerate(club.toys):
            toy.body.x, toy.body.y = 260 + i * 130, 160
            toy.body.vx = 370 if i % 2 == 0 else -300
            toy.body.vy = -100
            toy.body.spin = 460
            toy.bubble_until = 0
        for frame in range(150):
            now = time.monotonic()
            for _ in range(4):
                club.simulate(1 / 120, now)
            image = QImage(1040, 650, QImage.Format.Format_RGB32)
            image.fill(QColor("#102031"))
            p = QPainter(image)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setPen(QColor("#fbe077"))
            p.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
            p.drawText(38, 56, "NAIWA ROLL CLUB")
            p.setPen(QColor("#b8c9d6"))
            p.setFont(QFont("Microsoft JhengHei", 12))
            p.drawText(40, 88, "翻滾  /  拋擲  /  互撞  /  視窗頂端落地")
            p.setBrush(QColor("#1f3449"))
            p.setPen(QPen(QColor("#446077"), 1))
            p.drawRoundedRect(QRectF(170, 355, 500, 175), 15, 15)
            p.setPen(QColor("#91b6cf"))
            p.setFont(QFont("Microsoft JhengHei", 11))
            p.drawText(190, 390, "示範視窗 · Naiwa 可以滾過頂端")
            p.setPen(QPen(QColor("#688491"), 2))
            p.drawLine(0, 649, 1040, 649)
            for toy in club.toys:
                toy.render_frame(1 / 30)
                p.drawImage(round(toy.body.x - toy.cx), round(toy.body.y - toy.cy), toy.buffer)
            p.end()
            image.save(str(output / f"frame-{frame:03}.png"))
        for toy in club.toys:
            toy.hide()
        club.tray.hide()
    print("Rendered control room and 150 physics frames to verification/")


if __name__ == "__main__":
    main()
