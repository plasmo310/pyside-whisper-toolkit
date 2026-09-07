"""サンプル1: 音声ファイルを文字起こしする。

使い方:
    python -m wsptoolkit.cli.transcribe input/audio/sample.mp3
    python -m wsptoolkit.cli.transcribe input/audio/sample.mp3 --model medium --language ja
    python -m wsptoolkit.cli.transcribe sample.mp3 --formats txt,srt,vtt,json
"""

from __future__ import annotations

import argparse
import os
import sys

from wsptoolkit.lib.data import Segment, TranscriptionResult, parse_formats
from wsptoolkit.lib.paths import AUDIO_DIR
from wsptoolkit.lib.timecode import format_timestamp
from wsptoolkit.lib.whisper import WhisperManager

from .common import (
    add_output_args,
    add_whisper_args,
    logger,
    report_written,
    resolve_existing,
    run,
    whisper_config_from_args,
)


def parse_args() -> argparse.Namespace:
    """コマンドライン引数を解析する。

    共通引数 (音声パス・モデル・言語・デバイスなど) は
    common.add_whisper_args() が登録し、ここでは
    このサンプル固有の引数だけを足す。

    Returns:
        argparse.Namespace: 解析済みの引数。

    Raises:
        SystemExit: 引数が不正なとき、または -h/--help のとき
            argparse が終了する。
    """
    parser = argparse.ArgumentParser(
        description="Transcribe audio with Whisper (faster-whisper)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    add_whisper_args(parser)
    parser.add_argument(
        "--task",
        default="transcribe",
        choices=["transcribe", "translate"],
        help="transcribe in the source language or translate into English",
    )
    add_output_args(parser, TranscriptionResult, "txt,srt")
    return parser.parse_args()


def main() -> int:
    """文字起こしを実行し、結果を表示・書き出しする。

    音声パスの解決 → WhisperManager での推論 → セグメントの逐次表示 →
    指定形式での書き出し、の順に進む。失敗したときの例外は run() が
    受け止める。

    Returns:
        int: 正常終了なら 0。
    """
    args = parse_args()
    audio = resolve_existing(
        args.audio, AUDIO_DIR, "Input file not found"
    )

    def show(seg: Segment) -> None:
        # 逐次表示（長い音声でも進捗が分かる）
        start = format_timestamp(seg.start)
        end = format_timestamp(seg.end)
        print(f"[{start} --> {end}] {seg.text}", flush=True)

    manager = WhisperManager(whisper_config_from_args(args))
    result = manager.transcribe(audio, task=args.task, on_segment=show)

    print("\n--- Full transcript ---")
    print(result.full_text)
    print(file=sys.stderr)
    logger.info(
        "%d segments / elapsed %.1fs (%.1fx audio duration)",
        len(result.segments),
        result.elapsed,
        result.speed_ratio,
    )

    stem = os.path.splitext(os.path.basename(audio))[0]
    report_written(
        result.write(args.output_dir, stem, parse_formats(args.formats))
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(run(main))
