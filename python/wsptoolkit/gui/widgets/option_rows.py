"""タブで使い回す入力行のウィジェット。

どの行も「左にラベル、右に入力欄」で幅を揃える。値の取り出しは
`path()` / `formats()` のような素の Python 型を返すメソッドで行い、
Qt のウィジェットをタブの外へ露出させない。

縦位置は行の高さを `ToolConfig.ROW_HEIGHT` に固定し、中に置く
ウィジェットを全部 `AlignVCenter` で入れることで揃える
（ラベルとチェックボックスの高さが違っても行の中心に並ぶ）。
"""

from __future__ import annotations

import os
from collections.abc import Sequence

from PySide6 import QtCore, QtGui, QtWidgets
from wsptoolkit.definitions import LanguageType, ModelType
from wsptoolkit.lib.whisper import WhisperConfig
from wsptoolkit.tool_config import ToolConfig

# 既定値は lib 側の dataclass を唯一の出どころにする
_DEFAULT_CONFIG = WhisperConfig()

# 行の中身を縦中央に揃えるための指定
_ALIGN_V_CENTER = QtCore.Qt.AlignmentFlag.AlignVCenter

# Browse ボタンの幅
_BROWSE_BUTTON_WIDTH = 34


def build_label(label_text: str) -> QtWidgets.QLabel:
    """入力行の左に置く、幅を揃えたラベルを作る。

    Args:
        label_text: 表示する文字列。

    Returns:
        QtWidgets.QLabel: 幅を固定し、縦中央に寄せたラベル。
    """
    label = QtWidgets.QLabel(label_text)
    label.setProperty("class", "RowLabel")
    label.setFixedWidth(ToolConfig.LABEL_WIDTH)
    label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | _ALIGN_V_CENTER)
    return label


def build_row_widget() -> tuple[QtWidgets.QWidget, QtWidgets.QHBoxLayout]:
    """高さを揃えた空の 1 行と、そのレイアウトを作る。

    Returns:
        tuple[QtWidgets.QWidget, QtWidgets.QHBoxLayout]: 行とレイアウト。
    """
    row = QtWidgets.QWidget()
    row.setProperty("class", "OptionRow")
    row.setFixedHeight(ToolConfig.ROW_HEIGHT)

    layout = QtWidgets.QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    layout.setAlignment(_ALIGN_V_CENTER)
    return row, layout


def build_labeled_row(
    label_text: str,
    *widgets: QtWidgets.QWidget,
    stretch_last: bool = True,
) -> QtWidgets.QWidget:
    """ラベルと任意個のウィジェットを 1 行に並べる。

    行の enable/disable は返されたウィジェットに対して `setEnabled()` を
    呼べばまとめて効く。

    Args:
        label_text: 左に置くラベルの文字列。
        *widgets: 右に並べるウィジェット。
        stretch_last: 最後のウィジェットを横に伸ばすか。入力欄なら True、
            スピンボックスのように幅を固定したいものは False にする。

    Returns:
        QtWidgets.QWidget: 1 行ぶんのウィジェット。
    """
    row, layout = build_row_widget()
    layout.addWidget(build_label(label_text), 0, _ALIGN_V_CENTER)
    for index, widget in enumerate(widgets):
        is_last = index == len(widgets) - 1
        stretch = 1 if (is_last and stretch_last) else 0
        layout.addWidget(widget, stretch, _ALIGN_V_CENTER)
    if not stretch_last:
        layout.addStretch()
    return row


def build_group(title: str, *rows: QtWidgets.QWidget) -> QtWidgets.QGroupBox:
    """入力行をまとめたグループを作る。

    余白は QSS 側 (`QGroupBox` の padding) に任せるので、ここでは
    レイアウトの margin を 0 にする。全部の行を同じグループの中に
    置くことで、ラベルの左端がタブ内で揃う。

    Args:
        title: グループの見出し。
        *rows: 縦に並べる行。

    Returns:
        QtWidgets.QGroupBox: 行を並べたグループ。
    """
    group = QtWidgets.QGroupBox(title)
    layout = QtWidgets.QVBoxLayout(group)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    for row in rows:
        layout.addWidget(row)
    return group


