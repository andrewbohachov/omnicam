#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
VENV="$DIR/venv"

# Create venv if missing
if [ ! -d "$VENV" ]; then
    echo "[*] Creating virtualenv..."
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install -q --upgrade pip
    "$VENV/bin/pip" install -q -r "$DIR/requirements.txt"
fi

export PYTHONPATH="$DIR:$PYTHONPATH"
exec "$VENV/bin/python" -m aircam.cli "$@"
