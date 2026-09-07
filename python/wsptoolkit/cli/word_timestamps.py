"""サンプル2: 単語単位のタイムスタンプを取得する。

word_timestamps=True を指定すると、Whisper の cross-attention から
DTW (Dynamic Time Warping) で各単語の開始/終了時刻が推定される。

使い方:
    python -m wsptoolkit.cli.word_timestamps input/audio/sample.mp3
    python -m wsptoolkit.cli.word_timestamps sample.mp3 --language ja --formats json,csv
    python -m wsptoolkit.cli.word_timestamps sample.mp3 --min-prob 0.5
    python -m wsptoolkit.cli.word_timestamps sample.mp3 --find 議事録
"""

from __future__ import annotations

import argparse
import os
import sys

from wsptoolkit.lib.data import Word, WordTimingsResult, parse_formats
from wsptoolkit.lib.paths import AUDIO_DIR
from wsptoolkit.lib.timecode import format_timestamp
from wsptoolkit.lib.whisper import WhisperManager

from .common import (
    add_output_args,
    add_whisper_args,
    decode_options_from_args,
    logger,
    report_written,
    resolve_existing,
    run,
    whisper_config_from_args,
)


def parse_args() -> argparse.Namespace:
    """コマンドライン引数を解析する。

    共通引数は common.add_whisper_args() が登録する。ここでは
    抽出条件 (--min-prob / --find) と、後半が繰り返し・ハルシネーションで
    崩れるとき用のデコード調整フラグを足す。

    Returns:
        argparse.Namespace: 解析済みの引数。

    Raises:
        SystemExit: 引数が不正なとき、または -h/--help のとき
            argparse が終了する。
    """
    parser = argparse.ArgumentParser(
        description="Get word-level timestamps with Whisper (faster-whisper)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    add_whisper_args(parser)
    add_output_args(parser, WordTimingsResult, "json,csv")
    parser.add_argument(
        "--min-prob",
        type=float,
        default=None,
        metavar="P",
        help="Show only words below this confidence threshold",
    )
    parser.add_argument(
        "--find",
        default=None,
        metavar="WORD",
        help="Show timestamps only for words containing this text",
    )
    # --- 後半が繰り返し・ハルシネーションで崩れるとき用のデコード調整（→ README §6）---
    # まず共通フラグの --no-vad を単体で試す。それでも直らないとき、次の順で。
    # 下 2 つはサビの連呼まで潰して歌詞照合をかえって壊すことがあるので必要なときだけ。
    parser.add_argument(
        "--no-condition-on-previous-text",
        dest="condition_on_previous_text",
        action="store_false",
        default=True,
        help="Do not use previous output as the prompt for the next segment; "
        "helps stop repeated chorus loops from propagating",
    )
    parser.add_argument(
        "--no-repeat-ngram-size",
        type=int,
        default=0,
        metavar="N",
        help="Block repeated N-grams (for example, 3); 0 disables this. "
        "This may also suppress intentional repetitions and reduce the "
        "lyrics match rate",
    )
    parser.add_argument(
        "--hallucination-silence-threshold",
        type=float,
        default=None,
        metavar="SEC",
        help="Skip silence of at least this duration when a hallucination is "
        "detected; values that are too small may remove opening vocals",
    )
    return parser.parse_args()


def main() -> int:
    """単語単位のタイムスタンプを取得し、表示・書き出しする。

    --min-prob / --find を指定した場合、画面表示だけを絞り込む
    （書き出しは常に全単語）。失敗したときの例外は run() が受け止める。

    Returns:
        int: 正常終了なら 0。
    """
    args = parse_args()
    audio = resolve_existing(
        args.audio, AUDIO_DIR, "Input file not found"
    )

    header_shown = False

    def show(word: Word) -> None:
        # 推論の進み具合が分かるよう、条件に合う語をその場で出す
        nonlocal header_shown
        if not header_shown:
            print(f"{'start':>12}  {'end':>12}  {'prob':>5}  word")
            print("-" * 48)
            header_shown = True
        if args.min_prob is not None and word.probability >= args.min_prob:
            return
        if args.find is not None and args.find not in word.word:
            return
        print(
            f"{format_timestamp(word.start):>12}  "
            f"{format_timestamp(word.end):>12}  "
            f"{word.probability:5.2f}  {word.word.strip()}",
            flush=True,
        )

    manager = WhisperManager(whisper_config_from_args(args))
    result = manager.transcribe_words(
        audio, options=decode_options_from_args(args), on_word=show
    )

    print(file=sys.stderr)
    logger.info(
        "%d words / %d segments", len(result.words), len(result.segments)
    )
    if result.words:
        logger.info("Average confidence %.3f", result.average_probability)

    stem = os.path.splitext(os.path.basename(audio))[0]
    report_written(
        result.write(args.output_dir, stem, parse_formats(args.formats))
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(run(main))
