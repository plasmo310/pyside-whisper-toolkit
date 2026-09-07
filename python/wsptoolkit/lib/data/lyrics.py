"""時刻を張った歌詞 (サンプル③) のデータ。書き出せる形式は lrc/json/srt。

照合そのものは `lyrics_sync.py` にある。ここにあるのは
「照合の結果できあがったデータ」と「その書き出し方」だけ。
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import ClassVar

from wsptoolkit.lib.timecode import format_lrc_time, format_timestamp

from .interface import OutputDocument


@dataclass
class LyricLine:
    """歌詞 1 行。表示用テキストと照合用テキストを分けて持つ。

    表示用 (display) には記号や空白がそのまま残るが、照合用
    (match_text) は正規化して記号を落とすため文字位置がずれる。
    その対応表が match_pos。

    Attributes:
        index: 対象行の通し番号 (0 始まり)。
        lineno: 歌詞ファイル上の行番号 (警告表示用)。
        display: LRC / SRT に書く表示テキスト。
        match_text: 照合に使う正規化済みテキスト。
        match_pos: match_text[k] が display の何文字目かの対応表。
        start: 行の開始時刻 (秒)。未確定なら None。
        end: 行の終了時刻 (秒)。未確定なら None。
        char_times: display の文字位置 -> (start, end) の辞書。
        matched_chars: 認識結果と直接対応が取れた文字数。
        interpolated: 時刻を補間で埋めた行なら True。
    """

    index: int
    lineno: int
    display: str
    match_text: str = ""
    match_pos: list[int] = field(default_factory=list)
    start: float | None = None
    end: float | None = None
    char_times: dict[int, tuple[float, float]] = field(default_factory=dict)
    matched_chars: int = 0
    interpolated: bool = False


@dataclass
class LyricsMeta:
    """LRC / JSON の先頭に入れるメタ情報。

    Attributes:
        title: LRC の [ti:] タグ。
        artist: LRC の [ar:] タグ。
        duration: 音声全体の長さ (秒)。LRC の [length:] タグに使う。
        model: 元の認識に使ったモデル名 (JSON 用)。
        language: 元の認識の言語コード (JSON 用)。
        match_rate: 照合の一致率 0.0-1.0 (JSON 用)。
    """

    title: str | None = None
    artist: str | None = None
    duration: float | None = None
    model: str | None = None
    language: str | None = None
    match_rate: float | None = None


@dataclass
class LyricsDocument(OutputDocument):
    """時刻を張った歌詞ひとまとめ。

    Attributes:
        lines: 時刻が張られた LyricLine のリスト。
        meta: LRC / JSON に入れるメタ情報。
        offset: 全時刻に加算する秒数（負値で早出し）。書き出すときに
            初めて足すので、lines 自体の時刻は変えない。
        word_tags: True なら拡張 LRC の文字タグ (<mm:ss.xx>) を付ける。
        end_tag: True なら LRC の最終行の後ろに終了時刻だけの行を入れる。
    """

    FILE_LABEL: ClassVar[str] = "lyrics"
    FORMATS: ClassVar[tuple[str, ...]] = ("json", "lrc", "srt")

    lines: list[LyricLine] = field(default_factory=list)
    meta: LyricsMeta = field(default_factory=LyricsMeta)
    offset: float = 0.0
    word_tags: bool = False
    end_tag: bool = True

    def writers(self) -> dict[str, Callable[[str], None]]:
        """形式名と書き出し関数の対応表。"""
        return {
            "lrc": self._write_lrc,
            "json": self._write_json,
            "srt": self._write_srt,
        }

    def _write_lrc(self, path: str) -> None:
        """カラオケ字幕 (LRC) を書き出す。

        offset は [offset:] タグではなく時刻へ直接加算する
        （[offset:] の符号の解釈がプレイヤーによって違うため）。
        """
        out: list[str] = []
        if self.meta.title:
            out.append(f"[ti:{self.meta.title}]")
        if self.meta.artist:
            out.append(f"[ar:{self.meta.artist}]")
        out.append("[re:whisper-sample sync_lyrics.py]")
        if self.meta.duration:
            out.append(f"[length:{format_lrc_time(self.meta.duration)}]")
        out.append("")

        for line in self.lines:
            stamp = format_lrc_time(line.start + self.offset)
            if self.word_tags and line.char_times:
                first = min(line.char_times)
                body: list[str] = []
                for pos, ch in enumerate(line.display):
                    times = line.char_times.get(pos)
                    if times is not None and pos != first:
                        at = format_lrc_time(times[0] + self.offset)
                        body.append(f"<{at}>")
                    body.append(ch)
                out.append(f"[{stamp}]" + "".join(body))
            else:
                out.append(f"[{stamp}]{line.display}")

        if self.end_tag and self.lines:
            last = format_lrc_time(self.lines[-1].end + self.offset)
            out.append(f"[{last}]")

        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(out) + "\n")

    def _write_srt(self, path: str) -> None:
        """歌詞を SRT 字幕として書き出す（ズレの目視確認用）。"""
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            for n, line in enumerate(self.lines, start=1):
                start = format_timestamp(line.start + self.offset, sep=",")
                end = format_timestamp(line.end + self.offset, sep=",")
                f.write(f"{n}\n{start} --> {end}\n{line.display}\n\n")

    def _write_json(self, path: str) -> None:
        """行単位の JSON を書き出す。

        キー名は words.json に揃えてあり、各行の "words" には文字単位の
        時刻が入る。
        """
        rows = []
        for line in self.lines:
            chars = [
                {
                    "word": line.display[pos],
                    "start": times[0] + self.offset,
                    "end": times[1] + self.offset,
                }
                for pos, times in sorted(line.char_times.items())
            ]
            rows.append(
                {
                    "index": line.index,
                    "lineno": line.lineno,
                    "text": line.display,
                    "start": line.start + self.offset,
                    "end": line.end + self.offset,
                    "interpolated": line.interpolated,
                    "words": chars,
                }
            )

        payload = {
            "model": self.meta.model,
            "language": self.meta.language,
            "duration": self.meta.duration,
            "offset": self.offset,
            "match_rate": self.meta.match_rate,
            "lines": rows,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
