"""Windows build: Qt must use Windows ICU, never an unrelated ICU from PATH."""
from pathlib import Path

root = Path(SPECPATH).parent
import sys
sys.path.insert(0, str(root))
from project_info import EXECUTABLE_NAME
a = Analysis(
    [str(root / "naiwa.py")],
    pathex=[str(root)],
    binaries=[],
    datas=[(str(root / "assets"), "assets")],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
# Qt 6 on supported Windows versions imports the OS's unversioned ICU exports.
# Poppler/Conda ICU uses versioned exports but the same DLL name. PyInstaller's
# PATH scan can accidentally bundle it. API-set forwarders also belong to the OS.
a.binaries = [entry for entry in a.binaries
              if not Path(entry[0]).name.lower().startswith(
                  ("icu", "api-ms-win-", "ext-ms-win-"))]
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name=EXECUTABLE_NAME, debug=False, bootloader_ignore_signals=False,
    strip=False, upx=False, console=False, disable_windowed_traceback=False,
    icon=str(root / "assets" / "naiwa.ico"),
)

