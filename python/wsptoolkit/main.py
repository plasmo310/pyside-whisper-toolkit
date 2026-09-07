"""Whisper Toolkit (GUI) の起点。

    scripts/win/LaunchApp.bat      (Windows)
    scripts/mac/LaunchApp.sh       (macOS / Linux)

または PYTHONPATH に `python/` を通したうえで

    python -m wsptoolkit.main

で起動する。パッケージ内の API をそのまま呼ぶだけなので、CLI と同じ
`.venv` で動く (PySide6 だけ追加で必要)。
"""

from __future__ import annotations

import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from .gui.main_controller import MainController
from .tool_config import ToolConfig


def main() -> int:
    """メイン処理

    Returns:
        int: プロセスの終了コード。
    """
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(ToolConfig.get_tool_icon_path()))
    app.setStyle("Fusion")
    stylesheet = ToolConfig.load_stylesheet()
    if stylesheet:
        app.setStyleSheet(stylesheet)

    controller = MainController()
    controller.launch()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
