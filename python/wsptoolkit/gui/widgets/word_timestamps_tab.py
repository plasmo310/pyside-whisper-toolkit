"""サンプル② 単語単位の時間 + ③ 歌詞との突き合わせのタブ。

`wsptoolkit.cli.word_timestamps` の設定に加えて、続けて
`wsptoolkit.cli.sync_lyrics` 相当の処理を走らせる Lyrics Sync を持つ。
Run を押すと入力内容を `WordTimestampsRequest` に詰めて emit するだけで、
推論と照合そのものは Controller / Model の担当。

画面にはよく使うものだけを置き、細かい調整 (デコードの調整フラグや
LRC のタグまわり) は CLI 側に任せる。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from PySide6 import QtCore, QtWidgets
from wsptoolkit.gui.widgets.option_rows import (
    DirPathRow,
    FilePathRow,
    FormatsRow,
    WhisperOptionsGroup,
    build_form_scroll_area,
    build_group,
    build_labeled_row,
)
from wsptoolkit.lib.data import LyricsDocument, WordTimingsResult
from wsptoolkit.lib.lyrics import SyncOptions
from wsptoolkit.lib.paths import AUDIO_DIR, LYRICS_DIR, OUTPUT_DIR
from wsptoolkit.lib.whisper import WhisperConfig
from wsptoolkit.tool_config import ToolConfig

# 初期状態でチェックしておく書き出し形式 (CLI の既定と同じ)
_DEFAULT_FORMATS = ("json", "csv")
_DEFAULT_LYRICS_FORMATS = ("json", "lrc")

# 既定値は lib 側の dataclass を唯一の出どころにする
_DEFAULT_SYNC = SyncOptions()


@dataclass
class LyricsSyncRequest:
    """歌詞との突き合わせの実行内容。

    Attributes:
        lyrics_path: 正解の歌詞テキストのパス。
        formats: 書き出す形式名。空なら書き出さない。
        options: 貼り直しの設定。
    """

    lyrics_path: str
    formats: list[str] = field(default_factory=list)
    options: SyncOptions = field(default_factory=SyncOptions)


@dataclass
class WordTimestampsRequest:
    """単語単位のタイムスタンプ取得の実行内容。

    Attributes:
        audio_path: 入力音声/動画のパス。
        output_dir: 書き出し先ディレクトリ。
        formats: 書き出す形式名。空なら書き出さない。
        config: 推論の設定。
        lyrics: 続けて実行する歌詞照合。None なら実行しない。
    """

    audio_path: str
    output_dir: str
    formats: list[str] = field(default_factory=list)
    config: WhisperConfig = field(default_factory=WhisperConfig)
    lyrics: LyricsSyncRequest | None = None


class WordTimestampsTab(QtWidgets.QWidget):
    """単語単位の時間タブ"""

    on_click_run_signal = QtCore.Signal(object)
    on_click_cancel_signal = QtCore.Signal()

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        """タブを組み立てる。

        Args:
            parent: 親ウィジェット。
        """
        super().__init__(parent)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.__build_form(), 1)
        layout.addWidget(self.__build_buttons())

    def __build_form(self) -> QtWidgets.QWidget:
        """入力欄をまとめたスクロール領域を作る。"""
        content = QtWidgets.QWidget()
        content.setProperty("class", "FormArea")
        layout = QtWidgets.QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        self.__input_row = FilePathRow(
            "Input Audio", AUDIO_DIR, ToolConfig.AUDIO_FILE_FILTER
        )

        self.__output_row = DirPathRow("Output Dir", OUTPUT_DIR)
        self.__output_row.set_path(OUTPUT_DIR)

        self.__formats_row = FormatsRow(
            "Output Formats", WordTimingsResult.FORMATS, _DEFAULT_FORMATS
        )

        layout.addWidget(
            build_group(
                "Input / Output",
                self.__input_row,
                self.__output_row,
                self.__formats_row,
            )
        )

        self.__whisper_options = WhisperOptionsGroup()
        layout.addWidget(self.__whisper_options)
        layout.addWidget(self.__build_lyrics_group())
        layout.addStretch()

        return build_form_scroll_area(content)

    def __build_lyrics_group(self) -> QtWidgets.QWidget:
        """歌詞との突き合わせ (Lyrics Sync) の設定を作る。"""
        self.__lyrics_group = QtWidgets.QGroupBox()
        self.__lyrics_group.setProperty("class", "LyricsGroup")
        lyrics_tooltip = (
            "Replace recognized words with the supplied lyrics while "
            "preserving timestamps, then write an LRC file"
        )
        self.__lyrics_group.setToolTip(lyrics_tooltip)
        layout = QtWidgets.QVBoxLayout(self.__lyrics_group)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.__lyrics_check = QtWidgets.QCheckBox("Lyrics Sync")
        self.__lyrics_check.setProperty("class", "GroupHeader")
        self.__lyrics_check.setChecked(False)
        self.__lyrics_check.setToolTip(lyrics_tooltip)
        layout.addWidget(
            self.__lyrics_check,
            0,
            QtCore.Qt.AlignmentFlag.AlignVCenter,
        )

        self.__lyrics_content = QtWidgets.QWidget()
        lyrics_layout = QtWidgets.QVBoxLayout(self.__lyrics_content)
        lyrics_layout.setContentsMargins(0, 0, 0, 0)
        lyrics_layout.setSpacing(8)

        self.__lyrics_row = FilePathRow(
            "Lyrics File", LYRICS_DIR, ToolConfig.LYRICS_FILE_FILTER
        )
        lyrics_layout.addWidget(self.__lyrics_row)

        self.__lyrics_formats_row = FormatsRow(
            "Lyrics Formats",
            LyricsDocument.FORMATS,
            _DEFAULT_LYRICS_FORMATS,
        )
        lyrics_layout.addWidget(self.__lyrics_formats_row)

        self.__offset_spin = QtWidgets.QDoubleSpinBox()
        self.__offset_spin.setRange(-30.0, 30.0)
        self.__offset_spin.setSingleStep(0.1)
        self.__offset_spin.setValue(_DEFAULT_SYNC.offset)
        self.__offset_spin.setSuffix(" sec")
        self.__offset_spin.setToolTip(
            "Seconds added to all timestamps; use a negative value "
            "to show lyrics earlier"
        )
        lyrics_layout.addWidget(
            build_labeled_row("Offset", self.__offset_spin, stretch_last=False)
        )

        self.__keep_blank_check = QtWidgets.QCheckBox(
            "keep blank lines (hides lyrics during interludes)"
        )
        self.__keep_blank_check.setChecked(_DEFAULT_SYNC.keep_blank)
        self.__keep_blank_check.setToolTip(
            "Enable this when VAD Filter is turned off"
        )
        lyrics_layout.addWidget(
            build_labeled_row(
                "Keep Blank", self.__keep_blank_check, stretch_last=False
            )
        )

        layout.addWidget(self.__lyrics_content)
        self.__lyrics_content.setEnabled(False)
        self.__lyrics_check.toggled.connect(self.__lyrics_content.setEnabled)

        return self.__lyrics_group

    def __build_buttons(self) -> QtWidgets.QWidget:
        """Run / Cancel ボタンの行を作る。"""
        button_row = QtWidgets.QWidget()
        button_row.setProperty("class", "ButtonRow")
        layout = QtWidgets.QHBoxLayout(button_row)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(8)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignVCenter)
        layout.addStretch()

        self.__cancel_button = QtWidgets.QPushButton("Cancel")
        self.__cancel_button.setProperty("class", "ButtonAction")
        self.__cancel_button.setFixedWidth(ToolConfig.CANCEL_BUTTON_WIDTH)
        self.__cancel_button.setEnabled(False)
        self.__cancel_button.setToolTip(
            "Stop after the current word has been finalized"
        )
        self.__cancel_button.clicked.connect(self.on_click_cancel_signal)
        layout.addWidget(self.__cancel_button)

        self.__run_button = QtWidgets.QPushButton("Run")
        self.__run_button.setProperty("class", "ButtonBlue")
        self.__run_button.setFixedWidth(ToolConfig.CANCEL_BUTTON_WIDTH)
        self.__run_button.setDefault(True)
        self.__run_button.clicked.connect(self.__on_click_run_button)
        layout.addWidget(self.__run_button)

        return button_row

    def __on_click_run_button(self) -> None:
        """Run ボタン押下時処理"""
        self.on_click_run_signal.emit(self.request())

    def __sync_options(self) -> SyncOptions:
        """Lyrics Sync の設定を、有効/無効に関わらず組み立てる。

        画面に無い項目 (max_gap_fill / word_tags / end_tag / title /
        artist) は dataclass の既定値のまま。
        """
        return SyncOptions(
            keep_blank=self.__keep_blank_check.isChecked(),
            offset=self.__offset_spin.value(),
        )

    def __lyrics_request(self) -> LyricsSyncRequest | None:
        """Lyrics Sync の実行内容を組み立てる。無効なら None を返す。"""
        if not self.__lyrics_check.isChecked():
            return None
        return LyricsSyncRequest(
            lyrics_path=self.__lyrics_row.path(),
            formats=self.__lyrics_formats_row.formats(),
            options=self.__sync_options(),
        )

    def request(self) -> WordTimestampsRequest:
        """入力内容から実行内容を組み立てる。

        Returns:
            WordTimestampsRequest: 画面で指定された実行内容。
        """
        return WordTimestampsRequest(
            audio_path=self.__input_row.path(),
            output_dir=self.__output_row.path(),
            formats=self.__formats_row.formats(),
            config=self.__whisper_options.config(),
            lyrics=self.__lyrics_request(),
        )

    def set_running(self, is_running: bool) -> None:
        """実行中の見た目に切り替える。

        Args:
            is_running: 実行中なら True。
        """
        self.__run_button.setEnabled(not is_running)
        self.__cancel_button.setEnabled(is_running)

    def state(self) -> dict[str, Any]:
        """保存する入力値を返す。"""
        request = self.request()
        return {
            "audio_path": request.audio_path,
            "output_dir": request.output_dir,
            "formats": request.formats,
            "config": asdict(request.config),
            "is_lyrics_enabled": request.lyrics is not None,
            "lyrics_path": self.__lyrics_row.path(),
            "lyrics_formats": self.__lyrics_formats_row.formats(),
            "sync_options": asdict(self.__sync_options()),
        }

    def set_state(self, state: dict[str, Any]) -> None:
        """保存済みの入力値を画面に戻す。

        古いバージョンで保存された余分なキーは無視する。

        Args:
            state: `state()` が返した辞書。
        """
        self.__input_row.set_path(state.get("audio_path", ""))
        self.__output_row.set_path(state.get("output_dir", OUTPUT_DIR))
        self.__formats_row.set_formats(state.get("formats", _DEFAULT_FORMATS))
        self.__whisper_options.set_config(
            WhisperConfig(**state.get("config", {}))
        )

        self.__lyrics_check.setChecked(
            bool(state.get("is_lyrics_enabled", False))
        )
        self.__lyrics_row.set_path(state.get("lyrics_path", ""))
        self.__lyrics_formats_row.set_formats(
            state.get("lyrics_formats", _DEFAULT_LYRICS_FORMATS)
        )
        sync = SyncOptions(**state.get("sync_options", {}))
        self.__keep_blank_check.setChecked(sync.keep_blank)
        self.__offset_spin.setValue(sync.offset)
