#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ ! -x .venv/bin/python ]]; then
    python3 -m venv .venv
fi
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m PyInstaller --noconfirm --workpath build/linux packaging/Naiwa-Linux.spec
.venv/bin/python verify_linux.py dist/Naiwa/Naiwa
cp README.md LICENSE THIRD_PARTY.md start.sh dist/Naiwa/
chmod +x dist/Naiwa/start.sh dist/Naiwa/Naiwa
tar -C dist -czf dist/Naiwa-Linux-x64.tar.gz Naiwa
echo 'Ready: dist/Naiwa-Linux-x64.tar.gz'
