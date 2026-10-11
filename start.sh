#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ -z "${DISPLAY:-}" ]]; then
    echo 'Naiwa needs an X11/XWayland graphical session. Choose Ubuntu on Xorg or a Mint desktop session.' >&2
    exit 1
fi
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"
if [[ -x ./Naiwa ]]; then
    exec ./Naiwa --panel "$@"
elif [[ -x dist/Naiwa/Naiwa ]]; then
    exec dist/Naiwa/Naiwa --panel "$@"
fi
if [[ ! -x .venv/bin/python ]]; then
    python3 -m venv .venv
fi
.venv/bin/python -m pip install -r requirements.txt
exec .venv/bin/python naiwa.py --panel "$@"
