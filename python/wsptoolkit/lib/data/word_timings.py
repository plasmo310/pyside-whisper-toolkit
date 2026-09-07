"""単語単位のタイムスタンプ (サンプル②) の結果データ。

書き出せる形式は json / csv。この JSON はサンプル③ の入力にもなるので、
読み戻す `load()` もここに置く。② と ③ のファイル契約がこのクラスに
集約される。
"""

from __future__ import annotations

import csv
import json
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from typing import ClassVar

from wsptoolkit.lib.settings import WhisperSampleError

from .interface import OutputDocument
from .transcription import Segment

# CSV の列。duration は end - start をその場で計算する
_CSV_HEADER = [
    "index",
    "segment_id",
    "word",
    "start",
    "end",
    "duration",
    "probability",
]


@dataclass
class Word:
    """単語 1 語ぶんの時刻と確信度。

    Attributes:
        index: 全体を通した単語の通し番号。
        segment_id: この単語が属するセグメントの id。
        word: 認識された表記。前後の空白を含む「そのまま」の文字列。
        start: 開始時刻 (秒)。
        end: 終了時刻 (秒)。
        probability: この語の確信度 (0.0-1.0)。
    """

    index: int
    segment_id: int
    word: str
    start: float
    end: float
    probability: float

    @property
    def duration(self) -> float:
        """発音されている長さ (秒)。"""
        return self.end - self.start


@dataclass
class WordTimingsResult(OutputDocument):
    """単語タイムスタンプの結果ひとまとめ。

    Attributes:
        model: 使ったモデル名。
        language: 判定された言語コード。
        duration: 音声全体の長さ (秒)。
        segments: セグメントのリスト。
        words: 単語のリスト。
    """

    FILE_LABEL: ClassVar[str] = "words"
    FORMATS: ClassVar[tuple[str, ...]] = ("json", "csv")

    model: str
    language: str
    duration: float
    segments: list[Segment] = field(default_factory=list)
    words: list[Word] = field(default_factory=list)

    @property
    def average_probability(self) -> float:
        """全単語の確信度の平均。単語が無ければ 0.0。"""
        if not self.words:
            return 0.0
        return sum(w.probability for w in self.words) / len(self.words)

    @classmethod
    def load(cls, path: str) -> WordTimingsResult:
        """`<名前>.words.json` を読み戻す（サンプル③ の入口）。

        既に手元にある words.json をそのまま読めるよう、欠けたキーには
        既定値を入れる。segments は ③ が使わないので読まない。

        Args:
            path: words.json のパス。

        Returns:
            WordTimingsResult: 復元した結果。

        Raises:
            WhisperSampleError: JSON として読めない、または words が空。
            OSError: ファイルを開けないとき。
        """
        with open(path, encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                raise WhisperSampleError(
                    f"Could not read words JSON: {path} ({e})"
                ) from e

        words = [
            Word(
                index=w.get("index", 0),
                segment_id=w.get("segment_id", 0),
                word=w.get("word") or "",
                start=w.get("start", 0.0),
                end=w.get("end", 0.0),
                probability=w.get("probability", 0.0),
            )
            for w in data.get("words") or []
        ]
        if not words:
            raise WhisperSampleError(f"No words found in: {path}")

        return cls(
            model=data.get("model", ""),
            language=data.get("language", ""),
            duration=data.get("duration"),
            words=words,
        )

    def writers(self) -> dict[str, Callable[[str], None]]:
        """形式名と書き出し関数の対応表。"""
        return {"json": self._write_json, "csv": self._write_csv}

    def _write_json(self, path: str) -> None:
        """単語と時刻を JSON で書き出す（日本語はエスケープしない）。"""
        payload = {
            "model": self.model,
            "language": self.language,
            "duration": self.duration,
            "segments": [asdict(seg) for seg in self.segments],
            "words": [asdict(w) for w in self.words],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def _write_csv(self, path: str) -> None:
        """単語ごとの時刻と確信度を CSV で書き出す。"""
        # Excel で開いても文字化けしないよう BOM 付き UTF-8 で書き出す
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(_CSV_HEADER)
            for w in self.words:
                writer.writerow(
                    [
                        w.index,
                        w.segment_id,
                        w.word,
                        f"{w.start:.3f}",
                        f"{w.end:.3f}",
                        f"{w.duration:.3f}",
                        f"{w.probability:.3f}",
                    ]
                )
