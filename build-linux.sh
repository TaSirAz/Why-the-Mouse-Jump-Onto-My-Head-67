#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ ! -x .venv/bin/python ]]; then
    python3 -m venv .venv
fi
.venv/bin/python -m pip install -r requirements-dev.txt
if [[ "${1:-}" == --with-ai ]]; then
    bash enable-background-removal.sh
elif [[ -n "${1:-}" ]]; then
    echo "Usage: bash build-linux.sh [--with-ai]" >&2
    exit 1
fi
.venv/bin/python -m PyInstaller --noconfirm --workpath build/linux packaging/Naiwa-Linux.spec
readarray -t package_info < <(.venv/bin/python -c 'from project_info import EXECUTABLE_NAME, ARCHIVE_NAME; print(EXECUTABLE_NAME); print(ARCHIVE_NAME)')
package_name="${package_info[0]}"
archive_name="${package_info[1]}"
.venv/bin/python verify_linux.py "dist/$package_name/$package_name"
cp README.md UBUNTU.md LICENSE THIRD_PARTY.md start.sh linux_setup.py linux_desktop.py project_info.py enable-background-removal.sh requirements-background.txt "dist/$package_name/"
cp -R gnome-extension "dist/$package_name/"
chmod +x "dist/$package_name/start.sh" "dist/$package_name/$package_name"
tar -C dist -czf "dist/$archive_name" "$package_name"
echo "Ready: dist/$archive_name"

