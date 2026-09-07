"""ツールの設定と、resources/ の場所の解決。

画面に並べる選択肢は `definitions.py` に置いてあるので、ここには
ツール自体の見た目・保存先・リソースのパスだけを置く。
"""

from __future__ import annotations

import os
import sys

from wsptoolkit.lib.settings import IS_WINDOWS

# スタイルシートの中で resources/ の絶対パスに置き換えるプレースホルダ
_RESOURCES_DIR_PLACEHOLDER = "{RESOURCES_DIR}"


class ToolConfig:
    """ツール設定クラス"""

    # ツールタイトル
    TOOL_TITLE = "Whisper Toolkit"

    # ウィンドウの既定サイズ
    WINDOW_WIDTH = 1000
    WINDOW_HEIGHT = 880

    # 入力行の高さ (全部揃えて縦位置をきれいに出す)
    ROW_HEIGHT = 28

    # Cancel / Run ボタンの幅
    # 高さはタブと揃えるため stylesheet.qss 側で指定している
    CANCEL_BUTTON_WIDTH = 110

    # 入力行の左に置くラベルの幅 (タブ間で揃える)
    LABEL_WIDTH = 150

    # QSettings の識別子
    SETTINGS_ORGANIZATION = "WhisperToolkit"
    SETTINGS_APPLICATION = "WhisperToolkit"

    # 音声ファイル選択ダイアログのフィルタ
    AUDIO_FILE_FILTER = (
        "Audio / Video (*.wav *.mp3 *.m4a *.flac *.ogg *.mp4 *.mov);;"
        "All Files (*)"
    )

    # 歌詞ファイル選択ダイアログのフィルタ
    LYRICS_FILE_FILTER = "Text (*.txt);;All Files (*)"

    @staticmethod
    def __get_resources_dir() -> str:
        """resources/ の絶対パスを返す。

        PyInstaller で固めた場合は `_internal/resources/` を見る。
        参考: https://pyinstaller.org/en/stable/runtime-information.html
        """
        if hasattr(sys, "_MEIPASS"):
            return os.path.join(sys._MEIPASS, "resources")
        return os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "resources")
        )

    @staticmethod
    def get_tool_icon_path() -> str:
        """ツールアイコンのパス (プラットフォーム別)

        Windows は角のある .ico、macOS は丸い .icns を使う。
        どちらも resources/icon/icon_base.png から作ってある。
        """
        file_name = (
            "tool_icon_rect.ico" if IS_WINDOWS else "tool_icon_round.icns"
        )
        return os.path.join(
            ToolConfig.__get_resources_dir(), "icon", file_name
        )

    @staticmethod
    def load_stylesheet() -> str:
        """スタイルシートを読み込む。

        QSS の `url()` は実行時のカレントディレクトリ基準で解決されて
        しまうので、`{RESOURCES_DIR}` を resources/ の絶対パスに
        置き換えてから返す。区切りは QSS が解釈できるスラッシュにする。

        Returns:
            str: スタイルシートの中身。読めなければ空文字。
        """
        resources_dir = ToolConfig.__get_resources_dir()
        stylesheet_path = os.path.join(resources_dir, "ui", "stylesheet.qss")
        if not os.path.isfile(stylesheet_path):
            return ""

        try:
            with open(stylesheet_path, encoding="utf-8") as file:
                stylesheet = file.read()
        except UnicodeDecodeError:
            with open(stylesheet_path, encoding="utf-8-sig") as file:
                stylesheet = file.read()

        return stylesheet.replace(
            _RESOURCES_DIR_PLACEHOLDER, resources_dir.replace("\\", "/")
        )
