#!/bin/bash
# Build Whisper Toolkit into build_env/scripts/mac/dist.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_ENV_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
ROOT_DIR="$(cd "$BUILD_ENV_DIR/.." && pwd)"

VENV_DIR="$BUILD_ENV_DIR/.venv"
PYTHON_EXE="$VENV_DIR/bin/python"
if [ ! -f "$PYTHON_EXE" ]; then
    echo "Not found python env. Please execute 'build_env/scripts/mac/Setup.sh'."
    exit 1
fi

export PYTHONDONTWRITEBYTECODE=1
PYTHON_SRC_DIR="$ROOT_DIR/python"
RESOURCES_DIR="$ROOT_DIR/resources"

source "$VENV_DIR/bin/activate"
cd "$BUILD_ENV_DIR" || exit 1

BUILD_TMP_DIR="$SCRIPT_DIR/build"
BUILD_DIST_DIR="$SCRIPT_DIR/dist"

EXE_NAME="WhisperToolkit"
ICON_PATH="$RESOURCES_DIR/icon/tool_icon_round.icns"

# References: https://pyinstaller.org/en/stable/usage.html
pyinstaller --noconsole --onedir --name "$EXE_NAME"     --paths "$PYTHON_SRC_DIR"     --hidden-import "PySide6"     --collect-all "faster_whisper"     --collect-all "ctranslate2"     --collect-all "onnxruntime"     --add-data "$RESOURCES_DIR:./resources"     --icon "$ICON_PATH"     --distpath "$BUILD_DIST_DIR" --workpath "$BUILD_TMP_DIR"     "$BUILD_ENV_DIR/python/run.py"

# Clean up
rm -rf "$BUILD_TMP_DIR"
find "$PYTHON_SRC_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

echo "Complete build app."
