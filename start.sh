#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
# The app-menu shortcut records failures that otherwise disappear with Terminal=false.
if [[ "${1:-}" == --desktop ]]; then
    shift
    state_dir="${XDG_STATE_HOME:-$HOME/.local/state}/WhyTheMouseJumpOntoMyHead67"
    if [[ "$state_dir" != /* ]]; then
        echo 'XDG_STATE_HOME must be an absolute path.' >&2
        exit 1
    fi
    mkdir -p -- "$state_dir"
    exec >>"$state_dir/launcher.log" 2>&1
    printf '\nLaunch %s\n' "$(date -Iseconds)"
fi
case "${1:-}" in
    --help|-h)
        cat <<'HELP'
Desktop pet (Ubuntu / Linux Mint)
  bash start.sh                   Launch offline after setup
  bash start.sh --setup           Install/update source Python dependencies
  bash start.sh --setup-ai        Enable real AI photo background removal
  bash start.sh --install-gnome-bridge  Optional native Wayland window geometry
  bash start.sh --remove-gnome-bridge   Remove optional GNOME bridge
  bash start.sh --doctor          Check actual X11 connection, Qt libraries and Python
  bash start.sh --install-desktop Add this pet to your app menu
  bash start.sh --remove-desktop  Remove the app-menu shortcut (keep settings)
See UBUNTU.md for installation, image import, controls and troubleshooting.
HELP
        exit 0 ;;
    --setup-ai)
        exec bash enable-background-removal.sh ;;
    --doctor|--install-desktop|--remove-desktop|--install-gnome-bridge|--remove-gnome-bridge)
        command -v python3 >/dev/null || { echo 'Install python3 first: sudo apt install python3' >&2; exit 1; }
        exec python3 linux_setup.py "$1" ;;
esac
# New names are read from project metadata; keep old packaged folders launchable.
package_name=Why-the-Mouse-Jump-Onto-My-Head-67
if [[ -f project_info.py ]] && command -v python3 >/dev/null; then
    package_name=$(python3 -c 'from project_info import EXECUTABLE_NAME; print(EXECUTABLE_NAME)')
fi
if [[ -x "./$package_name" ]]; then
    executable=("./$package_name")
elif [[ -x "dist/$package_name/$package_name" ]]; then
    executable=("dist/$package_name/$package_name")
elif [[ -x ./Naiwa ]]; then
    executable=(./Naiwa)
elif [[ -x dist/Naiwa/Naiwa ]]; then
    executable=(dist/Naiwa/Naiwa)
else
    if [[ "${1:-}" == --setup ]]; then
        command -v python3 >/dev/null || { echo 'Install Python: sudo apt install python3 python3-venv' >&2; exit 1; }
        if [[ ! -x .venv/bin/python ]] || ! .venv/bin/python -m pip --version >/dev/null 2>&1; then
            python3 -m venv .venv || { echo 'Install venv support: sudo apt install python3-venv, then rerun --setup.' >&2; exit 1; }
        fi
        exec .venv/bin/python -m pip install --disable-pip-version-check -r requirements.txt
    fi
    if [[ ! -x .venv/bin/python ]] || ! .venv/bin/python -c 'import PySide6.QtWidgets, Xlib' >/dev/null 2>&1; then
        echo 'Source dependencies are missing. Run: bash start.sh --setup' >&2
        exit 1
    fi
    executable=(.venv/bin/python naiwa.py)
fi
if [[ "${1:-}" == --setup ]]; then
    echo 'This packaged download already includes Python and Qt. Run bash start.sh --doctor to check system libraries.'
    exit 0
fi
if [[ -z "${DISPLAY:-}" ]]; then
    echo 'No X11/XWayland display. Open a terminal in your Ubuntu desktop. See UBUNTU.md for XWayland setup.' >&2
    exit 1
fi
case "${QT_QPA_PLATFORM:-xcb}" in
    xcb) ;;
    *) echo 'This pet needs XWayland/xcb for movable pets. Run: QT_QPA_PLATFORM=xcb bash start.sh' >&2; exit 1 ;;
esac
export QT_QPA_PLATFORM=xcb
exec "${executable[@]}" --panel "$@"
