"""3 本の CLI で共通の、引数定義とログの設定。

処理モジュールは画面出力もプロセス終了もしないので、その面倒を
ここで引き受ける。GUI を作るときは、このファイルの代わりに画面側が
`logging.Handler` を用意して同じことをする。
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from collections.abc import Callable

from wsptoolkit.lib.data import NO_OUTPUT, OutputDocument, WriteEntry
from wsptoolkit.lib.paths import OUTPUT_DIR, resolve_input
from wsptoolkit.lib.settings import (
    ACTIVATE_HINT,
    ROOT_LOGGER_NAME,
    WhisperSampleError,
)
from wsptoolkit.lib.whisper import MODEL_CHOICES, DecodeOptions, WhisperConfig

logger = logging.getLogger(ROOT_LOGGER_NAME)

# このプロジェクトが想定する Python のバージョン。変更するときは
# .python-version と scripts/win/setup_venv.bat・scripts/mac/setup_venv.sh の
# PYVER、pyproject.toml の target-version、build_env/scripts/*/Setup.* も
# 合わせること。
_REQUIRED_PYTHON = (3, 13)

# ログレベル -> 行頭に付けるラベル。従来の [info] / [warn] を保つ
_LEVEL_LABELS = {
    logging.DEBUG: "debug",
    logging.INFO: "info",
    logging.WARNING: "warn",
    logging.ERROR: "error",
    logging.CRITICAL: "error",
}


class _BracketFormatter(logging.Formatter):
    """`[info] メッセージ` の形に整える Formatter。"""

    def format(self, record: logging.LogRecord) -> str:
        """レベルのラベルを角括弧で前置した 1 行にする。"""
        label = _LEVEL_LABELS.get(record.levelno, record.levelname.lower())
        return f"[{label}] {record.getMessage()}"


def setup_logging() -> None:
    """このサンプルのログを標準エラーへ出すよう設定する。

    ルートロガーには触らない（faster-whisper 自身のログまで拾わないため）。
    """
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(_BracketFormatter())
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def check_python_version() -> None:
    """固定したバージョンの Python で動いていなければ警告する。

    .venv を有効化し忘れてシステムの Python で実行している、といった
    取り違えに気づくためのチェック。想定と違っても処理は止めない。
    """
    actual = sys.version_info[:2]
    if actual == _REQUIRED_PYTHON:
        return
    want = ".".join(str(x) for x in _REQUIRED_PYTHON)
    got = ".".join(str(x) for x in actual)
    logger.warning(
        "This project requires Python %s, but Python %s is currently in "
        "use. Activate the virtual environment with `%s` and try again.",
        want,
        got,
        ACTIVATE_HINT,
    )


def enable_utf8_stdout() -> None:
    """標準出力/標準エラーを UTF-8 に切り替える。

    Windows の cp932 コンソールやリダイレクト先で日本語が化けないように
    する。切り替えに失敗する環境では何もせずに続行する。
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # 切り替え不可の環境ではそのまま続行する
            pass


def add_whisper_args(parser: argparse.ArgumentParser) -> None:
    """音声を推論する 2 サンプル共通の引数を登録する。

    transcribe.py と word_timestamps.py から呼ぶ。sync_lyrics.py は音声を
    扱わないので使わない。
    """
    parser.add_argument(
        "audio",
        help="Input audio/video file (wav, mp3, m4a, mp4, etc.). Relative "
        "paths are searched from the current directory, repository root, "
        "then input/audio",
    )
    parser.add_argument(
        "-m",
        "--model",
        default="small",
        metavar="NAME",
        help=f"Model size or local path (default: small). Examples: "
        f"{', '.join(MODEL_CHOICES)}",
    )
    parser.add_argument(
        "-l",
        "--language",
        default=None,
        metavar="CODE",
        help="Language code (ja, en, etc.); auto-detected when omitted",
    )
    parser.add_argument(
        "-d",
        "--device",
        default="auto",
        choices=["auto", "cpu", "cuda"],
        help="Inference device (default: auto)",
    )
    parser.add_argument(
        "--compute-type",
        default=None,
        metavar="TYPE",
        help="Compute type (int8, int8_float16, float16, float32); selected "
        "automatically for the device by default",
    )
    parser.add_argument(
        "--beam-size",
        type=int,
        default=5,
        help="Beam search width (default: 5)",
    )
    parser.add_argument(
        "--vad",
        dest="vad",
        action="store_true",
        default=True,
        help="Use the VAD filter to remove silence (enabled by default)",
    )
    parser.add_argument(
        "--no-vad",
        dest="vad",
        action="store_false",
        help="Disable the VAD filter",
    )
    parser.add_argument(
        "--initial-prompt",
        default=None,
        metavar="TEXT",
        help="Prompt text for proper nouns and consistent spelling",
    )


def add_output_args(
    parser: argparse.ArgumentParser,
    document_cls: type[OutputDocument],
    default_formats: str,
) -> None:
    """書き出し先と書き出し形式の引数を登録する。

    対応形式のヘルプ文言は結果データクラスの FORMATS から作るので、形式を
    増やしてもここを直す必要はない。
    """
    parser.add_argument(
        "-o", "--output-dir", default=OUTPUT_DIR, help="Output directory"
    )
    parser.add_argument(
        "-f",
        "--formats",
        default=default_formats,
        help=(
            "Comma-separated output formats "
            f"({', '.join(document_cls.FORMATS)}); use {NO_OUTPUT} to write "
            "no files"
        ),
    )


def whisper_config_from_args(args: argparse.Namespace) -> WhisperConfig:
    """解析済みの引数から推論の設定を組み立てる。"""
    return WhisperConfig(
        model=args.model,
        language=args.language,
        device=args.device,
        compute_type=args.compute_type,
        beam_size=args.beam_size,
        vad=args.vad,
        initial_prompt=args.initial_prompt,
    )


def decode_options_from_args(args: argparse.Namespace) -> DecodeOptions:
    """解析済みの引数からデコード調整の設定を組み立てる。"""
    return DecodeOptions(
        condition_on_previous_text=args.condition_on_previous_text,
        no_repeat_ngram_size=args.no_repeat_ngram_size,
        hallucination_silence_threshold=args.hallucination_silence_threshold,
    )


def resolve_existing(path: str, default_dir: str, missing_message: str) -> str:
    """入力パスを解決し、実在することを確かめる。

    Args:
        path: 利用者が指定したパス。
        default_dir: 見つからないときに最後に探す既定の置き場。
        missing_message: 見つからないときの文言。末尾にパスが付く。

    Returns:
        str: 実在が確認できたパス。

    Raises:
        WhisperSampleError: どこにも見つからないとき。
    """
    resolved = resolve_input(path, default_dir)
    if not os.path.isfile(resolved):
        raise WhisperSampleError(f"{missing_message}: {resolved}")
    return resolved


def report_written(entries: list[WriteEntry]) -> None:
    """書き出しの結果を、指定された形式の順に画面へ出す。"""
    for entry in entries:
        if entry.path is None:
            logger.warning("Skipping unsupported format: %s", entry.fmt)
        else:
            logger.info("wrote %s", entry.path)


def run(main_func: Callable[[], int]) -> int:
    """CLI の共通の前処理と、エラーの受け止めをまとめる。

    Args:
        main_func: 実際の処理。終了コードを返す。

    Returns:
        int: プロセスの終了コード。失敗なら 1。
    """
    enable_utf8_stdout()
    setup_logging()
    check_python_version()
    try:
        return main_func()
    except WhisperSampleError as e:
        logger.error("%s", e)
        return 1
