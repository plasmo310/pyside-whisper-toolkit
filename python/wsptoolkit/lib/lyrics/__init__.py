"""正解の歌詞テキストで単語タイムスタンプの文字を貼り直す (サンプル③)。

起点は `lyrics_sync.py` の `sync_lyrics()`。ここを読めば流れが分かる。

    lyrics_sync.py   ← 起点。読み込み → 照合 → LyricsDocument までを通す
      ├ file_loader.py    歌詞ファイルの読み込みと文字の正規化
      └ char_matcher.py   difflib で 1 文字ずつ照合

② が出した `<名前>.words.json` は「Whisper が聞き取った文字」なので、
「番さ/晩さ」のような誤認識がそのまま時刻に紐づいている。一方で時刻
そのものは概ね正しいので、音声を再処理せずに difflib で照合し、時刻の
上に正しい文字を貼り直すだけでカラオケ用の LRC が作れる。音声もモデルも
触らない純粋な後処理で、追加ライブラリは不要（標準ライブラリのみ）。

    from wsptoolkit.lib.lyrics import SyncOptions, sync_lyrics

    result = sync_lyrics("song.words.json", "song.txt", SyncOptions())
    result.document.write("output", "song", ["lrc", "json"])

できあがったデータ (LyricLine / LyricsDocument) と書き出しは
`data/lyrics.py` にある。このパッケージが持つのは読み込みと照合だけ。
"""

from .char_matcher import DiffRow, MatchReport, match_chars
from .file_loader import load_lyrics
from .lyrics_sync import SyncOptions, SyncResult, sync_lyrics

__all__ = [
    "DiffRow",
    "MatchReport",
    "SyncOptions",
    "SyncResult",
    "load_lyrics",
    "match_chars",
    "sync_lyrics",
]
