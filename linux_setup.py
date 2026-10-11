"""Ubuntu diagnostics and user-only application menu registration (stdlib only)."""
import argparse
import ctypes
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from project_info import APP_NAME, APP_ID, EXECUTABLE_NAME

ROOT = Path(__file__).resolve().parent
LIBRARIES = {
    'libEGL.so.1': 'libegl1', 'libGL.so.1': 'libgl1',
    'libdbus-1.so.3': 'libdbus-1-3', 'libfontconfig.so.1': 'libfontconfig1',
    'libX11-xcb.so.1': 'libx11-xcb1', 'libxkbcommon-x11.so.0': 'libxkbcommon-x11-0',
    'libxcb-cursor.so.0': 'libxcb-cursor0', 'libxcb-icccm.so.4': 'libxcb-icccm4',
    'libxcb-image.so.0': 'libxcb-image0', 'libxcb-keysyms.so.1': 'libxcb-keysyms1',
    'libxcb-render-util.so.0': 'libxcb-render-util0', 'libxcb-xinerama.so.0': 'libxcb-xinerama0',
    'libxcb-xfixes.so.0': 'libxcb-xfixes0', 'libxcb-shape.so.0': 'libxcb-shape0',
    'libxcb-xinput.so.0': 'libxcb-xinput0',
}


def desktop_value(value):
    """Escape a Desktop Entry string value; no shell is involved."""
    return str(value).replace('\\', '\\\\').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')


def exec_argument(value):
    # Exec quoting is parsed after Desktop Entry string unescaping.
    value = str(value).replace('%', '%%')
    for char in ('\\', '"', '`', '$'):
        value = value.replace(char, '\\' + char)
    return desktop_value('"' + value + '"')


def desktop_entry(root):
    icon = root / 'assets/naiwa.png'
    if not icon.exists():
        icon = root / '_internal/assets/naiwa.png'
    return (f'[Desktop Entry]\nType=Application\nName={desktop_value(APP_NAME)}\n'
            'Comment=Play with your desktop companion\n'
            f'Exec=/bin/bash {exec_argument(root / "start.sh")} --desktop\n'
            f'Icon={desktop_value(icon)}\nTerminal=false\nCategories=Game;\n'
            'StartupNotify=false\n')


def shortcut_path():
    data = Path(os.environ.get('XDG_DATA_HOME') or Path.home() / '.local/share')
    if not data.is_absolute():
        raise ValueError('XDG_DATA_HOME must be an absolute path.')
    return data / 'applications' / (APP_ID + '.desktop')


def doctor():
    print(f'System: {platform.system()} {platform.machine()}')
    print('Session:', os.environ.get('XDG_SESSION_TYPE', 'unknown'))
    print('DISPLAY:', os.environ.get('DISPLAY', '(missing)'))
    missing = []
    for library, package in LIBRARIES.items():
        try:
            ctypes.CDLL(library)
        except OSError:
            missing.append(package)
    if missing:
        print('Missing graphics libraries. Install with:\nsudo apt install ' + ' '.join(missing))
    else:
        print('Graphics libraries: OK')
    if os.environ.get('WAYLAND_DISPLAY'):
        print('Wayland: pet movement uses XWayland; native Wayland windows cannot be collision platforms.')
    display_ok = False
    if not os.environ.get('DISPLAY'):
        print('Open a terminal inside the graphical desktop. See UBUNTU.md for XWayland instructions.')
    else:
        try:
            x11 = ctypes.CDLL('libX11.so.6')
            x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
            x11.XOpenDisplay.restype = ctypes.c_void_p
            x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
            connection = x11.XOpenDisplay(None)
            display_ok = bool(connection)
            if connection:
                x11.XCloseDisplay(connection)
            print('X11 connection: OK' if display_ok else 'X11 connection failed: open a terminal in the logged-in desktop; check XAUTHORITY and DISPLAY.')
        except OSError as error:
            print('X11 connection unavailable:', error)
    backend = os.environ.get('QT_QPA_PLATFORM', 'xcb')
    backend_ok = backend == 'xcb'
    if not backend_ok:
        print(f'Qt backend {backend!r} cannot run movable pets. Run: QT_QPA_PLATFORM=xcb bash start.sh')
    if shutil.which('fc-match'):
        result = subprocess.run(['fc-match', '-f', '%{family}', 'Noto Sans CJK TC'], capture_output=True, text=True)
        print('Chinese font:', result.stdout or '(not found)')
        if 'CJK' not in result.stdout:
            print('For readable Chinese labels: sudo apt install fonts-noto-cjk')
    bundled = any(path.is_file() for path in (ROOT / EXECUTABLE_NAME, ROOT / ('dist/' + EXECUTABLE_NAME) / EXECUTABLE_NAME, ROOT / 'Naiwa', ROOT / 'dist/Naiwa/Naiwa'))
    deps_ok = bundled
    if bundled:
        print('Runtime: packaged (no pip setup needed)')
    else:
        python = ROOT / '.venv/bin/python'
        result = None
        try:
            result = subprocess.run([str(python), '-c', 'import PySide6.QtWidgets, Xlib; print("Python dependencies: OK")'], capture_output=True, text=True)
            deps_ok = result.returncode == 0
        except OSError:
            deps_ok = False
        print('Python dependencies: OK' if deps_ok else 'Run: bash start.sh --setup')
        if not deps_ok and result is not None and result.stderr:
            print(result.stderr.strip().splitlines()[-1])
    print('Guide:', ROOT / 'UBUNTU.md')
    return int(bool(missing) or not display_ok or not backend_ok or not deps_ok)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    for option in ('doctor', 'install-desktop', 'remove-desktop'):
        group.add_argument('--' + option, action='store_true')
    args = parser.parse_args()
    if args.doctor:
        return doctor()
    target = shortcut_path()
    if args.remove_desktop:
        target.unlink(missing_ok=True)
        print('Removed app-menu shortcut. Application files and settings were kept.')
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(desktop_entry(ROOT), encoding='utf-8')
        print('Installed:', target)
        print(f'Open the app menu and search for {APP_NAME}. Keep this application folder in place.')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        raise SystemExit(str(error))
