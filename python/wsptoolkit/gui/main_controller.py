"""メイン画面 Controller。

View のシグナルを受けて Model を呼び、結果を View へ返す。
推論は数分かかることがあるので、実行は `TaskRunner` に載せて
別スレッドで回す。
"""

from __future__ import annotations

from wsptoolkit.gui.widgets.transcription_tab import TranscriptionRequest
from wsptoolkit.gui.widgets.word_timestamps_tab import WordTimestampsRequest
from wsptoolkit.logger import setup_gui_logger

from .main_model import MainModel, RunOutcome
from .main_view import MainView
from .task_runner import TaskFunc, TaskRunner

# QSettings に入力値を保存するときのタブの識別子
_TAB_KEY_TRANSCRIPTION = "transcription"
_TAB_KEY_WORD_TIMESTAMPS = "word_timestamps"

# モデルが未ダウンロードのときに出す確認ダイアログ
_DOWNLOAD_DIALOG_TITLE = "Download Model"
_DOWNLOAD_DIALOG_MESSAGE = (
    'Model "{model}" has not been downloaded yet.\n'
    "The first run may take several minutes to download it from Hugging "
    "Face (large models require several GB).\n\n"
    "Do you want to continue?"
)

_CLEAR_SETTINGS_DIALOG_TITLE = "Clear Saved Settings"
_CLEAR_SETTINGS_DIALOG_MESSAGE = (
    "This will clear the saved window layout and all tab values, then "
    "restore the defaults.\n\nDo you want to continue?"
)


class MainController:
    """メイン画面 Controllerクラス

    Attributes:
        __model (MainModel): メイン画面 Model。
        __view (MainView): メイン画面 View。
        __runner (TaskRunner | None): 実行中のワーカー。
    """

    def __init__(self) -> None:
        """Model と View を作り、繋ぐ。"""
        self.__model = MainModel()
        self.__view = MainView()
        self.__runner: TaskRunner | None = None
        self.__setup_logging()
        self.__setup_connections()
        self.__init_data()

    def launch(self) -> None:
        """ツール起動"""
        self.__view.show()
        window_state = self.__model.load_window_state()
        if window_state:
            self.__view.restore_window_state(window_state)

    def __setup_logging(self) -> None:
        """`whisper_sample` のログを画面のログ欄へ流す。"""
        self.__log_bridge = setup_gui_logger()
        self.__log_bridge.on_log_signal.connect(self.__view.append_log)

    def __init_data(self) -> None:
        """初期データの設定"""
        transcription_state = self.__model.load_tab_state(
            _TAB_KEY_TRANSCRIPTION
        )
        if transcription_state:
            self.__view.transcription_tab.set_state(transcription_state)

        word_timestamps_state = self.__model.load_tab_state(
            _TAB_KEY_WORD_TIMESTAMPS
        )
        if word_timestamps_state:
            self.__view.word_timestamps_tab.set_state(word_timestamps_state)

    def __setup_connections(self) -> None:
        """Viewとの接続"""
        self.__view.transcription_tab.on_click_run_signal.connect(
            self.__on_click_run_transcription_button
        )
        self.__view.transcription_tab.on_click_cancel_signal.connect(
            self.__on_click_cancel_button
        )
        self.__view.word_timestamps_tab.on_click_run_signal.connect(
            self.__on_click_run_word_timestamps_button
        )
        self.__view.word_timestamps_tab.on_click_cancel_signal.connect(
            self.__on_click_cancel_button
        )
        self.__view.on_clear_settings_signal.connect(
            self.__on_clear_settings
        )
        self.__view.on_close_window_signal.connect(self.__on_close_window)

    def __on_click_run_transcription_button(
        self, request: TranscriptionRequest
    ) -> None:
        """Transcription タブの Run ボタン押下時処理

        Args:
            request: 画面で指定された実行内容。
        """
        if not self.__confirm_model_download(request.config.model):
            return
        self.__start_task(
            lambda on_progress, is_canceled: self.__model.run_transcription(
                request, on_progress, is_canceled
            )
        )

    def __on_click_run_word_timestamps_button(
        self, request: WordTimestampsRequest
    ) -> None:
        """Word Timestamps タブの Run ボタン押下時処理

        Args:
            request: 画面で指定された実行内容。
        """
        if not self.__confirm_model_download(request.config.model):
            return
        self.__start_task(
            lambda on_progress, is_canceled: self.__model.run_word_timestamps(
                request, on_progress, is_canceled
            )
        )

    def __confirm_model_download(self, model: str) -> bool:
        """モデルが未ダウンロードなら、時間がかかる旨を確認する。

        Args:
            model: 使うモデル名。

        Returns:
            bool: 実行してよければ True。
        """
        if self.__model.is_model_downloaded(model):
            return True
        return self.__view.show_confirm_dialog(
            _DOWNLOAD_DIALOG_TITLE,
            _DOWNLOAD_DIALOG_MESSAGE.format(model=model),
        )

    def __on_click_cancel_button(self) -> None:
        """Cancel ボタン押下時処理"""
        if self.__runner is None:
            return
        self.__view.append_log("[info] Canceling...")
        self.__runner.cancel()

    def __start_task(self, task: TaskFunc) -> None:
        """処理を別スレッドで開始する。

        Args:
            task: 実行する処理。
        """
        if self.__runner is not None:
            return

        self.__view.clear_log()
        self.__view.set_running(True)

        self.__runner = TaskRunner(task)
        self.__runner.on_progress_signal.connect(self.__view.append_log)
        self.__runner.on_finished_signal.connect(self.__on_task_finished)
        self.__runner.on_error_signal.connect(self.__on_task_error)
        self.__runner.finished.connect(self.__on_task_stopped)
        self.__runner.start()

    def __on_task_finished(self, outcome: RunOutcome) -> None:
        """処理が終わったときの表示"""
        if outcome.is_canceled:
            return
        if outcome.written_paths:
            self.__view.append_log(
                f"[info] Completed ({len(outcome.written_paths)} files)"
            )
        else:
            self.__view.append_log("[info] Completed (no files written)")

        if outcome.output_dir and not self.__view.open_output_folder(
            outcome.output_dir
        ):
            self.__view.append_log(
                "[warning] Could not open the output folder: "
                f"{outcome.output_dir}"
            )

    def __on_task_error(self, message: str) -> None:
        """処理が失敗したときの表示

        Args:
            message: 表示する文言。
        """
        self.__view.append_log(f"[error] {message}")
        self.__view.show_error_dialog(message)

    def __on_task_stopped(self) -> None:
        """ワーカーのスレッドが終わったときの後始末"""
        self.__runner = None
        self.__view.set_running(False)

    def __on_clear_settings(self) -> None:
        """保存済み設定を消去し、画面を既定値へ戻す。"""
        if not self.__view.show_confirm_dialog(
            _CLEAR_SETTINGS_DIALOG_TITLE,
            _CLEAR_SETTINGS_DIALOG_MESSAGE,
        ):
            return
        self.__model.clear_settings()
        self.__view.reset_settings()
        self.__view.append_log("[info] Saved settings have been cleared")

    def __on_close_window(self) -> None:
        """ウィンドウ終了時処理"""
        if self.__runner is not None:
            self.__runner.cancel()
            self.__runner.wait(3000)
        self.__model.save_window_state(self.__view.get_window_state())
        self.__model.save_tab_state(
            _TAB_KEY_TRANSCRIPTION, self.__view.transcription_tab.state()
        )
        self.__model.save_tab_state(
            _TAB_KEY_WORD_TIMESTAMPS,
            self.__view.word_timestamps_tab.state(),
        )
