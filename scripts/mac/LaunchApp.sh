#!/bin/bash
# Whisper Toolkit (GUI) launcher.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

PYTHON_EXE="$ROOT_DIR/.venv/bin/python"
if [ ! -f "$PYTHON_EXE" ]; then
    echo "Not found python env. Please execute './scripts/mac/setup_venv.sh'."
    exit 1
fi

export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$ROOT_DIR/python"

"$PYTHON_EXE" -m wsptoolkit.main