def build_form_scroll_area(
    content: QtWidgets.QWidget,
) -> QtWidgets.QScrollArea:
    """フォームを載せるスクロール領域を作る。

    縦スクロールバーの場所は常に空けておく。出たり消えたりすると
    タブごとに入力欄の幅がずれてしまうため。スクロールが不要なときは
    スクロールバーを無効にして、QSS 側でつまみを消す。

    Args:
        content: 載せるウィジェット。

    Returns:
        QtWidgets.QScrollArea: 設定済みのスクロール領域。
    """
    scroll_area = QtWidgets.QScrollArea()
    scroll_area.setProperty("class", "FormScroll")
    scroll_area.setWidgetResizable(True)
    scroll_area.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
    scroll_area.setHorizontalScrollBarPolicy(
        QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    )
    scroll_area.setVerticalScrollBarPolicy(
        QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOn
    )
    scroll_area.setWidget(content)

    scroll_bar = scroll_area.verticalScrollBar()

    def update_scroll_bar_enabled(minimum: int, maximum: int) -> None:
        scroll_bar.setEnabled(maximum > minimum)

    scroll_bar.rangeChanged.connect(update_scroll_bar_enabled)
    update_scroll_bar_enabled(scroll_bar.minimum(), scroll_bar.maximum())
    return scroll_area


def select_combo_data(combo: QtWidgets.QComboBox, data: object) -> None:
    """`addItem(表示名, データ)` で入れた項目を、データで選び直す。

    Args:
        combo: 対象のコンボボックス。
        data: 選びたい項目のデータ。見つからなければ何もしない。
    """
    index = combo.findData(data)
    if index >= 0:
        combo.setCurrentIndex(index)


class NoWheelComboBox(QtWidgets.QComboBox):
    """閉じた状態でホイール操作による選択変更をしないコンボボックス。"""

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        """ホイールイベントを親へ渡し、フォームのスクロールに使う。"""
        event.ignore()


class _PathRowBase(QtWidgets.QWidget):
    """パス入力行の共通部分 (ラベル + 入力欄 + Browse ボタン)。

    Attributes:
        _default_dir (str): ダイアログを開く既定の場所。
    """

    def __init__(
        self,
        label_text: str,
        default_dir: str,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        """行を組み立てる。

        Args:
            label_text: 左に置くラベルの文字列。
            default_dir: 入力欄が空のときにダイアログを開く場所。
            parent: 親ウィジェット。
        """
        super().__init__(parent)
        self._default_dir = default_dir
        self.setProperty("class", "OptionRow")
        self.setFixedHeight(ToolConfig.ROW_HEIGHT)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.setAlignment(_ALIGN_V_CENTER)
        layout.addWidget(build_label(label_text), 0, _ALIGN_V_CENTER)

        self.__path_edit = QtWidgets.QLineEdit()
        layout.addWidget(self.__path_edit, 1, _ALIGN_V_CENTER)

        browse_button = QtWidgets.QPushButton("...")
        browse_button.setProperty("class", "EllipsisButton")
        browse_button.setFixedWidth(_BROWSE_BUTTON_WIDTH)
        browse_button.clicked.connect(self._on_click_browse_button)
        layout.addWidget(browse_button, 0, _ALIGN_V_CENTER)

    def _on_click_browse_button(self) -> None:
        """Browse ボタン押下時処理。サブクラスで実装する。"""
        raise NotImplementedError

    def _start_dir(self) -> str:
        """ダイアログを開く場所を決める。

        入力済みならそのパスの場所、空なら既定の置き場。
        """
        current = self.path()
        if current:
            return os.path.dirname(os.path.abspath(current))
        return self._default_dir

    def path(self) -> str:
        """入力されているパスを返す (前後の空白は落とす)。"""
        return self.__path_edit.text().strip()

    def set_path(self, path: str) -> None:
        """パスを設定する。

        Args:
            path: 設定するパス。
        """
        self.__path_edit.setText(path)


class FilePathRow(_PathRowBase):
    """ファイルパスの入力行。

    Attributes:
        __file_filter (str): ダイアログのファイルフィルタ。
    """

    def __init__(
        self,
        label_text: str,
        default_dir: str,
        file_filter: str,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        """行を組み立てる。

        Args:
            label_text: 左に置くラベルの文字列。
            default_dir: 入力欄が空のときにダイアログを開く場所。
            file_filter: ダイアログのファイルフィルタ。
            parent: 親ウィジェット。
        """
        super().__init__(label_text, default_dir, parent)
        self.__file_filter = file_filter

    def _on_click_browse_button(self) -> None:
        """Browse ボタン押下時処理"""
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select File", self._start_dir(), self.__file_filter
        )
        if path:
            self.set_path(os.path.normpath(path))


class DirPathRow(_PathRowBase):
    """ディレクトリパスの入力行。"""

    def _on_click_browse_button(self) -> None:
        """Browse ボタン押下時処理"""
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select Directory", self._start_dir()
        )
        if path:
            self.set_path(os.path.normpath(path))

    def _start_dir(self) -> str:
        """ダイアログを開く場所を決める。

        ディレクトリなので、入力済みならその場所自体を開く。
        """
        current = self.path()
        return current if current else self._default_dir


