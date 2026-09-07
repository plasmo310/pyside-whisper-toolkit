"""メイン画面 Model。

処理モジュールの API を呼ぶのはこのクラスだけ。Qt のウィジェットには
触らず (保存に `QSettings` を使うだけ)、進捗は渡された関数へ、
失敗は `WhisperSampleError` で返す。CLI の各スクリプトの `main()` に
あたる部分をここに置いている。
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from PySide6.QtCore import QByteArray, QSettings
from wsptoolkit.gui.widgets.transcription_tab import TranscriptionRequest
from wsptoolkit.gui.widgets.word_timestamps_tab import (
    LyricsSyncRequest,
    WordTimestampsRequest,
)
from wsptoolkit.lib.data import Segment, Word, WriteEntry
from wsptoolkit.lib.lyrics import MatchReport, sync_lyrics
from wsptoolkit.lib.paths import AUDIO_DIR, LYRICS_DIR, resolve_input
from wsptoolkit.lib.settings import WhisperSampleError, get_logger
from wsptoolkit.lib.timecode import format_lrc_time, format_timestamp
from wsptoolkit.lib.whisper import (
    WhisperConfig,
    WhisperManager,
    is_model_downloaded,
)
from wsptoolkit.tool_config import ToolConfig

_logger = get_logger(__name__)

# 単語一覧のヘッダ (word_timestamps.py の表示と揃える)
_WORD_HEADER = f"{'start':>12}  {'end':>12}  {'prob':>5}  word"

# Lyrics Sync は words JSON のファイルを読むので、この形式は必須になる
_REQUIRED_WORDS_FORMAT = "json"


class TaskCanceledError(Exception):
    """利用者が Cancel を押したことを知らせる内部例外。

    `WhisperManager` にキャンセル用のフックは無いが、セグメント/単語の
    コールバックから投げれば推論のループを抜けられる。Model の中で
    捕まえるので、外へは出さない。
    """


@dataclass
class RunOutcome:
    """1 回の実行の結果。

    Attributes:
        written_paths: 書き出したファイルのパス。
        output_dir: 書き出し先ディレクトリ。
        is_canceled: Cancel で途中終了したか。
    """

    written_paths: list[str] = field(default_factory=list)
    output_dir: str | None = None
    is_canceled: bool = False


class MainModel:
    """メイン画面 Modelクラス

    Attributes:
        __manager (WhisperManager | None): 保持している Whisper マネージャ。
        __manager_config (WhisperConfig | None): そのマネージャを作った設定。
        __settings (QSettings): ウィンドウ状態と入力値の保存先。
    """

    __SAVE_KEY_GEOMETRY = "window/geometry"
    __SAVE_KEY_SPLITTER = "window/splitter"
    __SAVE_KEY_TAB_STATE = "state/%s"

    def __init__(self) -> None:
        """モデルを作る（この時点ではモデルをロードしない）。"""
        self.__manager: WhisperManager | None = None
        self.__manager_config: WhisperConfig | None = None
        self.__settings = QSettings(
            ToolConfig.SETTINGS_ORGANIZATION,
            ToolConfig.SETTINGS_APPLICATION,
        )

    # ------------------------------------------------------------------
    # 実行
    # ------------------------------------------------------------------

    def run_transcription(
        self,
        request: TranscriptionRequest,
        on_progress: Callable[[str], None],
        is_canceled: Callable[[], bool],
    ) -> RunOutcome:
        """文字起こしを実行して書き出す (サンプル①)。

        Args:
            request: 画面で指定された実行内容。
            on_progress: 進捗 1 行ぶんを受け取る関数。
            is_canceled: Cancel が押されたかを返す関数。

        Returns:
            RunOutcome: 書き出したパスと、途中終了したかどうか。

        Raises:
            WhisperSampleError: 入力が見つからない、faster-whisper が
                未インストールのとき。
        """
        audio = self.__resolve_audio(request.audio_path)

        def show(segment: Segment) -> None:
            if is_canceled():
                raise TaskCanceledError
            start = format_timestamp(segment.start)
            end = format_timestamp(segment.end)
            on_progress(f"[{start} --> {end}] {segment.text}")

        manager = self.__get_manager(request.config)
        try:
            result = manager.transcribe(
                audio, task=request.task, on_segment=show
            )
        except TaskCanceledError:
            _logger.warning("Canceled")
            return RunOutcome(is_canceled=True)

        on_progress("")
        on_progress("--- Full transcript ---")
        on_progress(result.full_text)
        on_progress("")
        _logger.info(
            "%d segments / elapsed %.1fs (%.1fx audio duration)",
            len(result.segments),
            result.elapsed,
            result.speed_ratio,
        )

        entries = result.write(
            request.output_dir, self.__stem_of(audio), request.formats
        )
        return RunOutcome(
            written_paths=self.__report_written(entries),
            output_dir=request.output_dir,
        )

    def run_word_timestamps(
        self,
        request: WordTimestampsRequest,
        on_progress: Callable[[str], None],
        is_canceled: Callable[[], bool],
    ) -> RunOutcome:
        """単語単位のタイムスタンプを取得して書き出す (サンプル②)。

        `request.lyrics` があれば、続けて歌詞との突き合わせ (サンプル③)
        まで行う。

        Args:
            request: 画面で指定された実行内容。
            on_progress: 進捗 1 行ぶんを受け取る関数。
            is_canceled: Cancel が押されたかを返す関数。

        Returns:
            RunOutcome: 書き出したパスと、途中終了したかどうか。

        Raises:
            WhisperSampleError: 入力が見つからない、faster-whisper が
                未インストールのとき。
        """
        audio = self.__resolve_audio(request.audio_path)
        lyrics_path = (
            self.__resolve_lyrics(request.lyrics.lyrics_path)
            if request.lyrics is not None
            else None
        )
        formats = self.__words_formats(request)

        is_header_shown = False

        def show(word: Word) -> None:
            # 推論の進み具合が分かるよう、確定した語をその場で出す
            nonlocal is_header_shown
            if is_canceled():
                raise TaskCanceledError
            if not is_header_shown:
                on_progress(_WORD_HEADER)
                on_progress("-" * 48)
                is_header_shown = True
            on_progress(
                f"{format_timestamp(word.start):>12}  "
                f"{format_timestamp(word.end):>12}  "
                f"{word.probability:5.2f}  {word.word.strip()}"
            )

        manager = self.__get_manager(request.config)
        try:
            result = manager.transcribe_words(audio, on_word=show)
        except TaskCanceledError:
            _logger.warning("Canceled")
            return RunOutcome(is_canceled=True)

        on_progress("")
        _logger.info(
            "%d words / %d segments", len(result.words), len(result.segments)
        )
        if result.words:
            _logger.info("Average confidence %.3f", result.average_probability)

        stem = self.__stem_of(audio)
        entries = result.write(request.output_dir, stem, formats)
        written_paths = self.__report_written(entries)

        if request.lyrics is not None and lyrics_path is not None:
            written_paths += self.__run_lyrics_sync(
                request.lyrics,
                lyrics_path,
                self.__words_json_path(entries),
                request.output_dir,
                stem,
                on_progress,
            )
        return RunOutcome(
            written_paths=written_paths,
            output_dir=request.output_dir,
        )

    def __run_lyrics_sync(
        self,
        request: LyricsSyncRequest,
        lyrics_path: str,
        words_json_path: str,
        output_dir: str,
        stem: str,
        on_progress: Callable[[str], None],
    ) -> list[str]:
        """歌詞との突き合わせを実行して書き出す (サンプル③)。

        Args:
            request: 画面で指定された歌詞照合の内容。
            lyrics_path: 解決済みの歌詞テキストのパス。
            words_json_path: 直前に書き出した words JSON のパス。
            output_dir: 書き出し先ディレクトリ。
            stem: 書き出しファイル名の本体。
            on_progress: 進捗 1 行ぶんを受け取る関数。

        Returns:
            list[str]: 書き出したファイルのパス。

        Raises:
            WhisperSampleError: words が空、歌詞に対象行が無いとき。
        """
        on_progress("")
        result = sync_lyrics(words_json_path, lyrics_path, request.options)
        document, report = result.document, result.report

        for line in document.lines:
            mark = " *" if line.interpolated else ""
            stamp = format_lrc_time(line.start + document.offset)
            on_progress(f"[{stamp}] {line.display}{mark}")

        self.__show_report(report, on_progress)

        on_progress("")
        _logger.info(
            "Match rate %.1f%% (%d of %d lyric characters matched)",
            report.match_rate * 100,
            report.matched,
            report.ref_len,
        )
        total = len(document.lines)
        _logger.info(
            "Timestamped %d/%d lines (%d interpolated)",
            total,
            total,
            report.interpolated,
        )
        if report.interpolated:
            _logger.info(
                "Lines marked with * could not be matched and were "
                "interpolated from adjacent lines"
            )

        entries = document.write(output_dir, stem, request.formats)
        return self.__report_written(entries)

    @staticmethod
    def __show_report(
        report: MatchReport,
        on_progress: Callable[[str], None],
    ) -> None:
        """認識 → 歌詞 の差分を出す。

        Args:
            report: `sync_lyrics()` が返した照合結果。
            on_progress: 進捗 1 行ぶんを受け取る関数。
        """
        rows = report.diff_rows()
        on_progress("")
        on_progress("--- Recognition to lyrics differences ---")
        if not rows:
            on_progress("No differences (all characters matched)")
            return
        for row in rows:
            stamp = (
                f"[{format_lrc_time(row.at)}]"
                if row.at is not None
                else "[--:--.--]"
            )
            on_progress(
                f"{stamp} {row.hyp:<16} -> {row.ref:<16} {row.note}".rstrip()
            )

    # ------------------------------------------------------------------
    # 入力の解決とヘルパ
    # ------------------------------------------------------------------

    @staticmethod
    def is_model_downloaded(model: str) -> bool:
        """モデルが手元にあるか（＝初回ダウンロードが不要か）を返す。

        Args:
            model: 使うモデル名。

        Returns:
            bool: 手元にあれば True。
        """
        return is_model_downloaded(model)

    def __get_manager(self, config: WhisperConfig) -> WhisperManager:
        """設定に合う Whisper マネージャを返す。

        設定が前回と同じならモデルを保持したまま使い回し、
        再ロード（初回は数百 MB のダウンロード）を避ける。

        Args:
            config: 推論の設定。

        Returns:
            WhisperManager: この設定で推論するマネージャ。
        """
        if self.__manager is None or self.__manager_config != config:
            self.__manager = WhisperManager(config)
            self.__manager_config = config
        return self.__manager

    @staticmethod
    def __words_formats(request: WordTimestampsRequest) -> list[str]:
        """words の書き出し形式を決める。

        Lyrics Sync は words JSON のファイルを読むので、有効なのに
        json が外れていたら足しておく。

        Args:
            request: 画面で指定された実行内容。

        Returns:
            list[str]: 実際に書き出す形式名。
        """
        formats = list(request.formats)
        if request.lyrics is None or _REQUIRED_WORDS_FORMAT in formats:
            return formats
        _logger.info(
            "Writing %s because Lyrics Sync requires it",
            _REQUIRED_WORDS_FORMAT,
        )
        return formats + [_REQUIRED_WORDS_FORMAT]

    @staticmethod
    def __words_json_path(entries: list[WriteEntry]) -> str:
        """書き出し結果から words JSON のパスを取り出す。

        Args:
            entries: `WordTimingsResult.write()` の戻り値。

        Returns:
            str: words JSON のパス。

        Raises:
            WhisperSampleError: 書き出されていないとき。
        """
        for entry in entries:
            if entry.fmt == _REQUIRED_WORDS_FORMAT and entry.path:
                return entry.path
        raise WhisperSampleError(
            "Lyrics Sync cannot run because the words JSON was not written"
        )

    @staticmethod
    def __resolve_audio(path: str) -> str:
        """入力音声のパスを解決し、実在することを確かめる。

        Args:
            path: 画面で指定されたパス。

        Returns:
            str: 実在が確認できたパス。

        Raises:
            WhisperSampleError: 未入力、またはどこにも見つからないとき。
        """
        if not path:
            raise WhisperSampleError("Select an input audio file")
        resolved = resolve_input(path, AUDIO_DIR)
        if not os.path.isfile(resolved):
            raise WhisperSampleError(
                f"Input file not found: {resolved}"
            )
        return resolved

    @staticmethod
    def __resolve_lyrics(path: str) -> str:
        """歌詞テキストのパスを解決し、実在することを確かめる。

        Args:
            path: 画面で指定されたパス。

        Returns:
            str: 実在が確認できたパス。

        Raises:
            WhisperSampleError: 未入力、またはどこにも見つからないとき。
        """
        if not path:
            raise WhisperSampleError("Select a lyrics file")
        resolved = resolve_input(path, LYRICS_DIR)
        if not os.path.isfile(resolved):
            raise WhisperSampleError(
                f"Lyrics file not found: {resolved}"
            )
        return resolved

    @staticmethod
    def __stem_of(audio_path: str) -> str:
        """音声のパスから書き出しファイル名の本体を作る。"""
        return os.path.splitext(os.path.basename(audio_path))[0]

    @staticmethod
    def __report_written(entries: list[WriteEntry]) -> list[str]:
        """書き出しの結果をログに出し、成功したパスを返す。

        Args:
            entries: `OutputDocument.write()` の戻り値。

        Returns:
            list[str]: 実際に書き出したファイルのパス。
        """
        written_paths: list[str] = []
        for entry in entries:
            if entry.path is None:
                _logger.warning(
                    "Skipping unsupported format: %s", entry.fmt
                )
                continue
            _logger.info("wrote %s", entry.path)
            written_paths.append(entry.path)
        return written_paths

    # ------------------------------------------------------------------
    # 保存データ
    # ------------------------------------------------------------------

    def clear_settings(self) -> None:
        """保存済みのウィンドウ状態とタブ入力値をすべて消去する。"""
        self.__settings.clear()
        self.__settings.sync()

    def load_window_state(self) -> dict[str, QByteArray] | None:
        """保存済みのウィンドウ状態を返す。未保存の場合は None を返す。"""
        if not self.__settings.contains(self.__SAVE_KEY_GEOMETRY):
            return None
        return {
            "geometry": self.__settings.value(self.__SAVE_KEY_GEOMETRY),
            "splitter": self.__settings.value(self.__SAVE_KEY_SPLITTER),
        }

    def save_window_state(self, window_state: dict[str, QByteArray]) -> None:
        """ウィンドウ状態を保存する。

        Args:
            window_state: `MainView.get_window_state()` の戻り値。
        """
        self.__settings.setValue(
            self.__SAVE_KEY_GEOMETRY, window_state["geometry"]
        )
        self.__settings.setValue(
            self.__SAVE_KEY_SPLITTER, window_state["splitter"]
        )
        self.__settings.sync()

    def load_tab_state(self, tab_key: str) -> dict[str, Any] | None:
        """保存済みのタブ入力値を返す。未保存/壊れていれば None を返す。

        Args:
            tab_key: タブを識別する文字列。

        Returns:
            dict[str, Any] | None: 保存済みの入力値。
        """
        raw = self.__settings.value(self.__SAVE_KEY_TAB_STATE % tab_key)
        if not raw:
            return None
        try:
            state = json.loads(raw)
        except (TypeError, ValueError):
            # 形が変わった後の古い保存データは黙って捨てる
            return None
        return state if isinstance(state, dict) else None

    def save_tab_state(self, tab_key: str, state: dict[str, Any]) -> None:
        """タブの入力値を保存する。

        Args:
            tab_key: タブを識別する文字列。
            state: 保存する入力値。
        """
        self.__settings.setValue(
            self.__SAVE_KEY_TAB_STATE % tab_key,
            json.dumps(state, ensure_ascii=False),
        )
        self.__settings.sync()
