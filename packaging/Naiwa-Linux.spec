"""Linux x86_64 directory bundle; include Qt's own Linux ICU libraries."""
from pathlib import Path
import sys
import importlib.util
from PyInstaller.utils.hooks import collect_submodules, collect_dynamic_libs

root = Path(SPECPATH).parent
sys.path.insert(0, str(root))
from project_info import EXECUTABLE_NAME
model_datas = [(str(path), "models") for path in (root / "models").glob("*.onnx")]
optional_hidden = []
optional_binaries = []
if importlib.util.find_spec("onnxruntime") is not None:
    optional_hidden = collect_submodules("onnxruntime")
    optional_binaries = collect_dynamic_libs("onnxruntime")
a = Analysis(
    [str(root / "naiwa.py")], pathex=[str(root)], binaries=optional_binaries,
    datas=[(str(root / "assets"), "assets"), (str(root / "licenses"), "licenses")] + model_datas,
    hiddenimports=collect_submodules("Xlib") + ["PySide6.QtDBus"] + optional_hidden,
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[],
    noarchive=False, optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name=EXECUTABLE_NAME,
          debug=False, bootloader_ignore_signals=False, strip=False,
          upx=False, console=True)
collect = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name=EXECUTABLE_NAME)

