"""Ubuntu diagnostics and user-only application menu registration (stdlib only)."""
import argparse
import ctypes
import os
import ast
import re
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from project_info import APP_NAME, APP_ID, ORGANIZATION, EXECUTABLE_NAME
from linux_desktop import GNOME_BRIDGE_NAME, GNOME_BRIDGE_PATH, GNOME_BRIDGE_UUID

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
    data = Path(os.environ.get('DESKTOP_PETS_DESKTOP_DATA_HOME') or
                os.environ.get('XDG_DATA_HOME') or Path.home() / '.local/share')
    if not data.is_absolute():
        raise ValueError('XDG_DATA_HOME must be an absolute path.')
    return data / 'applications' / (APP_ID + '.desktop')



def extension_path():
    data = Path(os.environ.get('DESKTOP_PETS_DESKTOP_DATA_HOME') or
                os.environ.get('XDG_DATA_HOME') or Path.home() / '.local/share')
    if not data.is_absolute():
        raise ValueError('XDG_DATA_HOME must be an absolute path.')
    return data / 'gnome-shell/extensions' / GNOME_BRIDGE_UUID


def install_gnome_bridge(remove=False):
    target = extension_path()
    if target.is_symlink():
        raise ValueError('Refusing to overwrite a symlinked extension directory.')
    if remove:
        if shutil.which('gnome-extensions'):
            subprocess.run(['gnome-extensions', 'disable', GNOME_BRIDGE_UUID],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        for name in ('extension.js', 'metadata.json'):
            (target / name).unlink(missing_ok=True)
        if target.exists() and not any(target.iterdir()):
            target.rmdir()
        print('Removed the optional GNOME geometry bridge. X11 fallback remains available.')
        return 0
    if not shutil.which('gnome-shell'):
        raise ValueError('This optional bridge requires GNOME Shell 45–50; use X11 on other desktops.')
    version = subprocess.run(['gnome-shell', '--version'], capture_output=True, text=True, timeout=5)
    match = re.search(r'(\d+)\.', version.stdout)
    if not match or not 45 <= int(match.group(1)) <= 50:
        raise ValueError('The supplied bridge targets GNOME Shell 45–50. No extension was installed.')
    source = ROOT / 'gnome-extension' / GNOME_BRIDGE_UUID
    if not (source / 'extension.js').is_file():
        raise ValueError('Bridge source files are missing. Use the updated source/package.')
    target.mkdir(parents=True, exist_ok=True)
    for name in ('extension.js', 'metadata.json'):
        destination = target / name
        if destination.is_symlink():
            raise ValueError('Refusing to overwrite a symlinked extension file.')
        shutil.copyfile(source / name, destination)
    print('Installed read-only GNOME geometry bridge:', target)
    print('It exports window IDs, PIDs and rectangles; no titles, contents or window-control methods.')
    if shutil.which('gnome-extensions'):
        result = subprocess.run(['gnome-extensions', 'enable', GNOME_BRIDGE_UUID],
                                capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            if bridge_diagnostic():
                print('Enabled and connected. The running pet reconnects automatically within five seconds.')
                return 0
            print('GNOME accepted enable, but the bridge has not connected. Check extension errors:')
            print('gnome-extensions info ' + GNOME_BRIDGE_UUID)
            return 1
    print('GNOME needs a session reload to discover a new extension: save work, log out and log in.')
    print('Then run: gnome-extensions enable ' + GNOME_BRIDGE_UUID)
    print('Run bash start.sh --doctor to confirm the bridge is connected; the pet reconnects automatically.')
    return 0


def bridge_diagnostic():
    if not shutil.which('gdbus'):
        print('GNOME bridge: install libglib2.0-bin for command-line diagnostics, or use the app status.')
        return False
    try:
        result = subprocess.run(['gdbus', 'call', '--session', '--dest', GNOME_BRIDGE_NAME,
            '--object-path', GNOME_BRIDGE_PATH, '--method', GNOME_BRIDGE_NAME + '.GetWindows',
            str(os.getpid()), '[]'], capture_output=True, text=True, timeout=2)
        if result.returncode:
            print('GNOME bridge: unavailable; native Wayland windows are not detected. Optional setup: bash start.sh --install-gnome-bridge')
            return False
        payload = ast.literal_eval(result.stdout)[0]
        from linux_desktop import parse_gnome_snapshot
        records = parse_gnome_snapshot(payload, os.getpid())
        print(f'GNOME bridge: connected ({len(records)} active-workspace windows, including Wayland clients)')
        return True
    except (OSError, ValueError, SyntaxError, subprocess.TimeoutExpired) as error:
        print('GNOME bridge diagnostic failed:', error)
        return False

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
        print('Wayland: pet positioning still uses XWayland; native window geometry requires the optional GNOME bridge.')
        if 'GNOME' in os.environ.get('XDG_CURRENT_DESKTOP', '').upper():
            bridge_diagnostic()
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
    data_dir = Path(os.environ.get('XDG_DATA_HOME') or Path.home() / '.local/share') / ORGANIZATION / APP_ID
    if bundled:
        model_paths = (ROOT / '_internal/models/u2netp.onnx', ROOT / 'models/u2netp.onnx',
                       ROOT / 'dist' / EXECUTABLE_NAME / '_internal/models/u2netp.onnx')
        print('AI model: bundled' if any(path.is_file() for path in model_paths) else
              'AI model not bundled. Use an AI-enabled package or source --setup-ai.')
    elif deps_ok:
        check = subprocess.run([str(python), '-c',
            'import sys; from pet_images import background_removal_status; '
            'print(background_removal_status(sys.argv[1])[1])', str(data_dir)],
            cwd=ROOT, capture_output=True, text=True)
        print('AI background removal:', check.stdout.strip() or (check.stderr.strip().splitlines()[-1] if check.stderr.strip() else 'check unavailable'))
    print('Guide:', ROOT / 'UBUNTU.md')
    return int(bool(missing) or not display_ok or not backend_ok or not deps_ok)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    for option in ('doctor', 'install-desktop', 'remove-desktop', 'install-gnome-bridge', 'remove-gnome-bridge'):
        group.add_argument('--' + option, action='store_true')
    args = parser.parse_args()
    if args.doctor:
        return doctor()
    if args.install_gnome_bridge or args.remove_gnome_bridge:
        return install_gnome_bridge(args.remove_gnome_bridge)
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
