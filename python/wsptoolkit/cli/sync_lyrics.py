"""サンプル3: 正解の歌詞テキストで単語タイムスタンプの文字を貼り直す。

`wsptoolkit.cli.word_timestamps` が出した <名前>.words.json は「Whisper が聞き取った文字」なので、
「番さ/晩さ」のような誤認識がそのまま時刻に紐づいている。
一方で時刻そのものは概ね正しいので、音声を再処理せずに

    正解の歌詞テキスト × 認識結果 を difflib で照合して、時刻の上に正しい文字を貼り直す

だけでカラオケ用の LRC が作れる。追加ライブラリは不要（標準ライブラリのみ）。

使い方:
    python -m wsptoolkit.cli.sync_lyrics sample.words.json --lyrics sample.txt
    python -m wsptoolkit.cli.sync_lyrics sample.words.json --lyrics sample.txt --report
    python -m wsptoolkit.cli.sync_lyrics sample.words.json --lyrics sample.txt -f json,lrc,srt
    python -m wsptoolkit.cli.sync_lyrics sample.words.json --lyrics sample.txt --offset -0.3
    python -m wsptoolkit.cli.sync_lyrics sample.words.json --lyrics sample.txt --keep-blank
"""

from __future__ import annotations

import argparse
import os
import sys

from wsptoolkit.lib.data import LyricsDocument, parse_formats
from wsptoolkit.lib.lyrics import MatchReport, SyncOptions, sync_lyrics
from wsptoolkit.lib.paths import LYRICS_DIR, OUTPUT_DIR
from wsptoolkit.lib.timecode import format_lrc_time

from .common import (
    add_output_args,
    logger,
    report_written,
    resolve_existing,
    run,
)

# ② が書き出すファイル名の末尾。書き出し名を作るときに落とす
_WORDS_SUFFIX = ".words.json"


def parse_args() -> argparse.Namespace:
    """コマンドライン引数を解析する。

    このサンプルは音声を扱わないので、共通引数 (add_whisper_args) は
    使わずに独自の引数だけを定義する。

    Returns:
        argparse.Namespace: 解析済みの引数。

    Raises:
        SystemExit: 引数が不正なとき、または -h/--help のとき
            argparse が終了する。
    """
    parser = argparse.ArgumentParser(
        description=(
            "Replace recognized words with supplied lyrics and create LRC "
            "output"
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "words_json",
        help="<name>.words.json produced by word_timestamps.py. Relative "
        "paths are searched from the current directory, repository root, "
        "then output",
    )
    parser.add_argument(
        "--lyrics",
        required=True,
        metavar="PATH",
        help="Lyrics text (UTF-8, one phrase per line). Relative paths are "
        "searched from the current directory, repository root, then "
        "input/lyrics",
    )
    add_output_args(parser, LyricsDocument, "json,lrc")
    parser.add_argument(
        "--offset",
        type=float,
        default=0.0,
        metavar="SEC",
        help=(
            "Seconds added to all timestamps; negative values show lyrics "
            "earlier"
        ),
    )
    parser.add_argument(
        "--max-gap-fill",
        type=float,
        default=0.6,
        metavar="SEC",
        help="Maximum seconds per character when filling sections missed by "
        "Whisper; prevents lyrics from stretching across long interludes. "
        "Use 0 to disable",
    )
    parser.add_argument(
        "--word-tags",
        action="store_true",
        help="Add enhanced LRC character tags (<mm:ss.xx>)",
    )
    parser.add_argument("--title", default=None, help="LRC [ti:] tag")
    parser.add_argument("--artist", default=None, help="LRC [ar:] tag")
    parser.add_argument(
        "--report",
        action="store_true",
        help="Show all differences, including matching sections",
    )
    parser.add_argument(
        "--keep-blank",
        action="store_true",
        help="Preserve blank lyric lines as empty LRC tags for interludes",
    )
    parser.add_argument(
        "--no-end-tag",
        dest="end_tag",
        action="store_false",
        default=True,
        help="Do not add a timestamp-only line after the final lyric line",
    )
    return parser.parse_args()


def sync_options_from_args(args: argparse.Namespace) -> SyncOptions:
    """解析済みの引数から貼り直しの設定を組み立てる。"""
    return SyncOptions(
        keep_blank=args.keep_blank,
        offset=args.offset,
        max_gap_fill=args.max_gap_fill,
        word_tags=args.word_tags,
        end_tag=args.end_tag,
        title=args.title,
        artist=args.artist,
    )


def print_report(report: MatchReport, show_all: bool = False) -> None:
    """認識 → 歌詞 の差分を標準出力に表示する。

    何がどう直ったかがこの出力で分かる。

    Args:
        report: match_chars() が返した照合結果。
        show_all: True なら一致した箇所も含めて全件表示する
            (--report 相当)。False なら差分のある箇所だけ。
    """
    rows = report.diff_rows(show_all=show_all)
    print("\n--- Recognition to lyrics differences ---")
    if not rows:
        print("No differences (all characters matched)")
        return
    for row in rows:
        stamp = (
            f"[{format_lrc_time(row.at)}]"
            if row.at is not None
            else "[--:--.--]"
        )
        print(f"{stamp} {row.hyp:<16} -> {row.ref:<16} {row.note}".rstrip())


def stem_of_words_json(path: str) -> str:
    """words.json のパスから書き出しファイル名の本体を作る。

    `.words.json` を落とす。その形でなければ拡張子だけ落とす。
    """
    name = os.path.basename(path)
    if name.endswith(_WORDS_SUFFIX):
        return name[: -len(_WORDS_SUFFIX)]
    return os.path.splitext(name)[0]


def main() -> int:
    """歌詞と認識結果を突き合わせ、時刻付き歌詞を表示・書き出しする。

    words.json と歌詞テキストの読み込み → difflib での照合 →
    行ごとの時刻の表示 → 差分レポート → 指定形式での書き出し、の順に進む。
    音声の再処理はしない。失敗したときの例外は run() が受け止める。

    Returns:
        int: 正常終了なら 0。
    """
    args = parse_args()

    words_json = resolve_existing(
        args.words_json, OUTPUT_DIR, "Words JSON not found"
    )
    lyrics_path = resolve_existing(
        args.lyrics, LYRICS_DIR, "Lyrics file not found"
    )

    result = sync_lyrics(words_json, lyrics_path, sync_options_from_args(args))
    document, report = result.document, result.report

    for line in document.lines:
        mark = " *" if line.interpolated else ""
        stamp = format_lrc_time(line.start + document.offset)
        print(f"[{stamp}] {line.display}{mark}", flush=True)

    print_report(report, show_all=args.report)

    print(file=sys.stderr)
    logger.info(
        "Match rate %.1f%% (%d of %d lyric characters matched)",
        report.match_rate * 100,
        report.matched,
        report.ref_len,
    )
    total = len(document.lines)
    logger.info(
        "Timestamped %d/%d lines (%d interpolated)",
        total,
        total,
        report.interpolated,
    )
    if report.interpolated:
        logger.info(
            "Lines marked with * could not be matched and were interpolated "
            "from adjacent lines"
        )

    report_written(
        document.write(
            args.output_dir,
            stem_of_words_json(words_json),
            parse_formats(args.formats),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(run(main))
