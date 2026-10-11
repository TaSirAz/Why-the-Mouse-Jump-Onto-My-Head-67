"""Linux x86_64 directory bundle; include Qt's own Linux ICU libraries."""
from pathlib import Path
import sys
from PyInstaller.utils.hooks import collect_submodules

root = Path(SPECPATH).parent
sys.path.insert(0, str(root))
from project_info import EXECUTABLE_NAME
a = Analysis(
    [str(root / "naiwa.py")], pathex=[str(root)], binaries=[],
    datas=[(str(root / "assets"), "assets")],
    hiddenimports=collect_submodules("Xlib"),
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[],
    noarchive=False, optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name=EXECUTABLE_NAME,
          debug=False, bootloader_ignore_signals=False, strip=False,
          upx=False, console=True)
collect = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name=EXECUTABLE_NAME)

