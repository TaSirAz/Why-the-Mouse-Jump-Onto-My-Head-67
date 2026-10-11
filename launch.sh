#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
export XDG_DATA_HOME="$PWD/data"
export QT_QPA_PLATFORM=xcb
exec bash start.sh "$@"
