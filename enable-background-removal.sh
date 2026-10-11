#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ ! -f naiwa.py ]]; then
    echo "This binary package does not contain source setup. Use an AI-enabled package or install updated source and run --setup, then --setup-ai." >&2
    exit 1
fi
if [[ ! -x .venv/bin/python ]]; then
    echo 'Source setup is required first: bash start.sh --setup' >&2
    exit 1
fi
if [[ ! -f requirements-background.txt ]]; then
    echo 'AI requirements are missing. Use the updated source folder.' >&2
    exit 1
fi
.venv/bin/python -m pip install --disable-pip-version-check --cache-dir work/pip-cache -r requirements-background.txt
.venv/bin/python pet_images.py --download-model --model-dir models
echo 'AI photo background removal is ready. Restart the application before importing a photo.'
