"""文字起こし (サンプル①) の結果データ。書き出せる形式は txt/srt/vtt/json。"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from typing import ClassVar

from wsptoolkit.lib.timecode import format_timestamp

from .interface import OutputDocument


@dataclass
class Segment:
    """認識結果の 1 セグメント（≒ 1 フレーズ）。

    Attributes:
        id: セグメントの通し番号。
        start: 開始時刻 (秒)。
        end: 終了時刻 (秒)。
        text: 前後の空白を落とした認識テキスト。
    """

    id: int
    start: float
    end: float
    text: str


@dataclass
class TranscriptionResult(OutputDocument):
    """文字起こしの結果ひとまとめ。

    Attributes:
        model: 使ったモデル名。
        language: 判定された言語コード。
        language_probability: 言語判定の確信度。
        duration: 音声全体の長さ (秒)。
        segments: セグメントのリスト。
        elapsed: 推論にかかった秒数（表示用。ファイルには残さない）。
    """

    FILE_LABEL: ClassVar[str] = "transcribe"
    FORMATS: ClassVar[tuple[str, ...]] = ("txt", "srt", "vtt", "json")

    model: str
    language: str
    language_probability: float
    duration: float
    segments: list[Segment] = field(default_factory=list)
    elapsed: float = 0.0

    @property
    def full_text(self) -> str:
        """全セグメントをつないだ全文。日本語だけ語間に空白を入れない。"""
        sep = "" if self.language == "ja" else " "
        return sep.join(seg.text for seg in self.segments)

    @property
    def speed_ratio(self) -> float:
        """音声長に対する処理速度の倍率。elapsed が 0 なら 0.0。"""
        return self.duration / self.elapsed if self.elapsed else 0.0

    def writers(self) -> dict[str, Callable[[str], None]]:
        """形式名と書き出し関数の対応表。"""
        return {
            "txt": self._write_txt,
            "srt": self._write_srt,
            "vtt": self._write_vtt,
            "json": self._write_json,
        }

    def _write_txt(self, path: str) -> None:
        """全文テキストを 1 セグメント 1 行で書き出す。"""
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(seg.text.strip() + "\n" for seg in self.segments)

    def _write_srt(self, path: str) -> None:
        """SRT 字幕を書き出す（時刻の区切りはカンマ）。"""
        with open(path, "w", encoding="utf-8") as f:
            for i, seg in enumerate(self.segments, start=1):
                start = format_timestamp(seg.start, sep=",")
                end = format_timestamp(seg.end, sep=",")
                f.write(f"{i}\n{start} --> {end}\n{seg.text.strip()}\n\n")

    def _write_vtt(self, path: str) -> None:
        """WebVTT 字幕を書き出す（時刻の区切りはピリオド）。"""
        with open(path, "w", encoding="utf-8") as f:
            f.write("WEBVTT\n\n")
            for seg in self.segments:
                start = format_timestamp(seg.start)
                end = format_timestamp(seg.end)
                f.write(f"{start} --> {end}\n{seg.text.strip()}\n\n")

    def _write_json(self, path: str) -> None:
        """認識結果を JSON で書き出す（日本語はエスケープしない）。"""
        payload = {
            "model": self.model,
            "language": self.language,
            "language_probability": self.language_probability,
            "duration": self.duration,
            "text": self.full_text,
            "segments": [asdict(seg) for seg in self.segments],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
