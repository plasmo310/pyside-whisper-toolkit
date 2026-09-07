"""アプリを流れるデータクラス。

このサンプルで受け渡すデータはすべてここにある。各クラスは
`interface.OutputDocument` を継承していて、「自分をどの形式でどう
書き出すか」を自分で知っている。呼び出し側 (CLI / GUI) は

    document.write(output_dir, stem, ["lrc", "json"])

と書くだけでよく、形式ごとの分岐を持たなくてよい。

    interface.py       共通の約束ごと (OutputDocument / WriteEntry)
    transcription.py   ① 文字起こし
    word_timings.py    ② 単語単位のタイムスタンプ
    lyrics.py          ③ 時刻を張った歌詞
"""

from .interface import NO_OUTPUT, OutputDocument, WriteEntry, parse_formats
from .lyrics import LyricLine, LyricsDocument, LyricsMeta
from .transcription import Segment, TranscriptionResult
from .word_timings import Word, WordTimingsResult

__all__ = [
    "NO_OUTPUT",
    "LyricLine",
    "LyricsDocument",
    "LyricsMeta",
    "OutputDocument",
    "Segment",
    "TranscriptionResult",
    "Word",
    "WordTimingsResult",
    "WriteEntry",
    "parse_formats",
]