class FormatsRow(QtWidgets.QWidget):
    """書き出し形式のチェックボックス行。

    選択肢は結果データクラスの `FORMATS` から渡す。1 つもチェックが
    無ければ「書き出さない」(CLI の `--formats none` 相当) になる。

    Attributes:
        __check_box_dict (dict[str, QtWidgets.QCheckBox]): 形式名 -> チェックボックス。
    """

    def __init__(
        self,
        label_text: str,
        formats: Sequence[str],
        checked_formats: Sequence[str] = (),
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        """行を組み立てる。

        Args:
            label_text: 左に置くラベルの文字列。
            formats: 並べる形式名。
            checked_formats: 初期状態でチェックしておく形式名。
            parent: 親ウィジェット。
        """
        super().__init__(parent)
        self.setProperty("class", "OptionRow")
        self.setFixedHeight(ToolConfig.ROW_HEIGHT)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        layout.setAlignment(_ALIGN_V_CENTER)
        layout.addWidget(build_label(label_text), 0, _ALIGN_V_CENTER)

        self.__check_box_dict: dict[str, QtWidgets.QCheckBox] = {}
        for fmt in formats:
            check_box = QtWidgets.QCheckBox(fmt)
            check_box.setChecked(fmt in checked_formats)
            layout.addWidget(check_box, 0, _ALIGN_V_CENTER)
            self.__check_box_dict[fmt] = check_box
        layout.addStretch()

    def formats(self) -> list[str]:
        """チェックされている形式名を、並び順のまま返す。"""
        return [
            fmt
            for fmt, check_box in self.__check_box_dict.items()
            if check_box.isChecked()
        ]

    def set_formats(self, formats: Sequence[str]) -> None:
        """チェック状態を設定する。

        Args:
            formats: チェックする形式名。
        """
        for fmt, check_box in self.__check_box_dict.items():
            check_box.setChecked(fmt in formats)


class WhisperOptionsGroup(QtWidgets.QGroupBox):
    """2 つのタブで共通の Whisper オプション。

    よく使う 3 つだけを置き、それ以外 (device / compute_type /
    beam_size / initial_prompt) は `WhisperConfig` の既定値に任せる。
    細かく詰めたいときは CLI (`wsptoolkit.cli`) を使う。
    """

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        """グループを組み立てる。

        Args:
            parent: 親ウィジェット。
        """
        super().__init__("Whisper Options", parent)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 手入力させたくないので editable にはしない
        self.__model_combo = NoWheelComboBox()
        for model_type in ModelType:
            self.__model_combo.addItem(model_type.value, model_type)
        self.__model_combo.setToolTip(
            "Larger models are more accurate but slower; small is the "
            "practical minimum for Japanese"
        )
        layout.addWidget(build_labeled_row("Model", self.__model_combo))

        self.__language_combo = NoWheelComboBox()
        for language_type in LanguageType:
            self.__language_combo.addItem(language_type.label, language_type)
        self.__language_combo.setToolTip(
            "Selecting a language is faster and more accurate; Auto Detect "
            "lets Whisper determine it"
        )
        layout.addWidget(build_labeled_row("Language", self.__language_combo))

        self.__vad_check = QtWidgets.QCheckBox(
            "remove silence with Silero VAD"
        )
        self.__vad_check.setToolTip(
            "Try turning this off if transcription degrades later in a song"
        )
        layout.addWidget(
            build_labeled_row(
                "VAD Filter", self.__vad_check, stretch_last=False
            )
        )

        self.set_config(_DEFAULT_CONFIG)

    def config(self) -> WhisperConfig:
        """入力内容から推論の設定を組み立てる。

        Returns:
            WhisperConfig: 画面で指定された推論設定。画面に無い項目は
                dataclass の既定値のまま。
        """
        model_type: ModelType = self.__model_combo.currentData()
        language_type: LanguageType = self.__language_combo.currentData()
        return WhisperConfig(
            model=model_type.value,
            language=language_type.code or None,
            vad=self.__vad_check.isChecked(),
        )

    def set_config(self, config: WhisperConfig) -> None:
        """設定を画面に反映する。

        一覧に無いモデル名 (CLI で使える large-v2 など) が渡されたときは
        既定のモデルに落とす。

        Args:
            config: 反映する推論設定。
        """
        model_type = ModelType.from_name(config.model)
        if model_type is None:
            model_type = ModelType.from_name(_DEFAULT_CONFIG.model)
        select_combo_data(self.__model_combo, model_type)
        select_combo_data(
            self.__language_combo, LanguageType.from_code(config.language)
        )
        self.__vad_check.setChecked(config.vad)
