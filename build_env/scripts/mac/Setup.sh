#!/bin/bash
# Create the build venv (app dependencies + PyInstaller).

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_ENV_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV_DIR="$BUILD_ENV_DIR/.venv"

PYVER=3.13

PYTHON_CMD=""
for candidate in "python$PYVER" python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
        if "$candidate" -c "import sys; sys.exit(0 if sys.version_info[:2] == tuple(int(x) for x in '$PYVER'.split('.')) else 1)"; then
            PYTHON_CMD="$candidate"
            break
        fi
    fi
done
if [ -z "$PYTHON_CMD" ]; then
    echo "Python $PYVER not found. Please install Python $PYVER."
    exit 1
fi

"$PYTHON_CMD" -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip
pip install -r "$BUILD_ENV_DIR/requirements.txt"

echo "Complete setup build env."
