"""サンプル① 文字起こしのタブ。

`wsptoolkit.cli.transcribe` と同じ設定を画面から指定できるようにする。
Run を押すと入力内容を `TranscriptionRequest` に詰めて emit するだけで、
推論そのものは Controller / Model の担当。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from PySide6 import QtCore, QtWidgets
from wsptoolkit.definitions import TaskType
from wsptoolkit.gui.widgets.option_rows import (
    DirPathRow,
    FilePathRow,
    FormatsRow,
    NoWheelComboBox,
    WhisperOptionsGroup,
    build_form_scroll_area,
    build_group,
    build_labeled_row,
    select_combo_data,
)
from wsptoolkit.lib.data import TranscriptionResult
from wsptoolkit.lib.paths import AUDIO_DIR, OUTPUT_DIR
from wsptoolkit.lib.whisper import WhisperConfig
from wsptoolkit.tool_config import ToolConfig

# 初期状態でチェックしておく書き出し形式 (CLI の既定と同じ)
_DEFAULT_FORMATS = ("txt", "srt")


@dataclass
class TranscriptionRequest:
    """文字起こしの実行内容。

    Attributes:
        audio_path: 入力音声/動画のパス。
        output_dir: 書き出し先ディレクトリ。
        formats: 書き出す形式名。空なら書き出さない。
        config: 推論の設定。
        task: "transcribe" (そのまま) / "translate" (英語に翻訳)。
    """

    audio_path: str
    output_dir: str
    formats: list[str] = field(default_factory=list)
    config: WhisperConfig = field(default_factory=WhisperConfig)
    task: str = "transcribe"


class TranscriptionTab(QtWidgets.QWidget):
    """文字起こしタブ"""

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
            "Output Formats",
            TranscriptionResult.FORMATS,
            _DEFAULT_FORMATS,
        )

        self.__task_combo = NoWheelComboBox()
        for task_type in TaskType:
            self.__task_combo.addItem(task_type.value, task_type)
        self.__task_combo.setToolTip(
            "Select translate to transcribe while translating into English"
        )

        layout.addWidget(
            build_group(
                "Input / Output",
                self.__input_row,
                self.__output_row,
                self.__formats_row,
                build_labeled_row("Task", self.__task_combo),
            )
        )

        self.__whisper_options = WhisperOptionsGroup()
        layout.addWidget(self.__whisper_options)
        layout.addStretch()

        return build_form_scroll_area(content)

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
            "Stop after the current segment has been finalized"
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

    def request(self) -> TranscriptionRequest:
        """入力内容から実行内容を組み立てる。

        Returns:
            TranscriptionRequest: 画面で指定された実行内容。
        """
        return TranscriptionRequest(
            audio_path=self.__input_row.path(),
            output_dir=self.__output_row.path(),
            formats=self.__formats_row.formats(),
            config=self.__whisper_options.config(),
            task=self.__task_combo.currentData().value,
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
            "task": request.task,
        }

    def set_state(self, state: dict[str, Any]) -> None:
        """保存済みの入力値を画面に戻す。

        Args:
            state: `state()` が返した辞書。
        """
        self.__input_row.set_path(state.get("audio_path", ""))
        self.__output_row.set_path(state.get("output_dir", OUTPUT_DIR))
        self.__formats_row.set_formats(state.get("formats", _DEFAULT_FORMATS))
        self.__whisper_options.set_config(
            WhisperConfig(**state.get("config", {}))
        )
        select_combo_data(
            self.__task_combo, TaskType.from_name(state.get("task", ""))
        )
