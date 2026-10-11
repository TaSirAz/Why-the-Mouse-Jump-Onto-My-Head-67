#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ ! -x .venv/bin/python ]]; then
    python3 -m venv .venv
fi
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m PyInstaller --noconfirm --workpath build/linux packaging/Naiwa-Linux.spec
readarray -t package_info < <(.venv/bin/python -c 'from project_info import EXECUTABLE_NAME, ARCHIVE_NAME; print(EXECUTABLE_NAME); print(ARCHIVE_NAME)')
package_name="${package_info[0]}"
archive_name="${package_info[1]}"
.venv/bin/python verify_linux.py "dist/$package_name/$package_name"
cp README.md UBUNTU.md LICENSE THIRD_PARTY.md start.sh linux_setup.py project_info.py "dist/$package_name/"
chmod +x "dist/$package_name/start.sh" "dist/$package_name/$package_name"
tar -C dist -czf "dist/$archive_name" "$package_name"
echo "Ready: dist/$archive_name"

