"""このフォルダのデータクラスが共通で満たす約束ごと。

「どんなデータか」と「そのデータをどの形式でどう書き出すか」を 1 つの
クラスにまとめるための基底。呼び出し側 (CLI / GUI) は

    entries = document.write(output_dir, stem, formats)

の 1 行で済み、形式ごとの if/elif 分岐を持たなくてよい。
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import ClassVar

# --formats に渡すと「何も書き出さない」を意味する値
NO_OUTPUT = "none"


@dataclass
class WriteEntry:
    """1 形式ぶんの書き出し結果。

    Attributes:
        fmt: 指定された形式名。
        path: 書き出したファイルのパス。対応していない形式なら None。
    """

    fmt: str
    path: str | None = None


def parse_formats(text: str) -> list[str]:
    """`--formats` の指定を形式名のリストにする。

    Args:
        text: "txt,srt" のようなカンマ区切りの文字列。

    Returns:
        list[str]: 形式名のリスト。空文字や "none" だけなら空リスト
            （＝書き出さない）。
    """
    formats = [x.strip().lower() for x in text.split(",") if x.strip()]
    return [] if formats == [NO_OUTPUT] else formats


class OutputDocument(ABC):
    """ファイルに書き出せる結果データの基底。

    ファイル名は `<stem>.<FILE_LABEL>.<形式>` に統一する
    （例: `song.transcribe.srt` / `song.words.csv` / `song.lyrics.lrc`）。

    Attributes:
        FILE_LABEL: ファイル名に挟むラベル。サブクラスで定義する。
        FORMATS: 対応する形式名。`--formats` のヘルプ表示に使う。
    """

    FILE_LABEL: ClassVar[str] = ""
    FORMATS: ClassVar[tuple[str, ...]] = ()

    @abstractmethod
    def writers(self) -> dict[str, Callable[[str], None]]:
        """形式名 -> その形式で指定パスへ書き出す関数、の対応表。

        キーは FORMATS と一致させる。
        """

    def write(
        self, output_dir: str, stem: str, formats: Sequence[str]
    ) -> list[WriteEntry]:
        """指定された形式をまとめて書き出す。

        Args:
            output_dir: 書き出し先ディレクトリ。無ければ作る。
            stem: ファイル名の本体。
            formats: 書き出す形式名のリスト。空なら何もしない。

        Returns:
            list[WriteEntry]: 指定された順の結果。対応外の形式は
                path が None になる。

        Raises:
            OSError: ディレクトリを作れない、ファイルを書けないとき。
        """
        if not formats:
            return []

        writers = self.writers()
        os.makedirs(output_dir, exist_ok=True)
        entries: list[WriteEntry] = []
        for fmt in formats:
            writer = writers.get(fmt)
            if writer is None:
                entries.append(WriteEntry(fmt))
                continue
            path = os.path.join(output_dir, f"{stem}.{self.FILE_LABEL}.{fmt}")
            writer(path)
            entries.append(WriteEntry(fmt, path))
        return entries
