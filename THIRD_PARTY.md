# 來源與套件

- `assets/naiwa.png`：使用者提供的 `naiwa.png`，以 OpenAI imagegen 產生透明去背版本；原檔保留在原位置。不是動畫素材包，翻滾、壓扁回彈、粒子及互動由程式即時繪製。
- Naiwa 外觀、衣服標記、旗幟及校名等不包含在程式碼的 MIT 授權中。
- PySide6 / Qt：LGPLv3 / GPLv3 / commercial。官方授權：[Qt for Python licensing](https://doc.qt.io/qtforpython-6/licenses.html)。打包保留套件授權檔。可修改來源並用 `build.ps1` 重新打包替換 Qt；另可直接從 Python 原始碼執行。
- PyInstaller：GPL-2.0-or-later with bootloader exception，允許分發產生的執行檔。[官方授權](https://pyinstaller.org/en/stable/license.html)。

網路查找參考了以下概念；本專案物理、UI 與互動程式碼自行撰寫，沒有搬用其程式碼或素材：

- [desktop-pet-kirby](https://github.com/90shree/desktop-pet-kirby)：拖曳取樣速度、拋擲、重力與反彈互動。
- [QWidget 官方文件](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QWidget.html)：透明、無框、置頂視窗及遮罩。
- [QScreen 官方文件](https://doc.qt.io/qtforpython-6/PySide6/QtGui/QScreen.html)：螢幕工作區域。
- [QSystemTrayIcon 官方文件](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QSystemTrayIcon.html)：托盤與通知。
