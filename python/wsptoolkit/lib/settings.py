"""実行環境まわり: OS 差分・例外・ロガー。

Whisper とも歌詞処理とも無関係な、プロジェクト全体の土台。

Attributes:
    IS_WINDOWS (bool): Windows で動いているか。
    ACTIVATE_HINT (str): 仮想環境を有効化するコマンド (OS 別)。
    SETUP_SCRIPT (str): セットアップスクリプトのパス (OS 別)。
    ROOT_LOGGER_NAME (str): このサンプルのロガー名前空間の根。
"""

from __future__ import annotations

import logging
import os

# OS ごとに案内する手順が違うのでここで一度だけ振り分ける
IS_WINDOWS = os.name == "nt"
ACTIVATE_HINT = (
    ".venv\\Scripts\\activate" if IS_WINDOWS else "source .venv/bin/activate"
)
SETUP_SCRIPT = (
    "scripts\\win\\setup_venv.bat"
    if IS_WINDOWS
    else "scripts/mac/setup_venv.sh"
)

# ルートロガーではなくこの名前空間を使う。ルートにハンドラを付けると
# faster-whisper 自身のログまで拾ってしまい、出力が変わってしまうため。
ROOT_LOGGER_NAME = "whisper_sample"


class WhisperSampleError(Exception):
    """このサンプル由来のエラー。

    ライブラリ側は `sys.exit()` せずにこれを投げ、終了コードの決定と
    画面表示は呼び出し側 (CLI / GUI) に任せる。こうしておくと GUI から
    呼んだときにプロセスが落ちず、メッセージをダイアログに出せる。
    """


def get_logger(name: str) -> logging.Logger:
    """`whisper_sample.<name>` のロガーを返す。`__name__` を渡す。"""
    return logging.getLogger(f"{ROOT_LOGGER_NAME}.{name}")
